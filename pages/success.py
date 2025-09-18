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
blob_rel_path = st.query_params.get("blob", "")      # e.g. "<prefix>/posts+cap.json" or "<prefix>/something.zip"
download_name = st.query_params.get("name", "")      # suggested filename
session_id    = st.query_params.get("session_id", "")

if not blob_rel_path:
    st.error("Missing download information. Please contact support.")
    st.stop()

# Optional: verify payment (best-effort)
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

# Derive the backup prefix from the provided blob path
# "12345/John_20250101_101010/posts+cap.json" -> "12345/John_20250101_101010"
prefix = blob_rel_path.strip("/")
if not prefix:
    st.error("Invalid blob path.")
    st.stop()
if not blob_rel_path.endswith("/"):
    prefix = prefix.rsplit("/", 1)[0]
else:
    prefix = prefix.rstrip("/")

# Connect to Azure
try:
    bsc = BlobServiceClient.from_connection_string(AZ_CONN)
    cc  = bsc.get_container_client("backup")
except Exception as e:
    st.error(f"Azure connection failed: {e}")
    st.stop()

# Build curated ZIP (only images/ + profile.json)
images_prefix = f"{prefix}/images/"
profile_blob  = f"{prefix}/profile.json"

buf = io.BytesIO()
with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
    # Add profile.json (if present)
    try:
        bc_profile = cc.get_blob_client(profile_blob)
        if bc_profile.exists():
            zf.writestr("profile.json", bc_profile.download_blob().readall())
        else:
            zf.writestr("profile.json", json.dumps({"warning": "profile.json not found"}, indent=2))
    except Exception as e:
        zf.writestr("profile.json", json.dumps({"error": f"could not fetch profile.json: {e}"}, indent=2))

    # Add all images/* under this prefix
    try:
        for blob in cc.list_blobs(name_starts_with=images_prefix):
            arcname = blob.name[len(prefix)+1:]  # keep "images/..." inside the zip
            try:
                img_bytes = cc.get_blob_client(blob.name).download_blob().readall()
                zf.writestr(arcname, img_bytes)
            except Exception as e_img:
                zf.writestr(arcname + ".txt", f"Could not fetch image: {e_img}")
    except Exception as e:
        zf.writestr("images/README.txt", f"Could not list images: {e}")

data = buf.getvalue()

# Force the outgoing filename to .zip, set a nice default if missing
if not download_name:
    download_name = prefix.replace("/", "_") + "_images_profile.zip"
if not download_name.lower().endswith(".zip"):
    download_name = download_name.rsplit(".", 1)[0] + ".zip"

# Download button (ZIP only)
st.download_button(
    "⬇️ Download your backup",
    data=data,
    file_name=download_name,
    mime="application/zip",
    type="primary",
    use_container_width=True,
    key="dl_zip_btn",
)

st.info(f"File ready: **{download_name}**")

st.divider()
if st.button("📘 Go to Memories"):
    st.switch_page("pages/FbMemories.py")
