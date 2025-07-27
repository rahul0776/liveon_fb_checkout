# FbFullProfile.py (FINAL UPDATED)
import streamlit as st
import json, os, requests, zipfile, shutil, concurrent.futures
from datetime import datetime, timezone
from pathlib import Path
from azure.storage.blob import BlobServiceClient
import hashlib  # ✅ For safe cache filenames

# ── Config & Styles
st.set_page_config(
    page_title="LiveOn · New Backup",
    page_icon=":package:",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""<style>
html,body,.stApp{background:#fafbfc;color:#131517;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto;}
.topbar{display:flex;justify-content:space-between;align-items:center;background:#f0f2f5;
        padding:12px 24px;border-bottom:1px solid #E1E4E8;font-size:15px;position:sticky;top:0;z-index:998;}
.topbar a{color:#1877f2;font-weight:600;text-decoration:none;}
.card{background:#fff;border:1px solid #E1E4E8;border-radius:10px;box-shadow:0 2px 6px rgba(0,0,0,.05);
      max-width:520px;margin:40px auto;padding:34px 32px;}
.stButton>button{background:#1877f2;border:none;color:#fff;padding:12px 0;border-radius:6px;font-weight:600;font-size:15px;width:100%;}
.stButton>button:hover{background:#0f5bb5;}
.instructions {background:#f8f9fa;border-left:4px solid #1877f2;padding:12px 16px;margin:16px 0;font-size:14px;}
div[data-testid="stAlert"] {font-weight:600;border-left:4px solid #1877f2 !important;background:#e7f0fa !important;}
div[data-testid="stAlert"] * {color:#131517 !important;}
div[data-testid="stAlert"]:has(svg[data-testid="stIcon-success"]) {
    border-left-color:#28a745 !important;background:#d4edda !important;}
div[data-testid="stAlert"]:has(svg[data-testid="stIcon-warning"]) {
    border-left-color:#ffc107 !important;background:#fff3cd !important;}
div[data-testid="stAlert"]:has(svg[data-testid="stIcon-error"]) {
    border-left-color:#dc3545 !important;background:#f8d7da !important;}
</style>""", unsafe_allow_html=True)

st.markdown('<div class="topbar"><div><strong>LiveOn</strong> · Backup&nbsp;Process</div>'
            '<a href="/FbeMyProjects?tab=backups" target="_self">⇦ Back to Dashboard</a></div>', 
            unsafe_allow_html=True)
def dense_caption(img_path):
    endpoint = st.secrets["AZURE_VISION_ENDPOINT"].rstrip("/") + "/vision/v3.2/analyze?visualFeatures=Description,Tags,Objects"
    headers = {
        "Ocp-Apim-Subscription-Key": st.secrets["AZURE_VISION_KEY"],
        "Content-Type": "application/octet-stream"
    }
    try:
        with open(img_path, "rb") as f:
            data = f.read()
        r = requests.post(endpoint, headers=headers, data=data, timeout=8)
        r.raise_for_status()
        result = r.json()

        caption = result.get("description", {}).get("captions", [{}])[0].get("text", "No caption found.")
        tags = result.get("description", {}).get("tags", [])
        objects = [obj["object"] for obj in result.get("objects", [])]

        # Build richer context caption
        context_caption = caption
        if tags:
            context_caption += ", tags: " + ", ".join(tags)
        if objects:
            context_caption += ", objects: " + ", ".join(objects)
        return context_caption
    except requests.exceptions.Timeout:
        return "No caption (timeout)"
    except Exception:
        return "No caption (API error)"
# ── Azure & Paths
AZ_CONN = st.secrets["AZURE_CONNECTION_STRING"]
blob_service_client = BlobServiceClient.from_connection_string(AZ_CONN)
CONTAINER = "backup"
BACKUP_DIR = Path("facebook_data")
IMG_DIR = BACKUP_DIR / "images"
BACKUP_DIR.mkdir(exist_ok=True)
IMG_DIR.mkdir(exist_ok=True)

# ✅ Utility for safe cache filenames
def safe_token_hash(token):
    return hashlib.md5(token.encode()).hexdigest()

# ── Helpers
def fetch_data(endpoint, token, since=None, until=None, fields=None):
    url = f"https://graph.facebook.com/me/{endpoint}?access_token={token}"
    if fields: url += f"&fields={fields}"
    if since: url += f"&since={since}"
    if until: url += f"&until={until}"
    data, pages = [], 0
    while url and pages < 20:
        try:
            res = requests.get(url, timeout=20).json()
            if "error" in res:
                st.warning(f"Skipping {endpoint}: {res['error'].get('message')}")
                break
            data.extend(res.get("data", []))
            url = res.get("paging", {}).get("next")
            pages += 1
        except Exception as e:
            st.warning(f"Network error on {endpoint}: {e}")
            break
    return data

def save_json(obj, name):
    fp = BACKUP_DIR / f"{name}.json"
    fp.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    return fp

def upload(local_path, blob_path):
    container = blob_service_client.get_container_client(CONTAINER)
    try: container.create_container()
    except Exception: pass
    with local_path.open("rb") as f:
        container.get_blob_client(blob_path).upload_blob(f, overwrite=True)

# ✅ Download Facebook image & upload to Azure
def download_and_upload_image(fb_url, blob_folder, name_id):
    ext = fb_url.split("?")[0].split(".")[-1].split("/")[-1]
    if len(ext) > 5 or "/" in ext:
        ext = "jpg"
    fname = f"{name_id}.{ext}"
    local_path = IMG_DIR / fname
    try:
        r = requests.get(fb_url, stream=True, timeout=10)
        if r.status_code == 200:
            with open(local_path, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
            blob_path = f"{blob_folder}images/{fname}"
            upload(local_path, blob_path)

            # ✅ Generate caption using Azure Vision
            caption = dense_caption(local_path)
            return blob_path, caption
    except Exception as e:
        st.warning(f"Failed to fetch image: {fb_url} ({e})")
    return None, None

def zip_backup(zip_name):
    zip_path = Path(zip_name)
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for folder, _, files in os.walk(BACKUP_DIR):
            for file in files:
                fp = os.path.join(folder, file)
                arcname = os.path.relpath(fp, BACKUP_DIR)
                zipf.write(fp, arcname)
    return zip_path

# ── MAIN BACKUP WORKFLOW
st.markdown('<div class="card">', unsafe_allow_html=True)
st.header("📦 Create Facebook Backup")

if "fb_token" not in st.session_state:
    st.error("🔒 Please log in with Facebook first.")
    st.stop()

token = st.session_state["fb_token"]
if st.button("⬇️ Start My Backup"):
    profile = requests.get(f"https://graph.facebook.com/me?fields=id,name,email&access_token={token}").json()
    fb_name = profile.get("name", "user").replace(" ", "_")
    folder_prefix = f"{fb_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}/"
    bar = st.progress(0.1)

    # 1️⃣ Fetch posts
    posts = fetch_data("posts", token, fields="id,message,created_time,full_picture")
    bar.progress(0.3)

    # 2️⃣ Download & upload images
    st.info("🔄 Downloading images & uploading to Azure...")
    for post in posts:
        img_url = post.get("full_picture")
        if img_url:
            blob_img_path, caption = download_and_upload_image(img_url, folder_prefix, post["id"])
            post["full_picture"] = blob_img_path if blob_img_path else None
            post["caption"] = caption if caption else "No caption"
        else:
            post["caption"] = None

    save_json(posts, "posts")
    upload(BACKUP_DIR / "posts.json", folder_prefix + "posts.json")
    bar.progress(0.6)

    # 3️⃣ Upload summary
    summary = {
        "user": fb_name,
        "user_id": profile.get("id"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "posts": len(posts)
    }
    upload(save_json(summary, "summary"), folder_prefix + "summary.json")

    # 4️⃣ Zip backup (optional)
    zip_path = zip_backup(f"facebook_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")
    bar.empty()
    st.success(f"✅ Backup complete! Files archived in {zip_path}")

    # Update session state
    st.session_state.update({
        "latest_backup": {
            "Name": fb_name,
            "Created On": datetime.now().strftime("%b %d, %Y"),
            "# Posts": len(posts),
            "Folder": folder_prefix.rstrip("/"),
            "user_id": profile.get("id")
        },
        "new_backup_done": True,
        "fb_token": token
    })

    # Cache backup details
    cache_dir = Path("cache")
    cache_dir.mkdir(exist_ok=True)
    cache_file = cache_dir / f"backup_cache_{safe_token_hash(token)}.json"
    with open(cache_file, "w") as f:
        json.dump({
            "fb_token": token,
            "latest_backup": st.session_state["latest_backup"],
            "new_backup_done": True,
            "fb_id": profile.get("id"),
            "fb_name": fb_name
        }, f)


# Redirect logic

# After backup completion
if st.session_state.get("redirect_to_projects"):
    st.session_state["redirect_to_projects"] = False
    # Redirect with query parameter to open Projects tab
    st.switch_page("pages/Projects.py")
elif st.button("← Back to My Projects"):
    # Redirect with query parameter to open Projects tab
    st.switch_page("pages/Projects.py")

st.markdown('</div>', unsafe_allow_html=True)