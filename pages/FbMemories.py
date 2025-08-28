#Khushi's version
import streamlit as st  # type: ignore
import requests
import json
import re
from datetime import datetime, timedelta
import os
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from urllib.parse import quote, urlparse, urlunparse
from azure.storage.blob import BlobServiceClient  # type: ignore
import hashlib
import time 
from io import BytesIO

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from uuid import uuid4
from pathlib import Path
from textwrap import wrap


try:
    from PIL import Image as PILImage
    _HAVE_PIL = True
except Exception:
    _HAVE_PIL = False



# ── PAGE CONFIG ────────────────────────────────────────────────
st.set_page_config(page_title="🧠 Facebook Memories", layout="wide")

# from utils.theme import inject_global_styles




# inject_global_styles()
st.markdown("""
<style>
/* ====== Minimal Dark Theme (same as your current memories page) ====== */
html, body, .stApp { background:#0e1117; }
h1, h2, h3, h4, .stMarkdown { color:#FFFFFFDD; text-align:center; }
.stSpinner > div > div { color:#3366cc; }

/* Chapter title pill (kept from your current page) */
.chapter-title{
  margin-top:2rem;
  margin-bottom:1rem;
  font-size:1.8rem;
  color:#f5f5f5;
}

/* --- Light styling to preserve Khushi layout classes --- */
/* Cards & grids (kept so your promo and image grids don’t break) */
.card{
  background:rgba(255,255,255,.06);
  border:1px solid rgba(255,255,255,.14);
  border-radius:14px;
  padding:18px;
  box-shadow:0 10px 24px rgba(0,0,0,.18);
  margin-bottom:18px;
}
.grid-3{ display:grid; grid-template-columns: repeat(3,1fr); gap:16px; }
@media (max-width:1100px){ .grid-3{ grid-template-columns: repeat(2,1fr);} }
@media (max-width:700px){ .grid-3{ grid-template-columns:1fr; } }
.section-title{
  font-size:1.25rem; font-weight:800; margin:22px 0 10px;
  text-align:left; color:#FFFFFFDD;
}
.muted{ color:#AEB5C0; }
.badge{
  display:inline-block; padding:6px 12px; border-radius:999px;
  background:rgba(255,255,255,.08); color:#f5f5f5; font-weight:700;
}

/* Buttons: subtle dark theme button that matches your current page */
.stButton>button{
  background:#1f2937 !important;
  color:#FFFFFFDD !important; font-weight:700 !important;
  padding:10px 18px !important; border-radius:8px !important; border:1px solid rgba(255,255,255,.14) !important;
}
.stButton>button:hover{ filter:brightness(1.08); }

/* Keep promo tiles compact but dark-themed */
.promo-wrap{ max-width:1100px; margin:14px auto 20px; display:grid; grid-template-columns:1fr 1.2fr; gap:18px; }
@media (max-width:900px){ .promo-wrap{ grid-template-columns:1fr; } }
.promo-grid{ display:grid; grid-template-columns: repeat(3, 1fr); gap:12px; }
.promo-card{
  background:rgba(255,255,255,.06);
  border:1px solid rgba(255,255,255,.14);
  border-radius:12px; overflow:hidden;
  box-shadow:0 6px 16px rgba(0,0,0,.15);
}
.promo-card img{ display:block; width:100%; height:120px; object-fit:cover; }
.promo-card .caption{
  padding:8px 10px; font-weight:700; font-size:.9rem; color:#FFFFFFDD;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
}
.promo-copy{
  background:rgba(255,255,255,.06);
  border:1px solid rgba(255,255,255,.14);
  border-radius:12px; padding:16px 18px;
  box-shadow:0 6px 16px rgba(0,0,0,.15);
}

/* Hide default spinner SVG to match the original page */
div[data-testid="stSpinner"] svg { display:none !important; }
</style>
""", unsafe_allow_html=True)


# --- Promo asset paths (local) ---
PROMO1 = "media/LiveOn-Logo20.png"
PROMO2 = "media/image.png"
PROMO3 = "media/image (1).png"





def make_button_key(prefix, *parts):
    raw = prefix + "|" + "|".join(str(p) for p in parts)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def generate_unique_key(*args):
    """Generate a unique key using hash of arguments and timestamp"""
    base = "_".join(str(arg) for arg in args) + f"_{time.time_ns()}"
    return hashlib.md5(base.encode('utf-8')).hexdigest()

def stable_uuid_suffix(chap: str, post_idx: int, img_idx: int, img_url: str) -> str:
    """Return a stable UUID suffix per (chapter, post, image, url)."""
    k = f"{chap}|{post_idx}|{img_idx}|{normalize_url(img_url)}"
    store = st.session_state.setdefault("_uuid_for_keys", {})
    if k not in store:
        store[k] = uuid4().hex[:8]  # short, readable, and stable after first assignment
    return store[k]



def make_safe_key(chap, idx, img_url):
    """Generate a unique and safe Streamlit key using a hash."""
    base = f"{chap}_{idx}_{img_url}"
    return hashlib.md5(base.encode("utf-8")).hexdigest()

def sign_blob_url(blob_path: str) -> str:
    try:
        account_name = blob_service_client.account_name
        sas = generate_blob_sas(
            account_name=account_name,
            container_name=CONTAINER,
            blob_name=blob_path,
            account_key=blob_service_client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=24)
        ) 
        return f"https://{account_name}.blob.core.windows.net/{CONTAINER}/{quote(blob_path, safe='/')}?{sas}"

    except Exception as e:
        return "https://via.placeholder.com/600x400?text=Image+Unavailable"

# 🆕 Normalize URLs to remove query params for deduplication
def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    clean = parsed._replace(query="", fragment="")
    return urlunparse(clean)

def _cap(s) -> str:
    """Always return a safe, non-None caption string."""
    if s is None:
        return ""
    s = str(s).strip()
    return "" if s.lower() == "none" else s

def _text(s) -> str:
    if s is None: 
        return ""
    s = str(s).strip()
    return "" if s.lower() in {"none","null","undefined","na","n/a"} else s

def compose_caption(message, context):
    m = _text(message)
    c = _text(context)
    if m and c: 
        return f"{m} — 🧠 {c}"
    return m or (f"🧠 {c}" if c else "📷")

def _craft_caption_via_function(message: str, context: str) -> str:
    try:
        msg = _text(message)
        ctx = _text(context)
        if not msg and not ctx:
            return "📷"
        key = st.secrets.get("CRAFT_CAPTION_KEY") or os.environ.get("CRAFT_CAPTION_KEY", "")
        url = f"{FUNCTION_BASE}/craft_caption" + (f"?code={key}" if key else "")
        r = requests.post(url, json={"message": msg, "context": ctx}, timeout=12)
        r.raise_for_status()
        data = r.json() if r.headers.get("content-type","").startswith("application/json") else {}
        cap = _text((data or {}).get("caption"))
        return cap or (f"{msg} — 🧠 {ctx}" if msg and ctx else msg or (f"🧠 {ctx}" if ctx else "📷"))
    except Exception:
        # graceful fallback to your current style
        return (f"{_text(message)} — 🧠 {_text(context)}" if _text(message) and _text(context)
                else _text(message) or (f"🧠 {_text(context)}" if _text(context) else "📷"))

# keep a session-scoped set of used captions to avoid dupes
def _unique_caption(raw: str, tries=2) -> str:
    used = st.session_state.setdefault("_used_captions", set())
    cap = _text(raw)
    if cap and cap not in used:
        used.add(cap); return cap
    # nudge for variety
    base = cap
    for t in range(tries):
        alt = (base + " ✨") if t == 0 else (base + " — a moment anew")
        if alt not in used:
            used.add(alt); return alt
    # last resort: add a tiny hash
    import hashlib
    tag = hashlib.md5((cap or "📷").encode("utf-8")).hexdigest()[:4]
    final = f"{cap} • {tag}" if cap else f"📷 • {tag}"
    used.add(final)
    return final



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

