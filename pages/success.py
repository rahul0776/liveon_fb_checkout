import os, io, json, hashlib, time, zipfile
from pathlib import Path
from datetime import datetime, timedelta
import streamlit as st
from azure.storage.blob import BlobServiceClient
import stripe

st.set_page_config(page_title="Payment Success", page_icon="✅")

st.title("✅ Payment Successful")
st.caption("Your download will begin automatically. If it doesn’t, use the button below.")

# --- Save fb_token to per-user cache (unchanged)
if "fb_token" in st.session_state:
    cache_dir = Path("cache")
    cache_dir.mkdir(exist_ok=True)
    token_hash = hashlib.md5(st.session_state["fb_token"].encode()).hexdigest()
    (cache_dir / f"backup_cache_{token_hash}.json").write_text(
        json.dumps({"fb_token": st.session_state["fb_token"]})
    )

# --- Config
AZ_CONN = st.secrets.get("AZURE_CONNECTION_STRING") or os.getenv("AZURE_CONNECTION_STRING")
STRIPE_SECRET_KEY = st.secrets.get("STRIPE_SECRET_KEY") or os.getenv("STRIPE_SECRET_KEY")
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

# --- Incoming params from success_url
blob_rel_path = st.query_params.get("blob", "")
download_name = st.query_params.get("name", "backup.zip")
session_id    = st.query_params.get("session_id", "")

if not blob_rel_path:
    st.error("Missing download information. Please contact support.")
    st.stop()

# --- (Optional) verify Stripe says 'paid'
paid_ok = True
if session_id and STRIPE_SECRET_KEY:
    try:
        s = stripe.checkout.Session.retrieve(session_id)
        paid_ok = (s.get("payment_status") == "paid")
    except Exception:
        paid_ok = True  # don't hard-fail if Stripe check hiccups
if not paid_ok:
    st.error("We couldn’t verify your payment. If you were charged, please contact support.")
    st.stop()

# --- Fetch blob from Azure
try:
    bsc = BlobServiceClient.from_connection_string(AZ_CONN)
    bc  = bsc.get_blob_client(container="backup", blob=blob_rel_path)
    file_bytes = bc.download_blob().readall()
except Exception as e:
    st.error(f"Couldn’t fetch your file: {e}")
    st.stop()

# --- If we got a JSON blob, wrap it into a ZIP in-memory; if it's already a ZIP, pass through
mime = "application/zip"
if blob_rel_path.lower().endswith(".zip"):
    data = file_bytes
    if not download_name.lower().endswith(".zip"):
        download_name = download_name.rsplit(".", 1)[0] + ".zip"
else:
    # turn the JSON into a zip with a reasonable internal filename
    internal_json_name = (
        download_name if download_name.lower().endswith(".json")
        else "posts+cap.json"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(internal_json_name, file_bytes)
    data = buf.getvalue()
    if not download_name.lower().endswith(".zip"):
        base = download_name.rsplit(".", 1)[0]
        download_name = (base or "backup") + ".zip"

# --- The actual download button
st.download_button(
    "⬇️ Download your backup",
    data=data,
    file_name=download_name,
    mime=mime,
    type="primary",
    use_container_width=True,
    key="dl_zip_btn",
)

# --- Best-effort auto-click of the button
st.markdown(
    """
    <script>
      const tryClick = () => {
        const btns = Array.from(parent.document.querySelectorAll('button'));
        const btn = btns.find(b => b.innerText && b.innerText.includes('Download your backup'));
        if (btn) btn.click();
      };
      setTimeout(tryClick, 600);
    </script>
    """,
    unsafe_allow_html=True,
)

st.divider()
if st.button("📘 Go to Memories"):
    st.switch_page("pages/FbMemories.py")
