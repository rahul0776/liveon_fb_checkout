import streamlit as st
import json, os, requests, zipfile, shutil, concurrent.futures, hashlib
from datetime import datetime, timezone
from pathlib import Path
from azure.storage.blob import BlobServiceClient
from urllib.parse import quote_plus
import random
# ── Config & Styles ────────────────────────────────
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
            '<a href="/FbeMyProjects?tab=backups" target="_self">⇦ Back to Dashboard</a></div>', 
            unsafe_allow_html=True)
# ── Azure & Paths ────────────────────────────────
AZ_CONN = st.secrets["AZURE_CONNECTION_STRING"]
blob_service_client = BlobServiceClient.from_connection_string(AZ_CONN)
CONTAINER = "backup"
BACKUP_DIR = Path("facebook_data")
IMG_DIR = BACKUP_DIR / "images"
BACKUP_DIR.mkdir(exist_ok=True)
IMG_DIR.mkdir(exist_ok=True)
# ── Helpers ────────────────────────────────
def safe_token_hash(token):
    """Return a short hash of the fb_token for safe filenames"""
    return hashlib.md5(token.encode()).hexdigest()
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
def upload_folder(BACKUP_DIR, blob_prefix):
    """Upload entire folder contents to Azure"""
    container = blob_service_client.get_container_client(CONTAINER)
    try: container.create_container()
    except Exception: pass
    for root, _, files in os.walk(BACKUP_DIR):
        for file in files:
            local_path = Path(root) / file
            relative_path = str(local_path.relative_to(BACKUP_DIR))
            blob_path = f"{blob_prefix}/{relative_path}".replace("\\", "/")
            with open(local_path, "rb") as f:
                container.get_blob_client(blob_path).upload_blob(f, overwrite=True)
def download_image(url, name_id):
    #ext = url.split(".")[-1].split("?")[0]
    ext = url.split(".")[-1].split("?")[0]
    if len(ext) > 5 or "/" in ext:  # fallback if invalid
        ext = "jpg"

    fname = f"{name_id}.{ext}"
    local_path = IMG_DIR / fname
    r = requests.get(url, stream=True, timeout=10)
    if r.status_code == 200:
        with open(local_path, 'wb') as f: shutil.copyfileobj(r.raw, f)
    else: raise Exception(f"Image download failed: {r.status_code}")
    return str(local_path)

def generate_blob_url(folder_prefix: str, image_name: str) -> str:
    account_name = blob_service_client.account_name
    return f"https://{account_name}.blob.core.windows.net/{CONTAINER}/{quote_plus(folder_prefix + '/images/' + image_name)}"

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

        result = r.json()

        # ✅ Only the plain caption (no tags/objects)
        caption = result.get("description", {}).get("captions", [{}])[0].get("text", "")
        return caption or ""

        return context_caption

    except requests.exceptions.Timeout:
        return "No caption (timeout)"
    except Exception as e:
        return f"No caption (API error: {str(e)})"


def zip_backup(zip_name):
    zip_path = Path(zip_name)
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for folder, _, files in os.walk(BACKUP_DIR):
            for file in files:
                fp = os.path.join(folder, file)
                arcname = os.path.relpath(fp, BACKUP_DIR)
                zipf.write(fp, arcname)
    return zip_path