def persist_session():
    cache = {
        "fb_token": st.session_state.get("fb_token"),
        "latest_backup": st.session_state.get("latest_backup"),
        "new_backup_done": st.session_state.get("new_backup_done"),
    }
    if st.session_state.get("fb_id") or st.session_state.get("fb_name"):
        cache["latest_backup"] = cache.get("latest_backup", {}) | {
            "user_id": st.session_state.get("fb_id"),
            "name": st.session_state.get("fb_name"),
        }
    with open("backup_cache.json", "w") as f:
        json.dump(cache, f)



restore_session()
if "fb_token" not in st.session_state:
    st.warning("Please login with Facebook first.")
    st.stop()

# --- Session defaults ---
if "undo_stack" not in st.session_state:
    st.session_state["undo_stack"] = {}
# --- PDF state (do NOT auto-regenerate on every rerun) ---
st.session_state.setdefault("pdf_bytes", None)     # last built PDF bytes
st.session_state.setdefault("pdf_dirty", True)     # mark needs rebuild



st.markdown("""
<div class="header-container">
  <img src="https://minedco.com/favicon.ico" alt="Mined logo">
  <div class="header-title">Facebook <span class="accent">Memories</span></div>
</div>
<div class="hero-box">
  <h1>🧠 Your AI-Curated Scrapbook</h1>
  <p>Relive your favorite moments in one place.</p>
</div>

""", unsafe_allow_html=True)


st.markdown(f"""
<div class="promo-wrap">
  <div class="promo-grid">
    <div class="promo-card">
      <img src="{PROMO1}" alt="LiveOn Promo 1">
      <div class="caption">LiveOn + Memories</div>
    </div>
    <div class="promo-card">
      <img src="{PROMO2}" alt="LiveOn Promo 2">
      <div class="caption">From ZIP to Story</div>
    </div>
    <div class="promo-card">
      <img src="{PROMO3}" alt="LiveOn Promo 3">
      <div class="caption">Crafted Automatically</div>
    </div>
  </div>

  <div class="promo-copy">
    <div class="badge" style="margin-bottom:8px;">Want something more?</div>
    <div class="muted" style="font-size:1.05rem;line-height:1.6;">
      <strong>LiveOn</strong> doesn’t stop at backup.<br/>
      It can turn your photos and posts into a beautifully crafted story — in your tone, your style, your rhythm.<br/>
      A scrapbook that feels like you made it, without you doing a thing.
    </div>
  </div>
</div>
""", unsafe_allow_html=True)



# --- LiveOn promo strip (uses files in ../media) ---
MEDIA_DIR = Path(__file__).resolve().parent.parent / "media"
PROMO_IMAGES = [
    str(MEDIA_DIR / "image.png"),
    str(MEDIA_DIR / "LiveOn-Logo20.png"),
    str(MEDIA_DIR / "image (1).png"),
]

promo_cols = st.columns([1, 1, 1, 2])  # three small tiles + wider copy

# three compact promo tiles
for i in range(3):
    with promo_cols[i]:
        st.markdown('<div class="card" style="padding:12px">', unsafe_allow_html=True)
        st.image(PROMO_IMAGES[i], caption="", width=220)
        st.markdown('</div>', unsafe_allow_html=True)





# ── CONSTANTS ────────────────────────────────────────────────
FUNCTION_BASE = st.secrets.get(
    "FUNCTION_BASE",
    os.environ.get("FUNCTION_BASE", "https://test0776.azurewebsites.net/api")
)

if "azurewebsites.net" not in FUNCTION_BASE:
    st.warning("⚠️ FUNCTION_BASE is not pointing to your deployed Function App. "
               "Set FUNCTION_BASE in secrets to your deployed Functions base URL.")


CONNECT_STR   = st.secrets["AZURE_CONNECTION_STRING"]
CONTAINER     = "backup"

blob_service_client = BlobServiceClient.from_connection_string(CONNECT_STR)
container_client = blob_service_client.get_container_client(CONTAINER)
blob_names = [blob.name for blob in container_client.list_blobs()]

# --- SAS helpers (robust across SDK variants) ---
def _account_key_from_env() -> str | None:
    try:
        import re
        m = re.search(r'AccountKey=([^;]+)', CONNECT_STR)
        return m.group(1) if m else None
    except Exception:
        return None

def _account_key_from_client() -> str | None:
    cred = getattr(blob_service_client, "credential", None)
    return getattr(cred, "account_key", None) or getattr(cred, "key", None)

def _get_account_key() -> str | None:
    return _account_key_from_env() or _account_key_from_client()

def sign_blob_url(blob_path: str) -> str:
    try:
        account_name = blob_service_client.account_name
        account_key = _get_account_key()
        sas = generate_blob_sas(
            account_name=account_name,
            container_name=CONTAINER,
            blob_name=blob_path,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=24),
        )
        return f"https://{account_name}.blob.core.windows.net/{CONTAINER}/{quote(blob_path, safe='/')}?{sas}"
    except Exception:
        return "https://via.placeholder.com/600x400?text=Image+Unavailable"


from urllib.parse import unquote

query_params = st.query_params

# -- Simple router to make navbar links work --
view = (query_params.get("view") if isinstance(query_params.get("view", None), str)
        else (query_params.get("view", [None])[0] if query_params.get("view", None) else None))

if view == "projects":
    try:
        st.switch_page("pages/2_Projects.py")
    except Exception:
        try: st.switch_page("Projects.py")
        except Exception: pass
    st.stop()
elif view == "backups":
    try:
        st.switch_page("pages/1_FB_Backup.py")
    except Exception:
        try: st.switch_page("FB_Backup.py")
        except Exception: pass
    st.stop()
# elif "scrapbook": stay on this page


# 👇 Add this check early in FbMemories.py
backup_id = st.session_state.get("selected_backup")
project_id = st.query_params.get("project_id") or st.session_state.get("selected_project")

# Decide whether we're rendering from a full backup or project
if backup_id:
    blob_folder = backup_id  # already in format: fb_id/folder_name
    is_project = False
elif project_id:
    fb_token = st.session_state["fb_token"]
    fb_hash = hashlib.md5(fb_token.encode()).hexdigest()
    blob_folder = f"{fb_hash}/projects/{project_id}"
    is_project = True
else:
    st.error("⚠️ No backup or project selected. Please go to 'My Projects' or 'My Backups'.")
    st.stop()
#st.write("📂 Trying to load from blob folder:", blob_folder)



if project_id:
    project_id = unquote(project_id)
    st.session_state["selected_project"] = project_id



# Compute user-specific hash for blob path
#fb_token = st.session_state["fb_token"]
#fb_hash = hashlib.md5(fb_token.encode()).hexdigest()
#blob_folder = f"{fb_hash}/projects/{project_id}"
try:
    meta_blob = container_client.get_blob_client(f"{blob_folder}/project_meta.json")
    if meta_blob.exists():
        meta = json.loads(meta_blob.download_blob().readall())
        project_name = meta.get("project_name", "Facebook Memories")
    else:
        project_name = "Facebook Memories"
except:
    project_name = "Facebook Memories"

st.markdown(f"<div class='section-title'>📘 {project_name}</div>", unsafe_allow_html=True)




