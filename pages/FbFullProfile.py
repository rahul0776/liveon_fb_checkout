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
:root{
  --navy-900:#0F253D;     /* deep background */
  --navy-800:#143150;
  --navy-700:#1E3A5F;
  --navy-500:#2F5A83;
  --gold:#F6C35D;         /* brand accent */
  --text:#F3F6FA;         /* off-white text */
  --muted:#B9C6D6;        /* secondary text */
  --card:#112A45;         /* card background */
  --line:rgba(255,255,255,.14);
}

/* Page base */
html, body, .stApp{
  background: linear-gradient(180deg, var(--navy-900) 0%, var(--navy-800) 55%, var(--navy-700) 100%);
  color: var(--text);
  font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

/* Top bar */
.topbar{
  display:flex;justify-content:space-between;align-items:center;
  background: rgba(255,255,255,.04);
  padding:12px 24px;border-bottom:1px solid var(--line);
  font-size:15px;position:sticky;top:0;z-index:998;color:var(--text);
}
.topbar a{color:var(--gold);font-weight:700;text-decoration:none;}
.topbar a:hover{filter:brightness(.95);}

/* Cards */
.card{
  background: var(--card);
  border:1px solid var(--line);
  border-radius:12px;
  box-shadow:0 10px 24px rgba(0,0,0,.18);
  max-width:720px;           /* a little wider looks better */
  margin:40px auto;
  padding:34px 32px;
}

/* Headings */
h1,h2,h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3{
  color:var(--text) !important;
  letter-spacing:.25px;
}

/* Primary buttons */
.stButton>button{
  background: var(--gold);
  color: var(--navy-900);
  border:none;
  padding:12px 0;
  border-radius:10px;
  font-weight:800;
  font-size:15px;
  width:100%;
  box-shadow:0 4px 14px rgba(246,195,93,.22);
  transition: transform .15s ease, filter .15s ease, box-shadow .15s ease;
}
.stButton>button:hover{
  transform: translateY(-1px);
  filter:brightness(.95);
  box-shadow:0 6px 18px rgba(246,195,93,.28);
}

/* Instructions callout */
.instructions{
  background: rgba(255,255,255,.06);
  border-left:4px solid var(--gold);
  padding:12px 16px;margin:16px 0;font-size:14px;color:var(--muted);
}

/* Alerts that blend with dark theme */
div[data-testid="stAlert"]{
  font-weight:600;border-left:4px solid var(--gold) !important;
  background: rgba(255,255,255,.06) !important;color:var(--text) !important;
}
div[data-testid="stAlert"] * {color:var(--text) !important;}
div[data-testid="stAlert"]:has(svg[data-testid="stIcon-success"]){ border-left-color:#45d07e !important;}
div[data-testid="stAlert"]:has(svg[data-testid="stIcon-warning"]){ border-left-color:#ffcf66 !important;}
div[data-testid="stAlert"]:has(svg[data-testid="stIcon-error"]){ border-left-color:#ff6b6b !important;}

/* Progress bar in gold */
.stProgress [role="progressbar"] > div{ background: var(--gold) !important; }

/* Inputs on dark bg (date inputs, text, etc.) */
input, textarea, select{
  background: rgba(255,255,255,.06) !important;
  border:1px solid var(--line) !important;
  color: var(--text) !important;
  border-radius:10px !important;
}
label, .stMarkdown, .stCaption, .st-emotion-cache-1n76uvr{ color: var(--muted) !important; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="topbar"><div><strong>LiveOn</strong> · Backup&nbsp;Process</div>'
            '<a href="/Projects?tab=backups" target="_self">⇦ Back to Dashboard</a></div>', 
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
    return local_path

def generate_blob_url(folder_prefix: str, image_name: str) -> str:
    account_name = blob_service_client.account_name
    return (
        f"https://{account_name}.blob.core.windows.net/"
        f"{CONTAINER}/{folder_prefix}/images/{quote_plus(image_name)}"
    )

def dense_caption(img_path):
    endpoint = st.secrets["AZURE_VISION_ENDPOINT"].rstrip("/") + \
               "/vision/v3.2/analyze?visualFeatures=Description,Tags,Objects"
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
        captions = (result.get("description", {}).get("captions") or [{}])
        return captions[0].get("text", "") or ""
    except requests.exceptions.Timeout:
        return "No caption (timeout)"
    except Exception as e:
        return f"No caption (API error: {e})"

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
        futures = []  # (post, future) to keep alignment
        for post in posts:
            img_url = post.get("images")[0] if post.get("images") else None
            if not img_url:
                continue
            try:
                img_path = download_image(img_url, post["id"])
                futures.append((post, executor.submit(dense_caption, img_path)))

                # local path is img_path; use blob path for dashboard
                signed_url = generate_blob_url(folder_prefix, Path(img_path).name)
                post["picture"] = signed_url
                post.setdefault("images", [])
                if signed_url not in post["images"]:
                    post["images"].insert(0, signed_url)
            except Exception as e:
                post["picture"] = "download failed"
                post["context_caption"] = f"Image download failed: {e}"

        # ✅ Responsive progress while collecting results
        total = max(1, len(futures))
        for i, (post, fut) in enumerate(futures, start=1):
            try:
                post["context_caption"] = fut.result()
            except Exception:
                post["context_caption"] = "caption failed"
            # grow bar from 0.30 → 0.70 as captions complete
            bar.progress(0.30 + 0.40 * (i / total))


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
    st.switch_page("pages/Projects.py")
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
            st.switch_page("pages/Projects.py")

    st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)