# ── UI ────────────────────────────────
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
profile = requests.get(f"https://graph.facebook.com/me?fields=id,name,email&access_token={token}").json()
fb_name = profile.get("name", "user").replace(" ", "_")
fb_id = profile.get("id")
folder_prefix = f"{fb_id}/{fb_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
# ─── Check for Edit Mode ───────────────────────────────
editing_folder = st.session_state.get("editing_backup_folder")
if editing_folder:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("✂️ Edit Backup Duration")
    st.info(f"Editing backup: `{editing_folder}`")
    container = blob_service_client.get_container_client(CONTAINER)
    blob_client = container.get_blob_client(f"{editing_folder}/posts+cap.json")
    
    # ✅ Load posts+cap.json from Azure
    try:
        posts_data = json.loads(blob_client.download_blob().readall())
    except Exception as e:
        st.error(f"Failed to load backup data: {e}")
        st.stop()
    # ✅ Prepare date range
    all_dates = [datetime.fromisoformat(p["created_time"]).date() for p in posts_data if "created_time" in p]
    min_date, max_date = min(all_dates), max(all_dates)
    # ✅ Date range selector
    # ✅ Separate date pickers for start and end
    start_date = st.date_input(
        "📅 Start Date:",
        value=min_date,
        min_value=min_date,
        max_value=max_date
    )
    end_date = st.date_input(
        "📅 End Date:",
        value=max_date,
        min_value=min_date,
        max_value=max_date
    )
    # ✅ Ensure start_date <= end_date
    if start_date > end_date:
        st.warning("⚠️ Start date is after end date. Adjusting end date.")
        start_date, end_date = end_date, start_date


    project_name = st.text_input("📛 Enter Project Name:")
    # ✅ Filter posts based on selected range
    filtered_posts = [
        p for p in posts_data
        if start_date <= datetime.fromisoformat(p["created_time"]).date() <= end_date
    ]
    st.success(f"✅ {len(filtered_posts)} posts selected between {start_date} and {end_date}")
    # ✅ Save filtered posts as a new Project (not Backup)
    if st.button("✨ Create Project and Backup"):
        filtered_posts = [p for p in posts_data if start_date <= datetime.fromisoformat(p["created_time"]).date() <= end_date]
        # ✅ Create a backup folder like normal backups
        user_folder = f"{fb_id}/projects/{project_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        BACKUP_DIR = Path("facebook_data")
        IMG_DIR = BACKUP_DIR / "images"
        # Clean up previous local data
        if BACKUP_DIR.exists():
            shutil.rmtree(BACKUP_DIR)
        BACKUP_DIR.mkdir(exist_ok=True)
        IMG_DIR.mkdir(exist_ok=True)
        # Save filtered posts locally
        posts_fp = BACKUP_DIR / "posts.json"
        posts_fp.write_text(json.dumps(filtered_posts, indent=2, ensure_ascii=False), encoding="utf-8")
        # Download images and generate captions
        st.info("🔄 Downloading images & generating captions...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for post in filtered_posts:
                img_url = post.get("images")[0] if post.get("images") else None
                if img_url:
                    try:
                        img_path = download_image(img_url, post["id"])
                        futures.append(executor.submit(dense_caption, img_path))
                        blob_url_base = "https://fbbackupkhushi.blob.core.windows.net"
                        azure_img_url = generate_blob_url(user_folder, img_path.name)
                        post["picture"] = azure_img_url
                        post["images"] = [azure_img_url]


                    except Exception as e:
                        post["picture"] = "download failed"
                        post["context_caption"] = f"Image download failed: {e}"
            for idx, post in enumerate(filtered_posts):
                if post.get("full_picture"):
                    try:
                        post["context_caption"] = futures[idx].result()
                    except:
                        post["context_caption"] = "caption failed"
        # Save posts+cap.json
        posts_cap_fp = BACKUP_DIR / "posts+cap.json"
        posts_cap_fp.write_text(json.dumps(filtered_posts, indent=2, ensure_ascii=False), encoding="utf-8")
        # Create summary.json
        summary = {
            "user": fb_name,
            "user_id": fb_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "posts": len(filtered_posts)
        }
        summary_fp = BACKUP_DIR / "summary.json"
        summary_fp.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        # ✅ Save additional JSON files
        save_json({"comments": []}, "comments.json")  # Replace with actual comments if you fetch them
        save_json({"likes": []}, "likes.json")        # Replace with actual likes if you fetch them
        save_json({"videos": []}, "videos.json")      # Replace with actual videos if available
        save_json({"profile": {"name": fb_name, "id": fb_id}}, "profile.json")
        st.write("✅ profile.json saved:", (BACKUP_DIR / "profile.json").exists())


        # Upload backup folder to Azure
        upload_folder(BACKUP_DIR, user_folder)
        # ✅ Create project object (linked to this backup)
        project = {
            "id": f"{project_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "name": project_name,
            "description": f"Posts from {start_date} to {end_date}",
            "status": "Draft",
            "created": datetime.now().strftime("%b %d, %Y"),
            "posts": filtered_posts,
            "backup_folder": user_folder  # 👈 Added link to backup
        }
        # Save project locally and upload to Azure
        # Merge new project with existing projects from Azure
        projects_file = f"projects_{fb_id}.json"
        existing_projects = []
        # 🆕 Try to fetch existing projects from Azure first
        try:
            azure_blob = container.get_blob_client(f"{fb_id}/projects/projects_{fb_id}.json")
            if azure_blob.exists():
                azure_data = azure_blob.download_blob().readall().decode("utf-8")
                existing_projects = json.loads(azure_data)
        except Exception as e:
            st.warning(f"Could not fetch existing projects from Azure: {e}")
        # Append new project and avoid duplicates
        if not any(p["id"] == project["id"] for p in existing_projects):
            existing_projects.append(project)
        # Save locally and upload to Azure
        with open(projects_file, "w") as f:
            json.dump(existing_projects, f, indent=2)
        blob_client = container.get_blob_client(f"{fb_id}/projects/projects_{fb_id}.json")
        with open(projects_file, "rb") as f:
            blob_client.upload_blob(f, overwrite=True)


    



        st.success("✅ Project and filtered backup created successfully!")
        # Persist session safely before redirect
        cache_file = Path(f"backup_cache_{fb_id}.json")
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w") as f:
            json.dump({
                "fb_token": token,
                "latest_backup": {
                    "Name": fb_name,
                    "Created On": datetime.now().strftime("%b %d, %Y"),
                    "# Posts": len(posts),
                    "Folder": folder_prefix.rstrip("/"),
                    "user_id": fb_id
                },
                "new_backup_done": True,
                "new_project_added": True
            }, f)
        st.session_state["fb_token"] = token
        st.switch_page("pages/FbeMyProjects.py")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

def extract_image_urls(post):
    urls = set()
    def add(url):
        if url and isinstance(url, str) and url.startswith("http"):
            urls.add(url)
    add(post.get("full_picture"))
    add(post.get("picture"))

    # 🔄 Check attachments too
    att = (post.get("attachments") or {}).get("data", [])
    for a in att:
        media = (a.get("media") or {}).get("image", {})
        add(media.get("src"))
        subs = (a.get("subattachments") or {}).get("data", [])
        for s in subs:
            m = (s.get("media") or {}).get("image", {})
            add(m.get("src"))
    return list(urls)


if st.button("⬇️ Start My Backup"):
    bar = st.progress(0.1)

    # 1️⃣ Fetch posts
    posts = fetch_data("posts", token, fields="id,message,created_time,full_picture,attachments{media}")
    for post in posts:
        post["images"] = extract_image_urls(post)
    save_json(posts, "posts")
    bar.progress(0.3)

    # 2️⃣ Download images & captions
    st.info("🔄 Downloading images & generating captions...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for post in posts:
            img_url = post.get("images")[0] if post.get("images") else None
            if img_url:
                try:
                    img_path = download_image(img_url, post["id"])
                    futures.append(executor.submit(dense_caption, img_path))
                    # local path is img_path; use blob path for dashboard
                    signed_url = generate_blob_url(folder_prefix, img_path.name)
                    post["picture"] = signed_url
                    if "images" not in post:
                        post["images"] = [signed_url]
                    elif signed_url not in post["images"]:
                        post["images"].insert(0, signed_url)



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

    # 3️⃣ Save core files
    save_json(posts, "posts+cap")
    save_json({"comments": []}, "comments.json")
    save_json({"likes": []}, "likes.json")
    save_json({"videos": []}, "videos.json")
    save_json({"profile": {"name": fb_name, "id": fb_id}}, "profile.json")

    # ✅ NEW: Save summary.json (critical for dashboard visibility)
    summary = {
        "user": fb_name,
        "user_id": fb_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "posts": len(posts)
    }
    save_json(summary, "summary")

    bar.progress(0.7)

    # 4️⃣ Upload folder to Azure
    st.info("☁️ Uploading backup to Azure...")
    save_json({"comments": []}, "comments.json")
    save_json({"likes": []}, "likes.json")
    save_json({"videos": []}, "videos.json")
    save_json({"profile": {"name": fb_name, "id": fb_id}}, "profile.json")

    upload_folder(BACKUP_DIR, folder_prefix)

    # Upload ZIP (optional)
    zip_path = zip_backup(f"{fb_name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")
    with open(zip_path, "rb") as f:
        container = blob_service_client.get_container_client(CONTAINER)
        container.get_blob_client(f"{folder_prefix}/{zip_path.name}").upload_blob(f, overwrite=True)

    bar.empty()

    # Clean local backup folder for next use
    shutil.rmtree(BACKUP_DIR)
    BACKUP_DIR.mkdir(exist_ok=True)
    IMG_DIR.mkdir(exist_ok=True)

    # ✅ Save session + cache
    cache_file = Path(f"cache/backup_cache_{hashlib.md5(token.encode()).hexdigest()}.json")
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    latest_backup = {
        "Name": fb_name,
        "Created On": datetime.now().strftime("%b %d, %Y"),
        "# Posts": len(posts),
        "Folder": folder_prefix.rstrip("/"),
        "user_id": fb_id
    }
    with open(cache_file, "w") as f:
        json.dump({
            "fb_token": token,
            "latest_backup": latest_backup,
            "new_backup_done": True
        }, f)

    # ✅ Set Streamlit session state
    st.session_state["fb_token"] = token  # Required for restore_session()
    st.session_state["new_backup_done"] = True
    st.session_state["latest_backup"] = latest_backup
    st.session_state["redirect_to_backups"] = True
    st.session_state["force_reload"] = True
    # ✅ After backup complete
    st.success("✅ Backup complete! 🎉 Your scrapbook is ready to preview!")

    # 📖 Show scrapbook demo preview (sample of posts)
    image_posts = [p for p in posts if p.get("picture") or p.get("images")]
    if image_posts:
        # 🔗 Your Azure Function that selects/embeds posts into chapters
        FUNCTION_URL = "https://liveon-func-app3.azurewebsites.net/api/embed_classify_posts_into_chapters"

        chapters = ["Family & Friends", "Travel", "Work Achievements", "Celebrations", "Milestones"]

        try:
            res = requests.post(
                FUNCTION_URL,
                json={"posts": posts, "chapters": chapters, "max_per_chapter": 2},
                timeout=20
            )
            if res.status_code == 200:
                chapter_posts = res.json()
                # Flatten selected posts from chapters
                sample_posts = []
                for chap in chapter_posts.values():
                    sample_posts.extend(chap)
                # De-dup and limit to 5
                seen_ids, final_posts = set(), []
                for p in sample_posts:
                    pid = p.get("id")
                    if pid and pid not in seen_ids:
                        final_posts.append(p)
                        seen_ids.add(pid)
                sample_posts = final_posts[:5]
            else:
                st.warning("Fallback to random posts because function call failed.")
                sample_posts = random.sample(image_posts, min(5, len(image_posts)))
        except Exception as e:
            st.error(f"Function call failed: {e}")
            sample_posts = random.sample(image_posts, min(5, len(image_posts)))

        st.subheader("📖 Here's a glimpse of your scrapbook:")

        # 3 images per row
        for row_start in range(0, len(sample_posts), 3):
            row_posts = sample_posts[row_start:row_start+3]
            cols = st.columns(len(row_posts))

            for i, post in enumerate(row_posts):
                img_url = None
                if post.get("picture") and post["picture"] != "download failed":
                    img_url = post["picture"]
                elif post.get("images"):
                    first_img = post["images"][0]
                    if isinstance(first_img, str) and first_img.startswith("http"):
                        img_url = first_img

                with cols[i]:
                    if img_url:
                        st.image(img_url, use_container_width=True)
                        desc = post.get("message") or post.get("context_caption") or ""
                        if desc:
                            st.caption(desc)
                    else:
                        st.warning("No valid image available for this post.")

    # ✅ Next actions
    st.markdown("---")
    st.info("What would you like to do next?")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💳 Proceed to Payment"):
            st.switch_page("pages/FB_Backup.py")  # your payment page

    with col2:
        if st.button("← Back to My Projects"):
            st.switch_page("pages/FbeMyProjects.py")

    st.markdown('</div>', unsafe_allow_html=True)