@st.cache_data(show_spinner=False)
def load_all_posts_from_blob(container: str, folder: str) -> list[dict]:
    bsc = BlobServiceClient.from_connection_string(CONNECT_STR)
    cc = bsc.get_container_client(container)

    blobs = list(cc.list_blobs(name_starts_with=f"{folder}/"))

    def _items_from_blob(blob_name: str) -> list[dict]:
        txt = (
            bsc.get_blob_client(container, blob_name)
               .download_blob()
               .readall()
               .decode("utf-8")
        )
        try:
            data = json.loads(txt)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and isinstance(data.get("data"), list):
                return data["data"]
        except json.JSONDecodeError:
            pass
        return []

    # Key for dedupe: use a real ID if present, else hash of message+created_time
    def _key(p: dict) -> str:
        pid = p.get("id") or p.get("post_id") or p.get("status_id")
        if pid:
            return str(pid)
        base = f"{p.get('message','')}|{p.get('created_time','')}"
        return hashlib.md5(base.encode("utf-8")).hexdigest()

    posts_by_id: dict[str, dict] = {}

    # 1) First pass: prefer posts WITH captions (override anything else)
    for blob in blobs:
        name = blob.name.lower()
        if not (name.endswith(".json") or name.endswith(".json.json")):
            continue
        if "posts+cap.json" not in name:
            continue
        for p in _items_from_blob(blob.name):
            posts_by_id[_key(p)] = p

    # 2) Second pass: add plain posts ONLY if we don't already have them
    for blob in blobs:
        name = blob.name.lower()
        if not (name.endswith(".json") or name.endswith(".json.json")):
            continue
        if "posts" not in name or "posts+cap.json" in name:
            continue
        for p in _items_from_blob(blob.name):
            posts_by_id.setdefault(_key(p), p)

    return list(posts_by_id.values())



def call_function(endpoint:str, payload:dict, timeout:int=90):
    url = f"{FUNCTION_BASE}/{endpoint}"
    try:
        res = requests.post(url, json=payload, timeout=timeout)
        res.raise_for_status()
        return res
    except requests.exceptions.RequestException as err:
        st.error(f"❌ Azure Function error: {err}")
        st.stop()


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
    seen_urls: set[str] = set()

    for p in posts:
        caption = _unique_caption(_craft_caption_via_function(p.get("message"), p.get("context_caption")))
        why = post.get("why", {})
        if isinstance(why, dict) and "score" in why and advanced_mode:
            caption = f"{caption}  | 🧭 match={why['score']}"


        images = p.get("images", [])
        if not images:
            images = ["https://via.placeholder.com/300x200?text=No+Image+Available"]

        for img in images:
            if not img:
                continue
            # keep the original for display (preserves SAS/query)
            display_url = img if str(img).startswith("http") else sign_blob_url(str(img))



            # use a normalized key ONLY for dedupe
            key_url = normalize_url(display_url)
            if key_url in seen_urls:
                continue
            seen_urls.add(key_url)
            all_items.append(("image", display_url, caption))



    # 4-column grid layout
    cols = st.columns([1, 1, 1, 1])
    for idx, (kind, img_url, caption) in enumerate(all_items):
        with cols[idx % 4]:
            if kind == "image":
                try:
                    st.image(img_url, caption=_cap(caption), use_container_width=True)
                except:
                    st.image("https://via.placeholder.com/600x400?text=Image+Unavailable", caption=caption[:80], use_container_width=True)




# 🆕 CHANGE: Dynamic max_per_chapter calculation
def calculate_max_per_chapter(chapters, posts):
    posts_per_page = 3
    target_pages = 50
    total_posts = posts_per_page * target_pages
    chapters_count = len(chapters)
    return total_posts // chapters_count

def render_chapter_post_images(chap_title, chapter_posts, classification, FUNCTION_BASE):
    import json, requests
    import streamlit as st

    st.markdown("<div class='card'><div class='grid-3'>", unsafe_allow_html=True)

    # always 3 columns (we’re ignoring minimal UI now)
    cols = st.columns(3)

    seen_urls: set[str] = set()

    for post_idx, post in enumerate(chapter_posts):
        images = post.get("images", []) or ([post.get("image")] if "image" in post else [])
        caption = _unique_caption(_craft_caption_via_function(post.get("message"), post.get("context_caption")))
        why = post.get("why", {})
        if isinstance(why, dict) and "score" in why and advanced_mode:
            caption = f"{caption}  | 🧭 match={why['score']}"

        for img_idx, img_url in enumerate(images):
            with cols[post_idx % len(cols)]:   # ✅ safe modulo (fixes IndexError)
                display_url = img_url if str(img_url).startswith("http") else sign_blob_url(str(img_url))

                key = normalize_url(display_url)
                if key in seen_urls:
                    continue
                seen_urls.add(key)

                try:
                    st.image(display_url, caption=_cap(caption), use_container_width=True)
                except Exception:
                    st.image("https://via.placeholder.com/600x400?text=Image+Unavailable",
                             caption=caption[:80], use_container_width=True)

                # Replace / Undo
                button_key = f"replace_{chap_title}_{post_idx}_{img_idx}"
                undo_key = f"undo_{chap_title}_{post_idx}_{img_idx}"

                if st.button("🔄 Replace", key=button_key):
                    # ⏳ add hourglass while it works
                    with st.spinner("⏳ Finding a better fit..."):
                        prev_img = images[img_idx]
                        st.session_state["undo_stack"][undo_key] = prev_img

                        used_now = []
                        for _c, _plist in st.session_state.get("classification", {}).items():
                            for _p in _plist:
                                for _im in _p.get("images", []):
                                    used_now.append(str(_im).split("?")[0])

                        try:
                            payload = {
                                "chapter": chap_title,
                                "posts": st.session_state.get("all_posts_raw", []),
                                "exclude_images": [str(prev_img).split("?")[0]] + used_now,
                                "max_per": 1,
                                "prefer_year_spread": True,
                                "current_created_time": post.get("created_time"),
                                "user_prefix": blob_folder,
                            }

                            res = call_function("regenerate_chapter_subset", payload, timeout=60)
                            result = res.json().get(chap_title, [])
                            if result and result[0]["images"]:
                                new = result[0]
                                new_img = new["images"][0]

                                updated = json.loads(json.dumps(st.session_state["classification"]))
                                target = updated[chap_title][post_idx]

                                target["images"][img_idx] = new_img
                                if new.get("message") is not None:
                                    target["message"] = new["message"]
                                if new.get("created_time") is not None:
                                    target["created_time"] = new["created_time"]
                                target.pop("context_caption", None)

                                st.session_state["classification"] = updated
                                st.session_state["pdf_dirty"] = True     # <-- mark PDF as stale
                                st.success("✅ Image & caption updated!")
                                st.rerun()

                            else:
                                st.warning("😕 No alternative image found.")
                        except Exception as e:
                            st.error(f"Image replacement failed: {e}")

                if st.session_state.get("undo_stack") and undo_key in st.session_state["undo_stack"]:
                    if st.button("↩️ Undo", key=f"undo_btn_{undo_key}"):
                        try:
                            updated = json.loads(json.dumps(st.session_state["classification"]))
                            updated[chap_title][post_idx]["images"][img_idx] = st.session_state["undo_stack"][undo_key]
                            st.session_state["classification"] = updated
                            st.session_state["pdf_dirty"] = True     # <-- mark PDF as stale
                            del st.session_state["undo_stack"][undo_key]
                            st.success("✅ Undo successful.")
                            st.rerun()

                        except Exception as e:
                            st.error(f"Undo failed: {e}")

    st.markdown("</div></div>", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)


def _register_brand_fonts() -> tuple[str, str]:
    """
    Try to use modern, appealing fonts. Put the TTF files in ./fonts/.
    Fallback cleanly to Helvetica if the files aren’t present.
    """
    try:
        pdfmetrics.registerFont(TTFont("Inter", "fonts/Inter-Regular.ttf"))
        pdfmetrics.registerFont(TTFont("Inter-Bold", "fonts/Inter-Bold.ttf"))
        return "Inter", "Inter-Bold"
    except Exception:
        try:
            pdfmetrics.registerFont(TTFont("Playfair", "fonts/PlayfairDisplay-Regular.ttf"))
            pdfmetrics.registerFont(TTFont("Playfair-Bold", "fonts/PlayfairDisplay-Bold.ttf"))
            return "Playfair", "Playfair-Bold"
        except Exception:
            return "Helvetica", "Helvetica-Bold"

