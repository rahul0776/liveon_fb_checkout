import os, io, json, hashlib, zipfile
from pathlib import Path
import streamlit as st
from azure.storage.blob import BlobServiceClient
import stripe

st.set_page_config(page_title="Payment Success", page_icon="✅")

st.title("✅ Payment Successful")
st.caption("Your download will begin automatically. If it doesn’t, use the button below.")

# Cache fb_token (unchanged)
if "fb_token" in st.session_state:
    cache_dir = Path("cache"); cache_dir.mkdir(exist_ok=True)
    token_hash = hashlib.md5(st.session_state["fb_token"].encode()).hexdigest()
    (cache_dir / f"backup_cache_{token_hash}.json").write_text(
        json.dumps({"fb_token": st.session_state["fb_token"]})
    )

# Config
AZ_CONN = st.secrets.get("AZURE_CONNECTION_STRING") or os.getenv("AZURE_CONNECTION_STRING")
STRIPE_SECRET_KEY = st.secrets.get("STRIPE_SECRET_KEY") or os.getenv("STRIPE_SECRET_KEY")
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

# Query params from success_url
blob_rel_path = st.query_params.get("blob", "")
download_name = st.query_params.get("name", "backup.zip")
session_id    = st.query_params.get("session_id", "")

if not blob_rel_path:
    st.error("Missing download information. Please contact support.")
    st.stop()

# Force the outgoing filename to .zip (no matter what the caller sent)
if not download_name.lower().endswith(".zip"):
    download_name = download_name.rsplit(".", 1)[0] + ".zip"

# Optional: verify payment
paid_ok = True
if session_id and STRIPE_SECRET_KEY:
    try:
        s = stripe.checkout.Session.retrieve(session_id)
        paid_ok = (s.get("payment_status") == "paid")
    except Exception:
        paid_ok = True
if not paid_ok:
    st.error("We couldn’t verify your payment. If you were charged, please contact support.")
    st.stop()

# Fetch blob
try:
    bsc = BlobServiceClient.from_connection_string(AZ_CONN)
    bc  = bsc.get_blob_client(container="backup", blob=blob_rel_path)
    file_bytes = bc.download_blob().readall()
except Exception as e:
    st.error(f"Couldn’t fetch your file: {e}")
    st.stop()

# Serve ZIP:
# - If the blob is already a .zip → pass through
# - If it's not → wrap it into a .zip with a stable internal name
mime = "application/octet-stream"  # prevent browser content sniffing
if blob_rel_path.lower().endswith(".zip"):
    data = file_bytes
else:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("posts+cap.json", file_bytes)  # internal filename inside the zip
    data = buf.getvalue()

# Download button (the auto-click JS is optional and left out to avoid iframe issues)
st.download_button(
    "⬇️ Download your backup",
    data=data,
    file_name=download_name,
    mime=mime,
    type="primary",
    use_container_width=True,
    key="dl_zip_btn",
)

st.info(f"File ready: **{download_name}**")

st.divider()
if st.button("📘 Go to Memories"):
    st.switch_page("pages/FbMemories.py")
