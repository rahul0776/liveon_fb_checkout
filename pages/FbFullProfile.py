# FbFullProfile.py
import streamlit as st
import json, os, requests, zipfile, shutil, concurrent.futures
from datetime import datetime, timezone
from pathlib import Path
from azure.storage.blob import BlobServiceClient

# ── Config & Styles
st.set_page_config(
    page_title="LiveOn · New Backup",
    page_icon=":package:",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
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
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="topbar"><div><strong>LiveOn</strong> · Backup&nbsp;Process</div>'
            '<a href="/FbeMyProjects" target="_self">⇦ Back to Dashboard</a></div>', unsafe_allow_html=True)

# ── Azure & Paths
AZ_CONN = st.secrets["AZURE_CONNECTION_STRING"]
blob_service_client = BlobServiceClient.from_connection_string(AZ_CONN)
CONTAINER = "backup"
BACKUP_DIR = Path("facebook_data")
IMG_DIR = BACKUP_DIR / "images"
BACKUP_DIR.mkdir(exist_ok=True)
IMG_DIR.mkdir(exist_ok=True)
editing_folder = st.session_state.pop("editing_backup_folder", None)
user_input_name = editing_folder.split("_")[0] if editing_folder else ""
if editing_folder:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("✂️ Edit Backup Duration")
    st.info(f"Editing backup: `{editing_folder}`")

    # Load posts+cap.json from Azure
    container = blob_service_client.get_container_client(CONTAINER)
    blob_client = container.get_blob_client(f"{editing_folder}/posts+cap.json")
    try:
        posts_data = json.loads(blob_client.download_blob().readall())
    except Exception as e:
        st.error(f"Failed to load backup data: {e}")
        st.stop()

    # Prepare dates
    all_dates = []
    for p in posts_data:
        try:
            all_dates.append(datetime.fromisoformat(p["created_time"]).date())
        except Exception:
            continue

    if not all_dates:
        st.warning("No valid post dates found in this backup.")
        st.stop()

    min_date = min(all_dates)
    max_date = max(all_dates)

    start_date, end_date = st.date_input(
        "📅 Select a date range to create a new project from this backup",
        (min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    # Filter posts
    filtered_posts = [
        p for p in posts_data
        if "created_time" in p and start_date <= datetime.fromisoformat(p["created_time"]).date() <= end_date
    ]

    st.success(f"✅ Found {len(filtered_posts)} posts in the selected date range.")

    if st.button("✨ Create Project from this Range"):
        project_name = f"{user_input_name}_{start_date}_{end_date}"
        project = {
            "id": f"{user_input_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "name": project_name,
            "description": f"Posts from {start_date} to {end_date}",
            "status": "Draft",
            "created": datetime.now().strftime("%b %d, %Y"),
            "posts": filtered_posts
        }

        projects_file = f"projects_{st.session_state['fb_id']}.json"
        existing_projects = []
        if os.path.exists(projects_file):
            with open(projects_file, "r") as f:
                existing_projects = json.load(f)
        existing_projects.append(project)
        with open(projects_file, "w") as f:
            json.dump(existing_projects, f, indent=2)

        st.session_state["new_project_added"] = True
        st.session_state["latest_project"] = project
        st.success("🎉 New project created from selected date range!")
        st.switch_page("pages/FbeMyProjects.py")

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()


# ── Helpers
def fetch_data(endpoint, token, since=None, until=None, fields=None):
    if endpoint is None: return {}
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

def download_image(url, name_id):
    ext = url.split("?")[0].split(".")[-1]
    fname = f"{name_id}.{ext}"
    local_path = IMG_DIR / fname
    r = requests.get(url, stream=True, timeout=10)
    if r.status_code == 200:
        with open(local_path, 'wb') as f: shutil.copyfileobj(r.raw, f)
    else: raise Exception(f"Image download failed: {r.status_code}")
    return str(local_path)

def dense_caption(img_path):
    endpoint = st.secrets["AZURE_VISION_ENDPOINT"].rstrip("/") + "/vision/v3.2/analyze?visualFeatures=Description,Tags,Objects"
    headers = {"Ocp-Apim-Subscription-Key": st.secrets["AZURE_VISION_KEY"], "Content-Type": "application/octet-stream"}
    try:
        with open(img_path, "rb") as f: data = f.read()
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

def zip_backup(zip_name):
    zip_path = Path(zip_name)
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for folder, _, files in os.walk(BACKUP_DIR):
            for file in files:
                fp = os.path.join(folder, file)
                arcname = os.path.relpath(fp, BACKUP_DIR)
                zipf.write(fp, arcname)
    return zip_path

# ── UI
st.markdown('<div class="card">', unsafe_allow_html=True)
st.header("📦 Create Facebook Backup")

if "fb_token" not in st.session_state:
    st.error("🔒 Please log in with Facebook first.")
    st.stop()

st.markdown("""<div class="instructions">
<strong>How to create your backup:</strong>
<ol><li><strong>Click "Start My Backup"</strong></li></ol>
<em>Large backups may take several minutes.</em></div>""", unsafe_allow_html=True)

token = st.session_state["fb_token"]

if "start_backup" not in st.session_state:
    st.session_state["start_backup"] = False

if not st.session_state["start_backup"]:
    profile = requests.get(f"https://graph.facebook.com/me?fields=id,name,email&access_token={token}").json()
    fb_name = profile.get("name","user").replace(" ","_")
    if st.button("⬇️ Start My Backup"):
        st.session_state.update({
            "start_backup": True,
            "folder_prefix": f"{fb_name}/"
        })
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ── MAIN BACKUP WORKFLOW
profile = requests.get(f"https://graph.facebook.com/me?fields=id,name,email&access_token={token}").json()
fb_name = profile.get("name","user").replace(" ","_")
folder_prefix = f"{user_input_name or fb_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}/"

bar = st.progress(0.1)

# 1️⃣ Fetch posts & save posts.json
posts = fetch_data("posts", token, fields="id,message,created_time,full_picture")
save_json(posts, "posts")
bar.progress(0.3)

# 2️⃣ Download images + captions -> posts+cap.json
st.info("🔄 Downloading images & generating captions...")
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = []
    for post in posts:
        img_url = post.get("full_picture")
        if img_url:
            try:
                img_path = download_image(img_url, post["id"])
                futures.append(executor.submit(dense_caption, img_path))
                post["picture"] = img_path
            except Exception as e:
                post["picture"] = "download failed"
                post["context_caption"] = f"Image download failed: {e}"
    future_index = 0
    for post in posts:
        if post.get("full_picture"):
            try:
                post["context_caption"] = futures[future_index].result()
            except:
                post["context_caption"] = "caption failed"
            future_index += 1

posts_cap_fp = save_json(posts, "posts+cap")
upload(posts_cap_fp, folder_prefix + "posts+cap.json")
bar.progress(0.7)

# 3️⃣ Summary, zip & final upload
summary = {
    "user": fb_name,
    "user_id": profile.get("id"),
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "posts": len(posts)
}
upload(save_json(summary, "summary"), folder_prefix + "summary.json")
zip_path = zip_backup(f"facebook_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")
bar.empty()
st.success(f"✅ Backup complete! Files archived in {zip_path}")

st.session_state.update({
    "latest_backup": {"Name": fb_name, "Created On": datetime.now().strftime("%b %d, %Y"),
                      "# Posts": len(posts), "Folder": folder_prefix.rstrip("/")},
    "new_backup_done": True, "fb_token": token, "start_backup": False
})
with open("backup_cache.json","w") as f:
    json.dump({"fb_token":token,"latest_backup":st.session_state["latest_backup"],"new_backup_done":True}, f)
st.markdown('</div>', unsafe_allow_html=True)