def _nice_date(iso: str | None) -> str:
    if not iso: return ""
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y")
    except Exception:
        return ""

def _flatten_chapter_items(classification: dict, chap: str) -> list[dict]:
    """One image == one item; keeps captions & dates consistent."""
    items = []
    for p in classification.get(chap, []):
        imgs = p.get("images", []) or ([p.get("image")] if "image" in p else [])
        if not imgs: 
            continue
        caption = _unique_caption(_craft_caption_via_function(p.get("message"), p.get("context_caption")))
        date_s = _nice_date(p.get("created_time"))
        for u in imgs:
            items.append({"img": u, "caption": caption, "date": date_s})
    return items


@st.cache_data(show_spinner=False, ttl=3600)
def _pdf_image_bytes(url: str):
    """
    Fetch an image and return a BytesIO buffer that ReportLab can draw.
    - Signs Azure blob paths with SAS using sign_blob_url(...)
    - Returns JPEG/PNG as-is
    - Converts WEBP/GIF (and anything else Pillow can open) to PNG
    - Returns None on failure
    """
    # Sign blob paths so they’re publicly readable for the fetch
    if not isinstance(url, str):
        url = str(url)
    if not url.startswith("http"):
        url = sign_blob_url(url)

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.facebook.com/",
        "Accept": "image/*,*/*;q=0.8",
    }
    try:
        r = requests.get(url, timeout=12, stream=True, headers=headers)
        r.raise_for_status()
        ctype = (r.headers.get("Content-Type", "") or "").split(";")[0].lower()
        data = r.content

        # Fast path: ReportLab can draw JPEG/PNG directly
        if ctype in ("image/jpeg", "image/jpg", "image/png"):
            return BytesIO(data)

        # Convert other formats (e.g., webp/gif) via Pillow → PNG
        if _HAVE_PIL:
            try:
                im = PILImage.open(BytesIO(data)).convert("RGB")
                out = BytesIO()
                im.save(out, format="PNG")
                out.seek(0)
                return out
            except Exception:
                return None
        return None
    except Exception:
        return None
    

# ---------------- SCRAPBOOK THEME HELPERS ----------------

# Where your public asset images live on Azure (no trailing slash is fine)
PUBLIC_ASSET_BASE = "https://fbbackupkhushi.blob.core.windows.net/backup/app-assets"
# Folder name inside the "backup" container
ASSET_BLOB_PREFIX = "app-assets"
# --- Local assets folder (safe even if it doesn't exist) ---
BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"



def _asset(name: str) -> str | None:
    """
    Return a path/URL for an asset named `name`.
    1) If ./assets/<name> exists locally, use that.
    2) Else, return a SAS-signed URL for blob 'app-assets/<name>' in the 'backup' container.
    """
    # 1) Local dev override (no error if folder doesn't exist)
    try:
        p = ASSETS_DIR / name
        if p.exists():
            return str(p)
    except Exception:
        pass

    # 2) Azure blob (private): always return SAS
    blob_path = f"{ASSET_BLOB_PREFIX}/{name}"  # e.g., app-assets/paper_bg.jpg
    try:
        bc = container_client.get_blob_client(blob_path)
        if bc.exists():
            return sign_blob_url(blob_path)  # SAS for private container
    except Exception:
        pass

    return None


def _register_scrapbook_fonts() -> tuple[str, str, str]:
    """
    Try to use 'Special Elite' (typewriter) and 'Patrick Hand' (handwritten).
    Put TTFs under ./fonts/ if you have them; we fall back cleanly.
    """
    base, bold, script = "Helvetica", "Helvetica-Bold", "Courier"
    try:
        pdfmetrics.registerFont(TTFont("SpecialElite", "fonts/SpecialElite-Regular.ttf"))
        base = "SpecialElite"
    except Exception:
        pass
    try:
        pdfmetrics.registerFont(TTFont("PatrickHand", "fonts/PatrickHand-Regular.ttf"))
        script = "PatrickHand"
    except Exception:
        pass
    try:
        pdfmetrics.registerFont(TTFont("Inter-Bold", "fonts/Inter-Bold.ttf"))
        bold = "Inter-Bold"
    except Exception:
        pass
    return base, bold, script

def _theme_for(chap_title: str) -> dict:
    t = chap_title.lower()
    def any_kw(*kws): return any(k in t for k in kws)
    theme = {
        "bg": _asset("paper_bg.jpg"),
        "overlay": _asset("torn_paper.png"),
        "tape": _asset("tape.png"),
        "accent_rgb": (0.16, 0.16, 0.16),  # dark gray
        "title_font_scale": 1.0,
    }
    if any_kw("travel","trip","journey","adventure","vacation","explore"):
        theme.update({
            "bg": _asset("map_bg.jpg") or theme["bg"],
            "tape": _asset("tape.png"),
            "accent_rgb": (0.10, 0.35, 0.58),  # ocean
            "title_font_scale": 1.05,
        })
    elif any_kw("family","home","ties","gratitude","affection"):
        theme.update({
            "bg": theme["bg"],
            "tape": _asset("washi.png") or theme["tape"],
            "accent_rgb": (0.35, 0.17, 0.06),  # warm brown
        })
    elif any_kw("humor","playful","vibrant","fun","joy"):
        theme.update({
            "tape": _asset("washi.png") or theme["tape"],
            "accent_rgb": (0.62, 0.20, 0.55),  # playful magenta
        })
    elif any_kw("reflection","revelation","dream","future","past","self"):
        theme.update({
            "accent_rgb": (0.25, 0.33, 0.45),  # calm blue-gray
        })
    return theme

def _draw_bg(c, W, H, theme):
    # background
    bg = theme.get("bg")
    if bg:
        try:
            buf = _pdf_image_bytes(bg)
            if buf:
                img = ImageReader(buf)
                c.drawImage(img, 0, 0, width=W, height=H, preserveAspectRatio=False, mask='auto')
            else:
                raise RuntimeError("BG fetch failed")
        except Exception:
            c.setFillColorRGB(0.98, 0.97, 0.94)
            c.rect(0, 0, W, H, fill=True, stroke=False)
    else:
        c.setFillColorRGB(0.98, 0.97, 0.94)
        c.rect(0, 0, W, H, fill=True, stroke=False)

    # torn overlay (optional PNG with alpha)
    overlay = theme.get("overlay")
    if overlay:
        try:
            obuf = _pdf_image_bytes(overlay)
            if obuf:
                oimg = ImageReader(obuf)
                c.drawImage(oimg, 0, 0, width=W, height=H, preserveAspectRatio=False, mask='auto')
        except Exception:
            pass

