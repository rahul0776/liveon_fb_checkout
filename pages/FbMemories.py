
import streamlit as st  # type: ignore
import requests
import json
import re
from datetime import datetime
import os
from azure.storage.blob import BlobServiceClient  # type: ignore
def restore_session():
    """Restore session from cache if available"""
    cache_file = "backup_cache.json"
    if not all(key in st.session_state for key in ["fb_id", "fb_name", "fb_token"]):
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r") as f:
                    cached = json.load(f)
                    st.session_state.update({
                        "fb_token": cached.get("fb_token"),
                        "fb_id": cached.get("latest_backup", {}).get("user_id"), 
                        "fb_name": cached.get("latest_backup", {}).get("name"),
                        "latest_backup": cached.get("latest_backup"),
                        "new_backup_done": cached.get("new_backup_done")
                    })
            except Exception as e:
                st.error(f"Session restore error: {str(e)}")
restore_session()
if "fb_token" not in st.session_state:
    st.warning("Please login with Facebook first.")
    st.stop()
# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="🧠 Facebook Memories", layout="wide")

# Global dark‑theme tweaks to better match the PDF aesthetic
st.markdown(
    """
    <style>
        .main {background:#0e1117;}
        h1, h2, h3, h4, .stMarkdown {color:#FFFFFFDD; text-align:center;}
        .stSpinner > div > div {color:#3366cc;}
        .chapter-title {margin-top:2rem;margin-bottom:1rem;font-size:1.8rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ── CONSTANTS ──────────────────────────────────────────────────────────────────
FUNCTION_BASE = "http://localhost:7071/api"
CONNECT_STR   = st.secrets["AZURE_CONNECTION_STRING"]
CONTAINER     = "backup"

# ── FOLDER SELECTION ────────────────────────────────────────────────────────────
blob_service_client = BlobServiceClient.from_connection_string(CONNECT_STR)
container_client = blob_service_client.get_container_client(CONTAINER)
blob_names = [blob.name for blob in container_client.list_blobs()]
folders = sorted(list(set(name.split("/")[0] for name in blob_names if "/" in name)), reverse=True)

# ── FOLDER SELECTION ─────────────────────────────────────────────────────────
if "selected_backup" not in st.session_state:
    st.session_state["selected_backup"] = folders[0] if folders else None

current_folder = st.session_state["selected_backup"]
default_index = folders.index(current_folder) if current_folder in folders else 0

selected_backup = st.sidebar.selectbox(
    "📁 Choose a Backup Folder",
    folders,
    index=default_index
)
st.session_state["selected_backup"] = selected_backup


# ── HELPERS ────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_all_posts_from_blob(container: str, folder: str) -> list[dict]:
    blob_service_client = BlobServiceClient.from_connection_string(CONNECT_STR)
    container_client = blob_service_client.get_container_client(container)

    all_posts: list[dict] = []
    blobs = list(container_client.list_blobs(name_starts_with=f"{folder}/"))

    priority_files = []
    fallback_files = []

    for blob in blobs:
        if not blob.name.endswith(".json") or "posts" not in blob.name:
            continue
        if "posts+cap.json" in blob.name:
            priority_files.append(blob)
        else:
            fallback_files.append(blob)

    for blob in priority_files + fallback_files:
        blob_text = (
            blob_service_client
            .get_blob_client(container, blob.name)
            .download_blob()
            .readall()
            .decode("utf-8")
        )
        try:
            data = json.loads(blob_text)
            if isinstance(data, list):
                all_posts.extend(data)
            elif isinstance(data, dict) and isinstance(data.get("data"), list):
                all_posts.extend(data["data"])
        except json.JSONDecodeError:
            continue

        break

    return all_posts



def call_function(endpoint:str, payload:dict, timeout:int=90):
    url = f"{FUNCTION_BASE}/{endpoint}"
    try:
        res = requests.post(url, json=payload, timeout=timeout)
        res.raise_for_status()
        return res
    except requests.exceptions.RequestException as err:
        st.error(f"❌ Azure Function error: {err}")
        st.stop()

def extract_titles(ai_text:str) -> list[str]:
    def _clean(t:str) -> str:
        t = t.strip()
        t = re.sub(r"^[•\-–\d\.\s]+", "", t)
        t = re.sub(r'^[\"“”]+|[\"“”]+$', '', t)
        return t.strip()

    titles: list[str] = []
    for raw in ai_text.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        m = re.match(r"chapter\s*\d+[:\-]?\s*[\"“]?(.+?)[\"”]?$", raw, re.I)
        if m:
            titles.append(_clean(m.group(1)))
            continue
        m = re.match(r"(\d+\.|[•\-–])\s+(.+)$", raw)
        if m:
            titles.append(_clean(m.group(2)))
            continue
        m = re.match(r'[\"“](.+?)[\"”]$', raw)
        if m:
            titles.append(_clean(m.group(1)))
            continue
    return list(dict.fromkeys([t for t in titles if t]))

def render_chapter_grid(chapter: str, posts: list[dict]):
    st.markdown(f"<div class='chapter-title'>📖 {chapter}</div>", unsafe_allow_html=True)
    if not posts:
        st.info("No posts matched this chapter yet.")
        return

    # Step 1: Process and deduplicate all items
    processed_items = []
    seen_hashes = set()
    
    for post in posts:
        # Create unique content hash using multiple fields
        message = (post.get("message") or "").strip()
        context = (post.get("context_caption") or "").strip()
        created_time = post.get("created_time", "")[:10]  # Just date part
        
        # Build caption
        if message and context:
            caption = f"{message} — 🧠 {context}"
        elif message:
            caption = message
        elif context:
            caption = f"🧠 {context}"
        else:
            caption = "📷"

        # Get all valid image URLs
        images = []
        if "normalized_images" in post:  # Using pre-processed images
            images = [img for img in post["normalized_images"] if img.startswith("http")]
        
        # Create unique hash for this post (combines text and first image)
        content_hash = hash((caption, created_time, images[0] if images else ""))
        if content_hash in seen_hashes:
            continue
        seen_hashes.add(content_hash)

        # Add all images as separate items (but marked as same post)
        if images:
            for img_url in images:
                processed_items.append({
                    "type": "image",
                    "content": img_url,
                    "caption": caption,
                    "hash": content_hash
                })
        else:
            processed_items.append({
                "type": "text", 
                "content": "",
                "caption": caption,
                "hash": content_hash
            })

    # Step 2: Render the items in a grid
    if not processed_items:
        st.info("No displayable content for this chapter.")
        return

    # Special case: single item gets centered
    if len(processed_items) == 1:
        item = processed_items[0]
        if item["type"] == "image":
            st.image(item["content"], caption=item["caption"][:100], use_container_width=True)
        else:
            st.markdown(f"💬 *{item['caption']}*")
        return

    # Grid layout with 3 columns
    cols = st.columns(3)
    col_index = 0
    
    # Track last rendered hash to avoid consecutive duplicates
    last_hash = None
    
    for item in processed_items:
        # Skip if this is the same as the immediately previous item
        if item["hash"] == last_hash:
            continue
            
        with cols[col_index]:
            if item["type"] == "image":
                st.image(item["content"], 
                        caption=item["caption"][:100], 
                        use_container_width=True)
            else:
                st.markdown(f"💬 *{item['caption']}*")
        
        last_hash = item["hash"]
        col_index = (col_index + 1) % 3

# ── UI ─────────────────────────────────────────────────────────────────────────

st.title("🧠 AI‑Curated Facebook Memories")
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    advanced_mode = st.checkbox("Enable Advanced Mode (debug)", value=False)
    if st.button("🔄 Reload Posts"):
        st.cache_data.clear(); st.rerun()

st.caption("Loading your Facebook posts from Azure Blob Storage…")
try:
    posts = load_all_posts_from_blob(CONTAINER, selected_backup)
    if not posts:
        st.warning("⚠️ No posts found in blob storage. Upload some and try again.")
        st.stop()
    st.success(f"✅ Loaded {len(posts)} posts from {selected_backup}.")

except Exception as e:
    st.error("❌ Could not fetch blobs.")
    st.exception(e)
    st.stop()


for post in posts:
    message = (post.get("message") or "").strip()
    caption = (post.get("context_caption") or "").strip()
    combined_text = message
    if caption and caption not in message:
        combined_text += f" — {caption}"
    post["combined_text"] = combined_text or "📷"
    imgs = []
    if "images" in post:
        imgs = post["images"]
    elif "full_picture" in post and post["full_picture"].startswith("http"):
        imgs = [post["full_picture"]]
    elif "picture" in post and post["picture"].startswith("http"):
        imgs = [post["picture"]]
    post["normalized_images"] = imgs
# ── PRIMARY ACTION ────────────────────────────────────────────────────────────
if st.button("📘 Generate Scrapbook",use_container_width=True):
    # 1️⃣ Evaluate personality & life themes
    eval_prompt = (
        "Evaluate this person holistically based on their Facebook post history. "
        "Use both their original post messages and the context captions (context_caption) generated from their images. "
        "Consider emotional tone, recurring values, life priorities, behaviors, mindset, and expression style. "
        "Then summarize this evaluation into key themes and areas of their personality."
    )

    with st.spinner("🔍 Evaluating personality and life themes…"):
        eval_res  = call_function("ask_about_blob",{"question":eval_prompt,"posts":posts})
        eval_text = eval_res.text
    st.markdown("### 🧠 Personality Evaluation Summary"); st.markdown(eval_text)

    # 2️⃣ Ask for chapter suggestions
    with st.spinner("📚 Generating scrapbook chapters from evaluation…"):
        followup_res = call_function("ask_followup_on_answer",{
            "previous_answer":eval_text,
            "question":"Based on this evaluation, what would be good thematic chapter titles for a scrapbook of this person’s life?",
        })
        followup_text = followup_res.text
    st.markdown("### 🗂️ Suggested Chapter Themes"); st.markdown(followup_text)
    
        # 3️⃣ Extract chapter titles
    chapters = extract_titles(followup_text)
    if advanced_mode:
        st.write("**Parsed chapters:**", chapters)
    if not chapters:
        st.warning("We couldn't organize these memories yet. Try uploading more posts.")
        st.stop()

    
    with st.spinner("🧩 Organizing posts into chapters…"):
        classify_res = call_function("embed_classify_posts_into_chapters", {
            "chapters": chapters,
            "posts": posts,
            "max_per_chapter": 6,
        }, timeout=120)
        classification = classify_res.json()

    if "error" in classification:
        st.error("GPT classification failed.")
        if advanced_mode:
            st.code(classification.get("raw_response", ""))
        st.stop()

    # 5️⃣ Render each chapter with images and captions
    seen: set[tuple[str, str, str]] = set()  # moved outside loop to dedup globally

    for chap in chapters:
        st.markdown(f"### 📚 {chap}")
        chapter_posts = classification.get(chap, [])
        if not chapter_posts:
            st.info("No posts matched this chapter.")
            continue

        cols = st.columns(3)
        idx = 0

        for p in chapter_posts:
            message = (p.get("message") or "").strip()
            context = (p.get("context_caption") or "").strip()
            created_on = p.get("created_time", "")[:10]

            if message and context:
                caption = f"{message} — 🧠 {context}"
            elif message:
                caption = message
            elif context:
                caption = f"🧠 {context}"
            else:
                caption = ""

            images = p.get("images", [])
            if not images and "image" in p:
                images = [p["image"]]

            # Skip if absolutely empty
            if not caption and not images:
                continue

            # Render images first
            if images:
                for img_url in images:
                    if not img_url.startswith("http"):
                        continue
                    key = (caption, img_url, p.get("created_time", ""))
                    if key in seen:
                        continue
                    seen.add(key)
                    with cols[idx]:
                        st.image(img_url, caption=caption[:80] or "📷", use_container_width=True)
                    idx = (idx + 1) % 3
            else:
                # Render text only if unique
                key = (caption, "", p.get("created_time", ""))
                if key in seen or not caption.strip():
                    continue
                seen.add(key)
                with cols[idx]:
                    st.markdown(f"💬 *{caption}*")
                idx = (idx + 1) % 3

    st.success("🎉 Scrapbook complete!")