import streamlit as st  # type: ignore
import requests
import json
import re
from datetime import datetime, timedelta
import os
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from urllib.parse import quote_plus
from azure.storage.blob import BlobServiceClient  # type: ignore
from urllib.parse import urlparse, urlunparse  # 🆕 For URL normalization

def sign_blob_url(blob_path: str) -> str:
    try:
        account_name = blob_service_client.account_name
        sas = generate_blob_sas(
            account_name=account_name,
            container_name=CONTAINER,
            blob_name=blob_path,
            account_key=blob_service_client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=1)
        )
        return f"https://{account_name}.blob.core.windows.net/{CONTAINER}/{quote_plus(blob_path)}?{sas}"
    except Exception as e:
        return "https://via.placeholder.com/600x400?text=Image+Unavailable"


# 🆕 Normalize URLs to remove query params for deduplication
def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    clean = parsed._replace(query="", fragment="")
    return urlunparse(clean)

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

# ── PAGE CONFIG ────────────────────────────────────────────────
st.set_page_config(page_title="🧠 Facebook Memories", layout="wide")

# 🆕 Global dark-theme tweaks
st.markdown(
    """
    <style>
        .main {background:#0e1117;}
        h1, h2, h3, h4, .stMarkdown {color:#FFFFFFDD; text-align:center;}
        .stSpinner > div > div {color:#3366cc;}
        .chapter-title {
            margin-top:2rem;
            margin-bottom:1rem;
            font-size:1.8rem;
            color:#f5f5f5;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── CONSTANTS ────────────────────────────────────────────────
FUNCTION_BASE = "https://liveon-func-app3.azurewebsites.net/api"
CONNECT_STR   = st.secrets["AZURE_CONNECTION_STRING"]
CONTAINER     = "backup"

blob_service_client = BlobServiceClient.from_connection_string(CONNECT_STR)
container_client = blob_service_client.get_container_client(CONTAINER)
blob_names = [blob.name for blob in container_client.list_blobs()]
folders = sorted(list(set(name.split("/")[0] for name in blob_names if "/" in name)), reverse=True)

default_index = 0
if "selected_backup" in st.session_state:
    try: default_index = folders.index(st.session_state.pop("selected_backup"))
    except: pass
selected_backup = st.sidebar.selectbox("📁 Choose a Backup Folder", folders, index=default_index)

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

# if st.sidebar.button("🧪 Test ask_about_blob manually"):
#     debug_payload = {
#         "question": "Who is this person based on their Facebook posts?",
#         "posts": posts[:5]  # Send only first 5 posts to test
#     }
#     try:
#         res = call_function("ask_about_blob", debug_payload)
#         st.code(res.text)
#     except Exception as e:
#         st.error("❌ Azure Function test failed")
#         st.exception(e)
# ── HELPERS ────────────────────────────────────────────────
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


# 🆕 Fixed render_chapter_grid with fallback image and deduplication
def render_chapter_grid(chapter: str, posts: list[dict]):
    st.markdown(f"<div class='chapter-title'>📖 {chapter}</div>", unsafe_allow_html=True)
    if not posts:
        return  # Skip empty chapters

    all_items = []
    seen: set[str] = set()

    for p in posts:
        message = (p.get("message") or "").strip()
        context = (p.get("context_caption") or "").strip()
        caption = f"{message} — 🧠 {context}" if message and context else (message or context or "📷")

        images = p.get("images", [])
        if not images:
            images = ["https://via.placeholder.com/300x200?text=No+Image+Available"]

        for img in images:
            if img.startswith("http") and "?" in img:
                url = normalize_url(img)  # already signed
            else:
                url = normalize_url(sign_blob_url(img))  # sign the blob path

            if url not in seen:
                seen.add(url)
                all_items.append(("image", url, caption))

    # 4-column grid layout
    cols = st.columns([1, 1, 1, 1])
    for idx, (kind, img_url, caption) in enumerate(all_items):
        with cols[idx % 4]:
            if kind == "image":
                try:
                    st.image(img_url, caption=caption[:80], use_container_width=True)
                except:
                    st.image("https://via.placeholder.com/600x400?text=Image+Unavailable", caption=caption[:80], use_container_width=True)




# 🆕 CHANGE: Dynamic max_per_chapter calculation
def calculate_max_per_chapter(chapters, posts):
    posts_per_page = 3
    target_pages = 50
    total_posts = posts_per_page * target_pages
    chapters_count = len(chapters)
    return total_posts // chapters_count

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
    # 🆕 Get user name and gender from session/profile
    # 🆕 Read name from profile.json (stateless per user)
    try:
        blob_client = container_client.get_blob_client(f"{selected_backup}/profile.json")
        blob_data = blob_client.download_blob().readall()
        profile_data = json.loads(blob_data.decode("utf-8"))
        user_name = profile_data.get("name", "This person")
    except Exception as e:
        user_name = "This person"
    user_gender = st.session_state.get("fb_gender", "unspecified").lower()

    # 🆕 Decide pronouns
    if user_gender == "female":
        pronoun_subject = "she"
        pronoun_object = "her"
        pronoun_possessive = "her"
    elif user_gender == "male":
        pronoun_subject = "he"
        pronoun_object = "him"
        pronoun_possessive = "his"
    else:
        pronoun_subject = "they"
        pronoun_object = "them"
        pronoun_possessive = "their"

    # 🆕 Refined prompt
    eval_prompt = f"""
    Write a scrapbook personality summary for {user_name} based on their Facebook post history

    Use both their original post messages and the context captions (context_caption) generated from their images.

    ⚠️ IMPORTANT:
    - The first sentence must start with "{user_name}" (e.g., "{user_name} is a warm and reflective individual…").
    - After that, use pronouns naturally:
    - Subject: {pronoun_subject}
    - Object: {pronoun_object}
    - Possessive: {pronoun_possessive}
    - Do NOT use generic phrases like "This person" or "The individual."
    - Start with "{user_name}" in the first sentence (e.g., "{user_name} is a thoughtful and vibrant individual...").
    - After that, use pronouns naturally (he/she/they).
    - Make it sound warm, reflective, and personal, like it’s written for a scrapbook.


    Consider emotional tone, recurring values, life priorities, behaviors, mindset, and expression style.

    Then summarize this evaluation into key themes and areas of {user_name}'s personality.
    """


    with st.spinner("🔍 Evaluating personality and life themes…"):
        try:
            st.write(f"🧪 Sending {len(posts)} posts to `ask_about_blob`")
            # st.write(f"Prompt preview:\n{eval_prompt[:500]}...")  # optional
            eval_res = call_function("ask_about_blob", {
                "question": eval_prompt,
                "posts": posts
            })
            eval_text = eval_res.text
        except Exception as e:
            st.error("❌ Failed to get personality summary from Azure Function.")
            st.exception(e)
            st.stop()
    st.markdown("### 🧠 Personality Evaluation Summary"); st.markdown(eval_text)

    # 🆕 Refined GPT p   rompt to avoid odd/empty chapters
    refined_question = """
    Based on this evaluation, suggest thematic chapter titles for a scrapbook of this person’s life.

    ⚠️ IMPORTANT:
    - Only suggest chapter titles if there are specific Facebook posts that support them.
    - Avoid creating abstract or aspirational themes unless there are posts clearly matching them.
    - Ensure every chapter can be populated with posts.
    - Prefer practical and relatable themes over vague concepts.
    """

    # 2️⃣ Ask for chapter suggestions

    with st.spinner("📚 Generating scrapbook chapters from evaluation…"):
        st.write("📤 Sending to followup function", {
            "previous_answer": eval_text[:300],
            "question": "Based on this evaluation, suggest thematic chapter titles..."
        })
        followup_res = call_function("ask_followup_on_answer", {
            "previous_answer": eval_text,
            "question": """
        Based on this evaluation, suggest thematic chapter titles for a scrapbook of this person’s life.

        ⚠️ IMPORTANT:
        - Only suggest chapter titles if there are Facebook posts that support them.
        - Avoid creating abstract or philosophical chapter names unless there are posts that clearly fit those themes.
        - Each chapter should be grounded in observable events, emotions, or patterns in the posts.
        - Prefer practical and relatable themes over vague concepts.

        Respond with a list of chapter titles only.
        """
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

    
    max_per_chapter = calculate_max_per_chapter(chapters, posts)  # 🆕 CHANGE: Dynamic max_per_chapter
    with st.spinner("🧩 Organizing posts into chapters…"):
        # 🆕 Dynamically calculate max_per_chapter for big backups
        posts_per_page = 6
        target_pages = 100  # Allow large, photo-heavy scrapbooks
        total_posts = posts_per_page * target_pages
        chapters_count = len(chapters)
        max_per_chapter = total_posts // chapters_count
        
        filtered_posts = []
        for p in posts:
            imgs = p.get("images", []) or p.get("normalized_images", []) or []
            signed_imgs = []

            for img in imgs:
                if "blob.core.windows.net" in img and "?" in img:
                    # Already signed
                    signed_imgs.append(img)
                elif "blob.core.windows.net" in img:
                    # Needs signing
                    try:
                        # Extract path after container
                        parsed = urlparse(img)
                        blob_path = parsed.path.split(f"/{CONTAINER}/")[-1]
                        signed_img = sign_blob_url(blob_path)
                        signed_imgs.append(signed_img)
                    except:
                        continue
                elif not img.startswith("http"):
                    # It's a raw blob path
                    try:
                        signed_imgs.append(sign_blob_url(img))
                    except:
                        continue

            if signed_imgs:
                p["images"] = signed_imgs
                filtered_posts.append(p)

        if advanced_mode:
            st.code(json.dumps(filtered_posts[:2], indent=2))

        if not filtered_posts:
            st.error("❌ No valid posts with blob image URLs found. Cannot classify into chapters.")
            st.stop()

        # 🧠 Debug output
        if advanced_mode:
            st.write(f"🧪 Filtered to {len(filtered_posts)} posts with blob image URLs")

        # Call Azure Function
        classify_res = call_function("embed_classify_posts_into_chapters", {
            "chapters": chapters,
            "posts": filtered_posts,
            "max_per_chapter": max_per_chapter
        }, timeout=300)

        try:
            classification = classify_res.json()
        except json.JSONDecodeError:
            st.error("⚠️ Classification function did not return valid JSON.")
            st.code(classify_res.text)
            st.stop()

        if "error" in classification:
            st.error("⚠️ GPT classification failed.")
            if advanced_mode:
                st.code(classification.get("raw_response", ""))
            st.stop()

    # 🆕 Filter out empty chapters
    non_empty_chapters = [c for c in chapters if classification.get(c)]
    if not non_empty_chapters:
        st.warning("No chapters had matching posts.")
        st.stop()

    if "error" in classification:
        st.error("GPT classification failed.")
        if advanced_mode:
            st.code(classification.get("raw_response", ""))
        st.stop()

    # 5️⃣ Render each chapter with images and captions
    for chap in chapters:
        st.markdown(f"### 📚 {chap}")
        chapter_posts = classification.get(chap, [])
        if not chapter_posts:
            st.info("No posts matched this chapter.")
            continue
        cols = st.columns(3)
        idx = 0
        seen: set[tuple[str, str]] = set()
        for p in chapter_posts:
            message = (p.get("message") or "").strip()
            context = (p.get("context_caption") or "").strip()
            if message and context:
                caption = f"{message} — 🧠 {context}"
            elif message:
                caption = message
            elif context:
                caption = f"🧠 {context}"
            else:
                caption = "📷"
            images = p.get("images", [])
            if not images and "image" in p:
                images = [p["image"]]
            if images:
                for img_url in images:
                    signed_url = img_url  # It’s already a good URL from posts+cap.json

                    key = (caption, signed_url)
                    if key in seen:
                        continue
                    seen.add(key)
                    with cols[idx]:
                        st.image(signed_url, caption=caption[:80], use_container_width=True)
                    idx = (idx + 1) % 3

            else:
                key = (caption, "")
                if key in seen:
                    continue
                seen.add(key)
                with cols[idx]:
                    st.markdown(f"💬 *{caption}*")
                idx = (idx + 1) % 3

    st.success("🎉 Scrapbook complete!")