def _polaroid(c, img_buf: BytesIO, x: float, y: float, w: float, h: float,
              angle: float = 0.0, caption: str = "", tape_path: str | None = None):
    """
    Draw a 'polaroid': white frame with drop shadow, rotated slightly.
    (x,y) is the center of the polaroid; w,h are the photo box (not including frame).
    """
    frame_pad = 12     # white border
    foot_pad  = 40     # extra at bottom for caption
    total_w, total_h = w + 2*frame_pad, h + frame_pad + foot_pad

    c.saveState()
    c.translate(x, y)
    c.rotate(angle)

    # shadow
    c.setFillColorRGB(0,0,0); c.setStrokeColorRGB(0,0,0)
    c.setFillAlpha(0.12) if hasattr(c, "setFillAlpha") else None
    c.roundRect(-total_w/2+3, -total_h/2-3, total_w, total_h, 8, fill=True, stroke=False)
    if hasattr(c, "setFillAlpha"): c.setFillAlpha(1)

    # frame
    c.setFillColorRGB(1,1,1)
    c.roundRect(-total_w/2, -total_h/2, total_w, total_h, 8, fill=True, stroke=False)

    # photo
    try:
        img = ImageReader(img_buf)
        iw, ih = img.getSize()
        scale = min(w/iw, h/ih)
        pw, ph = iw*scale, ih*scale
        c.drawImage(img, -pw/2, -ph/2 + foot_pad/2, width=pw, height=ph, mask='auto')
    except Exception:
        c.setFillColorRGB(0.9,0.9,0.9)
        c.rect(-w/2, -h/2 + foot_pad/2, w, h, fill=True, stroke=False)

    # caption
    if caption:
        c.setFillColorRGB(0.20,0.20,0.20)
        c.setFont(_register_scrapbook_fonts()[2], 10)  # handwritten
        from textwrap import wrap
        wrap_chars = max(24, int(w/9))
        cap = wrap(caption, width=wrap_chars)[:2]
        yy = -total_h/2 + 8
        for line in cap:
            c.drawCentredString(0, yy, line)
            yy += 11

    # tape on top (only if caller asked for it)
    tp = tape_path
    if tp:
        try:
            tbuf = _pdf_image_bytes(tp)
            if tbuf:
                timg = ImageReader(tbuf)
                c.drawImage(timg, x+10, y+14, width=90, height=18, mask='auto')
        except Exception:
            pass



    c.restoreState()

def _find_profile_photo(blob_folder: str) -> str | None:
    """
    Try common profile pic names in the user's blob, else take the first
    image used in classification as a fallback.
    Returns a blob path or an http URL, or None.
    """
    try:
        # look for common names
        candidates = [
            f"{blob_folder}/profile.jpg",
            f"{blob_folder}/profile.jpeg",
            f"{blob_folder}/profile.png",
            f"{blob_folder}/profile_pic.jpg",
            f"{blob_folder}/profile_pic.png",
            f"{blob_folder}/avatar.jpg",
            f"{blob_folder}/avatar.png",
        ]
        for b in candidates:
            bc = container_client.get_blob_client(b)
            if bc.exists() and bc.get_blob_properties().size > 1024:
                return b
    except Exception:
        pass
    # fallback: first image in classification (set later)
    try:
        cls = st.session_state.get("classification", {})
        for plist in cls.values():
            for p in plist:
                for u in p.get("images", []):
                    if u:
                        return u
    except Exception:
        pass
    return None

def _draw_markdown_lines(c, text, x, y, base_font, bold_font, size=12, line_height=14, wrap_chars=95):
    """
    Draws lightweight Markdown:
    - **bold** supported
    - preserves line breaks
    - simple wrapping by characters (fast & good-enough for summaries)
    Returns the new y after drawing.
    """
    for para in text.split("\n"):
        if not para.strip():
            y -= line_height
            continue
        for line in wrap(para, width=wrap_chars):
            cx = x
            # split into bold / normal parts
            parts = re.findall(r'(\*\*.*?\*\*|[^*]+)', line)
            for part in parts:
                if part.startswith("**") and part.endswith("**"):
                    frag = part[2:-2]
                    c.setFont(bold_font, size)
                    c.drawString(cx, y, frag)
                    cx += c.stringWidth(frag, bold_font, size)
                else:
                    frag = part
                    c.setFont(base_font, size)
                    c.drawString(cx, y, frag)
                    cx += c.stringWidth(frag, base_font, size)
            y -= line_height
    return y

def _pick_hero_image(classification: dict, profile_summary: str) -> str | None:
    """
    Pick a 'defining' photo using simple scoring:
    - high 'why.score' from classification
    - message contains milestone keywords
    - prefer posts that have a message (not image-only)
    """
    kw = {
        "graduation","convocation","farewell","wedding","engagement","anniversary",
        "birthday","award","medal","promotion","first day","last day","picnic","trip",
        "trek","festival","family","friends","selfie","portrait"
    }
    kws_from_eval = {w for w in kw if w in (profile_summary or "").lower()}

    best_img, best_score = None, -1.0
    for chap, plist in classification.items():
        for p in plist:
            msg = _text(p.get("message"))
            imgs = p.get("images", []) or ([p.get("image")] if p.get("image") else [])
            if not imgs: 
                continue
            sc = float((p.get("why") or {}).get("score") or 0.0) * 1.5
            if msg: 
                sc += min(len(msg), 120) / 120.0 * 0.5
                low = msg.lower()
                if any(w in low for w in kw): sc += 0.8
                if any(w in low for w in kws_from_eval): sc += 0.6
            # take the first image of that post
            if sc > best_score:
                best_img, best_score = imgs[0], sc
    return best_img
def _draw_chapter_label(c, text, M, W, H):
    # label width based on text
    font_bold = _register_scrapbook_fonts()[1]
    c.setFont(font_bold, 14)
    label_w = c.stringWidth(f"📚 {text}", font_bold, 14) + 28
    x, y = M, H - M - 8  # top-left

    # shadow
    c.setFillColorRGB(0,0,0)
    if hasattr(c,'setFillAlpha'): c.setFillAlpha(0.12)
    c.roundRect(x-2, y-6, label_w+4, 26, 6, fill=True, stroke=False)
    if hasattr(c,'setFillAlpha'): c.setFillAlpha(1)

    # pale sticky note
    c.setFillColorRGB(1.0, 0.972, 0.90)   # #fff8e6-ish
    c.roundRect(x, y-4, label_w, 22, 6, fill=True, stroke=False)

    # tape
    tp = _asset("tape.png") or _asset("washi.png")
    if tp:
        try:
            c.drawImage(tp, x+10, y+14, width=90, height=18, mask='auto')
        except:
            pass

    # text
    c.setFillColorRGB(0.16,0.16,0.16)
    c.drawString(x+12, y+3, f"📚 {text}")


