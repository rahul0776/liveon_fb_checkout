import os
import time
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import quote_plus

import streamlit as st

# Azure Blob imports
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions

# Optional Stripe verification
try:
    import stripe
except Exception:
    stripe = None

st.set_page_config(page_title="Payment Success", page_icon="✅")

st.title("✅ Payment Successful")
st.markdown("Thank you for your purchase! Your download is starting…")

# -- Read query params ---------------------------------------------------------
try:
    qp = st.query_params  # Streamlit ≥ 1.31
    get_q = lambda k, d=None: qp.get(k, d)
except Exception:
    qp = st.experimental_get_query_params()
    get_q = lambda k, d=None: (qp.get(k) or [d])[0]

blob_path  = get_q("blob")
file_name  = get_q("name", "backup.json")
session_id = get_q("session_id")

# -- Optional: verify payment with Stripe -------------------------------------
STRIPE_SECRET_KEY = st.secrets.get("STRIPE_SECRET_KEY") or os.getenv("STRIPE_SECRET_KEY")
if session_id and STRIPE_SECRET_KEY and stripe is not None:
    try:
        stripe.api_key = STRIPE_SECRET_KEY
        s = stripe.checkout.Session.retrieve(session_id, expand=["payment_intent"])
        if s.get("payment_status") != "paid":
            st.error("We couldn’t confirm your payment yet. Please wait a moment or refresh this page.")
            st.stop()
    except Exception as e:
        # If verification fails, we still proceed to try the download but show a warning
        st.warning(f"Could not verify payment status: {e}")

# -- Save fb_token to per-user cache (your previous behavior) -----------------
if "fb_token" in st.session_state:
    cache_dir = Path("cache")
    cache_dir.mkdir(exist_ok=True)
    token_hash = hashlib.md5(st.session_state["fb_token"].encode()).hexdigest()
    cache_file = cache_dir / f"backup_cache_{token_hash}.json"
    with open(cache_file, "w") as f:
        json.dump({"fb_token": st.session_state["fb_token"]}, f)

# -- If we didn't get a blob target, show a friendly message -------------------
if not blob_path:
    st.info("No download target provided. You can return to the Projects page and try again.")
    st.link_button("Back to Projects", "Projects.py")
    st.stop()

# -- Create a short-lived SAS URL to auto-start the download -------------------
AZ_CONN = st.secrets.get("AZURE_CONNECTION_STRING") or os.getenv("AZURE_CONNECTION_STRING")
if not AZ_CONN:
    st.error("Missing AZURE_CONNECTION_STRING. Ask support if this persists.")
    st.stop()

service = BlobServiceClient.from_connection_string(AZ_CONN)
account_name = service.account_name

# Extract account key from the connection string (required for SAS creation)
account_key = None
for part in AZ_CONN.split(";"):
    if part.startswith("AccountKey="):
        account_key = part.split("=", 1)[1]
        break

container_name = "backup"   # your container
expires = datetime.utcnow() + timedelta(minutes=10)

sas = None
if account_key:
    try:
        sas = generate_blob_sas(
            account_name=account_name,
            container_name=container_name,
            blob_name=blob_path,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=expires,
        )
    except Exception as e:
        st.warning(f"Could not generate a SAS URL automatically: {e}")

# If SAS creation succeeded, redirect immediately to trigger download
if sas:
    sas_url = f"https://{account_name}.blob.core.windows.net/{container_name}/{quote_plus(blob_path)}?{sas}"

    # Auto-redirect via meta refresh (works in Streamlit)
    st.markdown(f"<meta http-equiv='refresh' content='0; url={sas_url}'>", unsafe_allow_html=True)

    st.success("Your download should begin automatically.")
    st.link_button("If it doesn’t, click to download now", sas_url)
else:
    # Fallback: stream the blob and offer a manual download button
    try:
        blob_client = service.get_container_client(container_name).get_blob_client(blob_path)
        data = blob_client.download_blob().readall()
        st.download_button("Download now", data=data, file_name=file_name, mime="application/json")
    except Exception as e:
        st.error(f"Could not prepare your download: {e}")

# Helpful links
st.divider()
col1, col2 = st.columns(2)
with col1:
    st.link_button("⬅️ Back to Projects", "Projects.py")
with col2:
    st.link_button("📘 Go to Memories", "pages/FbMemories.py")