def build_pdf_bytes(classification, chapters, blob_folder, show_empty_chapters, profile_summary, template="polaroid"):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    W, H = A4
    M = 42
    baseFont, boldFont, scriptFont = _register_scrapbook_fonts()

    # ---------- Cover ----------
    # Soft warm background
    c.setFillColorRGB(0.985, 0.975, 0.94)  # warm paper
    c.rect(0, 0, W, H, fill=True, stroke=False)

    # Decorative header band
    c.setFillColorRGB(0.12, 0.17, 0.28)
    c.rect(0, H-1.25*inch, W, 1.25*inch, fill=True, stroke=False)

    # Title (larger, with breathing room)
    title_font = _register_brand_fonts()[1]  # bold
    c.setFillColorRGB(1, 1, 1)
    c.setFont(title_font, 46)
    c.drawCentredString(W/2, H-0.75*inch, "My Facebook Scrapbook")

    # Name (subtle, smaller, further below)
    try:
        b1 = container_client.get_blob_client(f"{blob_folder}/profile.json")
        b2 = container_client.get_blob_client(f"{blob_folder}/profile.json.json")
        profile_data = {}
        if b1.exists(): profile_data = json.loads(b1.download_blob().readall())
        elif b2.exists(): profile_data = json.loads(b2.download_blob().readall())
        name = (profile_data.get("profile",{}).get("name") or profile_data.get("name") or "Facebook User").replace("_"," ")
    except Exception:
        name = "Facebook User"

    c.setFillColorRGB(0.18, 0.18, 0.2)
    c.setFont(_register_brand_fonts()[0], 18)
    c.drawCentredString(W/2, H-1.8*inch, f"For {name}")

    # Full-width hero image with generous margins
    hero = _pick_hero_image(classification, profile_summary) or _find_profile_photo(blob_folder)
    buf  = _pdf_image_bytes(hero) if hero else None
    if buf:
        hero_h = 4.0*inch
        hero_w = W - 2*M
        x, y   = M, (H - 1.8*inch - hero_h) / 2  # centered between header and footer

        # Soft shadow
        c.setFillColorRGB(0, 0, 0)
        if hasattr(c, "setFillAlpha"): c.setFillAlpha(0.12)
        c.roundRect(x-6, y-6, hero_w+12, hero_h+12, 18, fill=True, stroke=False)
        if hasattr(c, "setFillAlpha"): c.setFillAlpha(1)

        # White frame
        c.setFillColorRGB(1, 1, 1)
        c.roundRect(x-2, y-2, hero_w+4, hero_h+4, 16, fill=True, stroke=False)

        # Photo (cover fit)
        img   = ImageReader(buf)
        iw, ih = img.getSize()
        scale  = max(hero_w/iw, hero_h/ih)
        w, h   = iw*scale, ih*scale
        c.drawImage(img, x + (hero_w - w)/2, y + (hero_h - h)/2, width=w, height=h, mask='auto')

    # footer
    c.setFillColorRGB(0.35, 0.38, 0.45)
    c.setFont(_register_brand_fonts()[0], 10)
    c.drawCentredString(W/2, 0.7*inch, "Generated with LiveOn • facebook memories")
    c.showPage()

    # ---------- Personality page (sticky note style) ----------
    if profile_summary:
        # background (paper)
        theme = {"bg": _asset("paper_bg.jpg"), "overlay": None}
        _draw_bg(c, W, H, theme)

        # title
        c.setFillColorRGB(0.15,0.15,0.18)
        c.setFont(boldFont, 22)
        c.drawString(M, H - M + 2, "Personality Snapshot")

        # note card
        card_x, card_y = M+10, M+24
        card_w, card_h = W - 2*M - 20, H - 2*M - 60

        # shadow
        c.setFillColorRGB(0,0,0); 
        if hasattr(c, "setFillAlpha"): c.setFillAlpha(0.12)
        c.roundRect(card_x+4, card_y-4, card_w, card_h, 16, fill=True, stroke=False)
        if hasattr(c, "setFillAlpha"): c.setFillAlpha(1)

        # card
        c.setFillColorRGB(1,1,1)
        c.roundRect(card_x, card_y, card_w, card_h, 16, fill=True, stroke=False)

        # tape
       # tp = _asset("tape.png") or _asset("washi.png")
        #if tp:
         #   try:
          #      c.drawImage(tp, card_x + card_w/2 - 90, card_y + card_h - 10, width=180, height=28, mask='auto')
           # except Exception:
            #    pass


        # text in handwritten font (bold + line breaks preserved)
        c.setFillColorRGB(0.12,0.12,0.12)
        c.setFont(scriptFont, 12)
        text_x, text_y = card_x + 18, card_y + card_h - 44
        min_y = card_y + 28

        for para in profile_summary.split("\n"):
            # preserve blank lines
            if not para.strip():
                text_y -= 14
                if text_y < min_y:
                    c.showPage()
                    _draw_bg(c, W, H, theme)
                    c.setFont(scriptFont, 12)
                    text_x, text_y = M + 12, H - M - 24
                continue

            for line in wrap(para, width=95):
                cx = text_x
                # render **bold** fragments inline
                for part in re.findall(r'(\*\*.*?\*\*|[^*]+)', line):
                    if part.startswith("**") and part.endswith("**"):
                        frag = part[2:-2]
                        c.setFont(boldFont, 12)
                        c.drawString(cx, text_y, frag)
                        cx += c.stringWidth(frag, boldFont, 12)
                    else:
                        frag = part
                        c.setFont(scriptFont, 12)
                        c.drawString(cx, text_y, frag)
                        cx += c.stringWidth(frag, scriptFont, 12)
                text_y -= 14
                if text_y < min_y:
                    c.showPage()
                    _draw_bg(c, W, H, theme)
                    c.setFont(scriptFont, 12)
                    text_x, text_y = M + 12, H - M - 24

        c.showPage()




    # ---- Flexible layout helper (centers 1, 2, or 3 images per page) ----
    def _draw_polaroids_auto(c, items, theme, W, H, M, angles=(-1.2, 0.9, -0.8), tape=False, clean=False):
        _draw_bg(c, W, H, theme)

        # Chapter title
        c.setFillColorRGB(*theme.get("accent_rgb", (0.16, 0.16, 0.16)))
        title = theme.get("chapter_title", "")
        c.setFont(_register_scrapbook_fonts()[1], 20 * theme.get("title_font_scale", 1.0))
        c.drawString(M, H - M + 6, title)

        gap = 0.35 * inch
        n = max(1, min(3, len(items)))

        # Card sizes per count (bigger when fewer photos)
        if n == 1:
            card_w = W - 2*M - 0.8*inch
            card_h = min(1.05 * card_w, H - 2*M - 1.6*inch)
            centers = [(W/2, M + (H - 2*M)/2)]
        elif n == 2:
            card_w = (W - 2*M - gap) / 2.0
            card_h = card_w * 1.20
            y = M + (H - 2*M - card_h)/2.0
            centers = [
                (M + card_w/2, y),
                (W - M - card_w/2, y)
            ]
        else:  # 3
            card_w = (W - 2*M - 2*gap) / 3.0
            card_h = card_w * 1.25
            y = M + (H - 2*M - card_h)/2.0
            centers = [
                (M + card_w/2,                    y),
                (M + card_w/2 + card_w + gap,     y),
                (M + card_w/2 + 2*(card_w + gap), y),
            ]

        for pos, it in enumerate(items[:3]):
            buf = _pdf_image_bytes(it["img"])
            x, y = centers[pos]

            if clean:
                # Clean card (Natural Moodboard)
                c.saveState()
                c.setFillColorRGB(0,0,0)
                if hasattr(c,"setFillAlpha"): c.setFillAlpha(0.10)
                c.roundRect(x-(card_w/2)-3, y-(card_h/2)-3, card_w+6, card_h+6, 14, fill=True, stroke=False)
                if hasattr(c,"setFillAlpha"): c.setFillAlpha(1)
                c.setFillColorRGB(1,1,1)
                c.roundRect(x-card_w/2, y-card_h/2, card_w, card_h, 14, fill=True, stroke=False)
                try:
                    if buf:
                        img = ImageReader(buf)
                        iw, ih = img.getSize()
                        scale = min((card_w-18)/iw, (card_h-18)/ih)
                        w, h = iw*scale, ih*scale
                        c.drawImage(img, x-w/2, y-h/2, width=w, height=h, mask='auto')
                except:
                    pass
                cap = _text(it.get("caption",""))[:90]
                if cap:
                    c.setFillColorRGB(0.20,0.20,0.20)
                    c.setFont(_register_scrapbook_fonts()[2], 10)
                    c.drawCentredString(x, y - card_h/2 - 14, cap)
                c.restoreState()
            else:
                _polaroid(
                    c,
                    img_buf=buf if buf else BytesIO(),
                    x=x, y=y, w=card_w, h=card_h,
                    angle=angles[pos] if pos < len(angles) else 0,
                    caption=_text(it.get("caption",""))[:90],
                    tape_path=(theme.get("tape") if tape else None)
                )


    # ---- Template configuration (backgrounds + style) ----
    TEMPLATE_CONF = {
        "polaroid": {
            "bg": _asset("kraft.jpg") or _asset("paper_bg.jpg"),  # warmer base
            "overlay": None,          # no torn/grey overlay
            "tape": None,             # no stickers by default
            "angles": (-1.2, 0.9, -0.8),
            "clean": False,
        },
        "travel": {
            "bg": _asset("map_bg.jpg") or _asset("paper_bg.jpg"),
            "overlay": None,
            "tape": None,
            "angles": (-0.8, 0.6, -0.5),
            "clean": False,
        },
        "natural": {
            "bg": _asset("kraft.jpg") or _asset("paper_bg.jpg"),
            "overlay": None,
            "tape": None,
            "angles": (0, 0, 0),
            "clean": True,            # clean white cards (moodboard vibe)
        },
    }


    # ---------- Chapter pages (3 images per page, full A4) ----------
    def _flatten(chap):
        items = []
        for p in classification.get(chap, []):
            imgs = p.get("images", []) or ([p.get("image")] if "image" in p else [])
            if not imgs:
                continue
            crafted = _unique_caption(_craft_caption_via_function(p.get("message"), p.get("context_caption")))
            date_s  = _nice_date(p.get("created_time"))
            for u in imgs:
                cap = f"{date_s} — {crafted}" if date_s else crafted
                items.append({"img": u, "caption": cap})
        return items

    page_no = 1
    conf = TEMPLATE_CONF.get(template, TEMPLATE_CONF["polaroid"])

    for chap in chapters:
        items = _flatten(chap)
        if not items:
            continue

        for i in range(0, len(items), 3):
            chunk = items[i:i+3]
            theme = {
                "bg": conf["bg"],
                "overlay": conf.get("overlay"),
                "tape": conf.get("tape"),
                "accent_rgb": (0.16,0.16,0.16),
                "title_font_scale": 1.0,
                "chapter_title": chap
            }
            _draw_polaroids_auto(
                c, chunk, theme, W, H, M,
                angles=conf["angles"], tape=bool(conf["tape"]), clean=conf["clean"]
            )

            c.setFont(baseFont, 9); c.setFillColorRGB(0.45,0.48,0.55)
            c.drawCentredString(W/2, M - 18, str(page_no)); page_no += 1
            c.showPage()

    c.save()
    pdf = buffer.getvalue(); buffer.close()
    return pdf

import hashlib, json
from typing import Iterable

def _content_hash(
    images_bytes: Iterable[bytes],
    captions: Iterable[str],
    design_key: str,
    layout_key: str,
    page_size: str,
    bg_color: str,
    seed: int
) -> str:
    h = hashlib.sha256()
    for b in images_bytes:
        h.update(b)
    h.update(json.dumps([
        list(captions), design_key, layout_key, page_size, bg_color, seed
    ], ensure_ascii=False).encode("utf-8"))
    return h.hexdigest()


def _build_pdf(
    # ⚠️ include EVERY input that changes the PDF
    design_key: str,
    layout_key: str,
    page_size: str,
    bg_color: str,
    seed: int,
    images_bytes: tuple[bytes, ...],
    captions: tuple[str, ...],
    _ck: str  # computed content key; see call-site below
) -> bytes:
    # call your real, pure builder here; don't do any Streamlit UI in this function
    return _build_pdf(
        design_key=design_key,
        layout_key=layout_key,
        page_size=page_size,
        bg_color=bg_color,
        seed=seed,
        images_bytes=list(images_bytes),
        captions=list(captions),
    )

def _content_hash(
    images_bytes: Iterable[bytes],
    captions: Iterable[str],
    design_key: str,
    layout_key: str,
    page_size: str,
    bg_color: str,
    seed: int
) -> str:
    h = hashlib.sha256()
    for b in images_bytes:
        h.update(b)
    h.update(json.dumps([
        list(captions), design_key, layout_key, page_size, bg_color, seed
    ], ensure_ascii=False).encode("utf-8"))
    return h.hexdigest()

@st.cache_data(show_spinner=False, ttl=0)
def _build_pdf_cached(
    # ⚠️ include EVERY input that changes the PDF
    design_key: str,
    layout_key: str,
    page_size: str,
    bg_color: str,
    seed: int,
    images_bytes: tuple[bytes, ...],
    captions: tuple[str, ...],
    _ck: str  # computed content key; see call-site below
) -> bytes:
    return _build_pdf(
        design_key=design_key,
        layout_key=layout_key,
        page_size=page_size,
        bg_color=bg_color,
        seed=seed,
        images_bytes=list(images_bytes),
        captions=list(captions),
    )



# ── UI ─────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚙️ Settings")
    advanced_mode = st.checkbox("Enable Advanced Mode (debug)", value=False)
    show_empty_chapters = st.checkbox("🧹 Hide Empty Chapters", value=True)
    hero_mode = st.checkbox("🎨 Enable Hero Mode")

    if st.button("🔄 Reload Posts"):
        st.cache_data.clear()
        st.rerun()

    if st.button("🗑️ Clear Scrapbook"):
        st.session_state.pop("classification", None)
        st.session_state.pop("chapters", None)
        st.rerun()


st.caption("Loading your Facebook posts from Azure Blob Storage…")
try:
    posts = load_all_posts_from_blob(CONTAINER, blob_folder)
    if not posts:
        st.warning("⚠️ No posts found in blob storage. Upload some and try again.")
        st.stop()
    # Clean, true count (after dedupe), no folder/chapters noise
    st.success(f"✅ Loaded {len(posts)} unique posts")
    st.session_state["all_posts_raw"] = posts


    # Optional tiny hint row (feel free to keep or delete)
    st.markdown("""
    <div class="muted" style="margin-top:-6px;margin-bottom:8px;">
    Tip: Click <strong>Generate Scrapbook</strong> when you’re ready.
    </div>
    """, unsafe_allow_html=True)




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
    post["message"] = _text(post.get("message"))
    post["context_caption"] = _text(post.get("context_caption"))
# ── PRIMARY ACTION ────────────────────────────────────────────────────────────
if "classification" not in st.session_state:
    if st.button("📘 Generate Scrapbook",use_container_width=True):
        # 1️⃣ Evaluate personality & life themes
        import re
        user_name = "This person"
        try:
            profile_data = {}
            # Look for both filenames
            for candidate in ("profile.json", "profile.json.json"):
                bc = container_client.get_blob_client(f"{blob_folder}/{candidate}")
                if bc.exists():
                    profile_data = json.loads(bc.download_blob().readall())
                    break
            # nested "profile" or flat form
            raw_name = (
                (profile_data.get("profile") or {}).get("name")
                or profile_data.get("name")
                or ""
            )
            raw_name = raw_name.strip()
            if raw_name:
                # "Khushi_Singh" → "Khushi Singh"
                user_name = raw_name.replace("_", " ").strip()
        except Exception:
            # keep fallback "This person" if anything goes wrong
            pass

        


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
        # --- NEW: infer surname and fetch insight (non-blocking) ---
        surname = re.split(r"[ _]+", (user_name or "").strip())[-1] if user_name else ""
        surname_data = {}
        if surname:
            try:
                r = requests.post(f"{FUNCTION_BASE}/surname_insight", json={"surname": surname}, timeout=8)
                r.raise_for_status()
                surname_data = r.json()
            except Exception:
                surname_data = {}

        # save for later use (e.g., PDF)
        st.session_state["surname_insight"] = surname_data

        def _surname_preface(d) -> str:
            if not isinstance(d, dict) or not d.get("surname"):
                return ""
            lines = []
            lines.append(f"🔎 **Surname insight: {d['surname']}**")
            if d.get("origin_meaning"):
                lines.append(f"- Origin & meaning: {d['origin_meaning']}")
            if d.get("geography_ethnicity"):
                lines.append(f"- Geographic/Ethnic ties: {d['geography_ethnicity']}")
            if d.get("variants"):
                lines.append(f"- Variants: {', '.join(d['variants'][:6])}")
            if d.get("cultural_historical"):
                lines.append(f"- Cultural/Historical notes: {d['cultural_historical']}")
            if d.get("notable_people"):
                lines.append(f"- Notable people: {', '.join(d['notable_people'][:6])}")
            return "\n".join(lines)

        surname_preface = _surname_preface(surname_data)

        # 🆕 Refined prompt
        eval_prompt = f"""First, present the following surname insight block verbatim if provided (otherwise skip this block):

        {surname_preface}

        Then, immediately follow with the personality evaluation of the user, and **the very first sentence of the personality section must start with "{user_name}"** (e.g., "{user_name} is a warm and reflective individual…").

        Use both their original post messages and the image context captions (context_caption).
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
            eval_res  = call_function("ask_about_blob",{"question":eval_prompt,"posts":posts})
            eval_text = eval_res.text
            st.session_state["profile_summary"] = eval_text
        st.markdown("### 🧠 Personality Evaluation Summary"); st.markdown(eval_text)

        # 🆕 Refined GPT prompt to avoid odd/empty chapters
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
            max_per_chapter = calculate_max_per_chapter(chapters, posts)


            classify_res = call_function(
            "embed_classify_posts_into_chapters",
            {
                "chapters": chapters,
                "user_prefix": blob_folder,
                "posts": posts,
                "max_per_chapter": max_per_chapter,
                "min_per_chapter": 4,              # ensure more than one item in “Family Ties”, etc.
                "max_images_per_post": 2,          # breadth over depth
                "min_match": 0.18,                 # skip weak matches
                "balance_by_year": True,           # increase year diversity
                "allow_global_image_reuse": False, # DO NOT reuse the same photo
                "max_global_reuse": 1              # defensive cap on any accidental repeat
            },
            timeout=300
        )




            classification = classify_res.json()

            # --- Validate before storing ---
            if "error" in classification:
                st.error("GPT classification failed.")
                if advanced_mode:
                    st.code(classification.get("raw_response", ""))
                st.stop()

            non_empty_chapters = [c for c in chapters if classification.get(c)]
            if not non_empty_chapters:
                st.warning("No chapters had matching posts.")
                st.stop()

            # ✅ Store in session_state and rerun to render ONCE in the final section
            st.session_state["classification"] = {c: classification[c] for c in chapters if classification.get(c)}
            st.session_state["chapters"] = [c for c in chapters if classification.get(c)]


            st.rerun()  # Streamlit ≥1.30


        # 5️⃣ Render each chapter with images and captions
        for chap in chapters:
            st.markdown(f"<div class='chapter-title'>📚 {chap}</div>", unsafe_allow_html=True)
            chapter_posts = classification.get(chap, [])
            if show_empty_chapters and not chapter_posts:
                continue
            
            #chapter_posts = classification.get(chap, [])
            if not chapter_posts:
                st.info("No posts matched this chapter.")
                continue
            cols = st.columns(3)
            idx = 0
            seen: set[tuple[str, str]] = set()
            for post_idx, p in enumerate(chapter_posts):
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
                    for img_idx, img_url in enumerate(images):
                        signed_url = img_url if str(img_url).startswith("http") else sign_blob_url(str(img_url))
 # It’s already a good URL from posts+cap.json

                        key = (caption, normalize_url(signed_url))
                        if key in seen:
                            continue
                        seen.add(key)
                        with cols[idx]:
                            st.image(signed_url, caption=_cap(caption), use_container_width=True)

                            
        

                        idx = (idx + 1) % 3
                        

                else:
                    key = (caption, "")
                    if key in seen:
                        continue
                    seen.add(key)
                    with cols[idx]:
                        st.markdown(f"💬 *{caption}*")
                    idx = (idx + 1) % 3 
else:
    classification = st.session_state["classification"]
    chapters = st.session_state["chapters"]
    st.success("🎉 Scrapbook complete!") 

# ── RENDER SCRAPBOOK IF ALREADY GENERATED ─────────────────────────────
# ── RENDER SCRAPBOOK IF ALREADY GENERATED ─────────────────────────────
if "classification" in st.session_state:
    chapters = st.session_state["chapters"]
    classification = st.session_state["classification"]
    st.balloons()
    st.markdown("""
    <div class="card" style="text-align:center">
    <div class="section-title" style="margin-top:0">🎉 Your scrapbook is ready</div>
    <p class="muted">Replace any photo, undo, and download the scrapbook as a PDF.</p>
    </div>
    """, unsafe_allow_html=True)
        # Coverage meter (unique images used / available)
    def _coverage(posts_all, classification):
        all_keys = set()
        for p in posts_all:
            for u in (p.get("images") or p.get("normalized_images") or []):
                if u: all_keys.add(normalize_url(str(u)))
        used = set()
        for plist in classification.values():
            for p in plist:
                for u in p.get("images", []):
                    used.add(normalize_url(str(u)))
        return len(used), max(1, len(all_keys))

    used_ct, total_ct = _coverage(st.session_state.get("all_posts_raw", []), classification)
    pct = round(100.0 * used_ct / total_ct, 1)
    st.info(f"🧮 Coverage: **{used_ct} / {total_ct}** unique images used (**{pct}%**).")



    # ✅ Render all chapters first
    for chap in chapters:
        st.markdown(f"<div class='chapter-title'>📚 {chap}</div>", unsafe_allow_html=True)
        chapter_posts = classification.get(chap, [])
        render_chapter_post_images(chap, chapter_posts, classification, FUNCTION_BASE)
    def _rebuild_pdf_now():
        with st.spinner("Rebuilding your PDF…"):
            st.session_state["pdf_bytes"] = _build_pdf_cached(
                classification, chapters, blob_folder, show_empty_chapters,
                st.session_state.get("profile_summary",""),
                st.session_state.get("pdf_template", "natural")
            )
            st.session_state["pdf_dirty"] = False

    # ✅ Then (dedented!) place ONE download button after the loop
    # ---- 🎨 Design picker (3 choices) ----
    st.markdown("<div class='section-title'>🎨 Choose your download design</div>", unsafe_allow_html=True)

    # Thumbnails you shared (already on disk)
    TPL_PREV_1 = sign_blob_url("app-assets/preview_polaroid.png")
    TPL_PREV_2 = sign_blob_url("app-assets/preview_travel.png")
    TPL_PREV_3 = sign_blob_url("app-assets/preview_natural.png")



    st.session_state.setdefault("pdf_template", "natural")
    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        st.image(TPL_PREV_1, caption="", use_container_width=True)
        if st.button("Use Classic Polaroid", key="tpl_polaroid"):
            st.session_state["pdf_template"] = "polaroid"
            _rebuild_pdf_now()
            st.rerun()

    with cc2:
        st.image(TPL_PREV_2, caption="", use_container_width=True)
        if st.button("Use Travel Scrapbook", key="tpl_travel"):
            st.session_state["pdf_template"] = "travel"
            _rebuild_pdf_now()
            st.rerun()

    with cc3:
        st.image(TPL_PREV_3, caption="", use_container_width=True)
        if st.button("Use Natural Moodboard", key="tpl_natural"):
            st.session_state["pdf_template"] = "natural"
            _rebuild_pdf_now()
            st.rerun()



    sel_map = {
        "polaroid":"Classic Polaroid",
        "travel":"Travel Scrapbook",
        "natural":"Natural Moodboard"
    }
    st.caption(f"Selected design: **{sel_map.get(st.session_state['pdf_template'], 'Classic Polaroid')}**")

    # ---- Build PDF on demand (never automatically on replace/undo/template change) ----
    template = st.session_state.get("pdf_template", "polaroid")

    if st.session_state.get("pdf_bytes") is None:
        st.warning("Building your PDF…")
        _rebuild_pdf_now()


        

    st.markdown('<div class="card" style="position:sticky; bottom:12px; z-index:5;">', unsafe_allow_html=True)
    st.download_button(
        "📥 Download Scrapbook PDF",
        data=st.session_state.get("pdf_bytes") or b"",
        file_name="facebook_scrapbook.pdf",
        mime="application/pdf",
        key="download_pdf_btn",
        disabled=(st.session_state.get("pdf_bytes") is None) or st.session_state.get("pdf_dirty", True)
    )
    st.markdown('</div>', unsafe_allow_html=True)




