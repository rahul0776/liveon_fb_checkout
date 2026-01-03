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
# TOP OF FILE, with your other imports
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

# ---- Debug guard to catch & suppress accidental "None" renders ----
import functools, inspect

def _is_junk_label(x):
    """
    Treat None, 'none/null/undefined', empty strings, and *numeric zeros* as junk.
    This prevents lone '0' from ever rendering as a caption/markdown line.
    """
    try:
        if x is None:
            return True
        if isinstance(x, (int, float)):
            return float(x) == 0.0
        s = str(x).strip()
        if not s:
            return True
        s_low = s.lower()
        if s_low in {"none", "null", "undefined"}:
            return True
        # '0', '00', '0.0' etc…
        if s.replace(".", "", 1).isdigit():
            try:
                return float(s) == 0.0
            except Exception:
                return False
        return False
    except Exception:
        return False

def _guard(fn_name):
    orig = getattr(st, fn_name)
    @functools.wraps(orig)
    def wrapped(*args, **kwargs):
        if args and _is_junk_label(args[0]):
            fr = inspect.stack()[1]
            where = f"{fr.filename.split('/')[-1]}:{fr.lineno}"
            st.sidebar.warning(f"Suppressed junk value passed to st.{fn_name} at {where}")
            return
        return orig(*args, **kwargs)
    return wrapped

for _fn in ("write", "text", "caption", "markdown", "code"):
    setattr(st, _fn, _guard(_fn))

# -------------------------------------------------------------------



# ── PAGE CONFIG ────────────────────────────────────────────────
st.set_page_config(page_title="🧠 Facebook Memories", layout="wide")

from pages.utils.theme import inject_global_styles




inject_global_styles()
st.markdown("""
<style>
:root{
  --navy-900:#0F253D;     /* deep background */
  --navy-800:#143150;
  --navy-700:#1E3A5F;     /* headers / hover */
  --navy-500:#2F5A83;     /* accents */
  --gold:#F6C35D;         /* brand accent */
  --text:#F3F6FA;         /* off-white */
  --muted:#B9C6D6;        /* secondary text */
  --card:#112A45;         /* card bg */
  --line:rgba(255,255,255,.14);
}
/* Page */
html, body, .stApp{
  background: linear-gradient(180deg, var(--navy-900) 0%, var(--navy-800) 55%, var(--navy-700) 100%);
  color: var(--text);
  font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
/* Headings */
h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3{
  color: var(--text) !important;
  letter-spacing:.25px;
  text-align:center;
}
/* Header brand row (logo + title) */
.header-container{
  display:flex; align-items:center; justify-content:center; gap:12px;
  margin: 8px 0 12px 0;
}
.header-container img{
  width:56px; height:auto; filter: drop-shadow(0 2px 8px rgba(0,0,0,.25));
}
.header-title{
  font-weight:800; font-size: 32px; line-height:1.05; letter-spacing:.2px;
}
.header-title .accent{ color: var(--gold); }
/* Hero card */
.hero-box{
  text-align:center; max-width:560px; margin: 6px auto 10px;
  padding: 2rem 2rem;
  background: rgba(255,255,255,.06);
  border: 1px solid var(--line);
  border-radius: 16px;
  box-shadow: 0 6px 16px rgba(0,0,0,.12);
}
.card{ box-shadow: 0 6px 16px rgba(0,0,0,.12); }
/* Primary CTA: style Streamlit buttons like gold CTA */
.stButton>button{
  background: var(--gold) !important;
  color: var(--navy-900) !important; font-weight:800 !important; font-size:17px !important;
  padding: 12px 24px !important; border-radius: 8px !important; border: none !important;
  box-shadow: 0 4px 14px rgba(246,195,93,.22) !important;
  transition: transform .15s ease, box-shadow .15s ease, filter .15s ease !important;
}
.stButton>button:hover{
  filter: brightness(.95);
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(246,195,93,.28) !important;
}
/* Subtext + alerts */
.subtext{ font-size:.95rem; margin-top:.9rem; color: var(--muted); }
div[data-testid="stAlert"]{ border:1px solid var(--line); background: rgba(255,255,255,.06); }
/* Navbar */
.navbar{
  display:flex; justify-content:space-between; align-items:center;
  padding: 1rem 2rem; background: rgba(255,255,255,.04);
  border-bottom: 1px solid var(--line);
  box-shadow: 0 2px 6px rgba(0,0,0,.12);
}
.navbar a{ color: var(--text); text-decoration:none; margin-left:1.2rem; }
.navbar a:hover{ color: var(--gold); }
/* Shared cards/grid/titles for this page */
.card{
  background: rgba(255,255,255,.06);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 18px;
  box-shadow: 0 10px 24px rgba(0,0,0,.18);
  margin-bottom: 18px;
}
.grid-3{ display:grid; grid-template-columns: repeat(3,1fr); gap:16px; }
@media (max-width: 1100px){ .grid-3{ grid-template-columns: repeat(2,1fr);} }
@media (max-width: 700px){ .grid-3{ grid-template-columns: 1fr; } }
.section-title{
  font-size: 1.25rem; font-weight: 800; margin: 22px 0 10px;
  text-align:left; color: var(--text);
}
.badge{ display:inline-block; padding:6px 12px; border-radius:999px;
  background: rgba(255,255,255,.08); color: var(--gold); font-weight:700; }
.muted{ color: var(--muted); }
/* --- Promo strip (small, non-dominant) --- */
.promo-wrap{
  max-width:1100px; margin:8px auto 18px;
  display:grid; grid-template-columns: 1fr 1.2fr; gap:18px;
}
@media (max-width: 900px){ .promo-wrap{ grid-template-columns: 1fr; } }

.promo-grid{ display:grid; grid-template-columns: repeat(2, 1fr); gap:16px; }
@media (max-width: 900px){ .promo-grid{ grid-template-columns: 1fr; } }


.promo-card{
  background: rgba(255,255,255,.06);
  border: 1px solid var(--line);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 6px 16px rgba(0,0,0,.15);
}
/* Promo tiles: show full image, keep aspect, avoid blur */
/* Promo tiles: large, crisp, and full-bleed */
.promo-card img{
  display:block;
  width:100% !important;
  height:220px !important;         /* larger uniform tiles */
  object-fit:cover !important;     /* fill without squish */
  border-bottom:1px solid var(--line);
  border-radius:12px 12px 0 0;
  image-rendering:-webkit-optimize-contrast;
}

.promo-card .caption{
  padding:8px 10px; font-weight:700; font-size:.9rem; color:var(--text);
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
}

.promo-copy{
  background: rgba(255,255,255,.06);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 16px 18px;
  box-shadow: 0 6px 16px rgba(0,0,0,.15);
}
.promo-copy .badge{ color: var(--gold); font-weight:800; }   
/* Scrapbook chapter title */
.chapter-title{
  display:inline-block;
  background:#fff8e6;
  color:#2a2a2a;
  font-weight:800;
  font-size:1.15rem;
  padding:10px 14px;
  border-radius:8px;
  box-shadow: 0 8px 18px rgba(0,0,0,.18);
  border: 1px solid rgba(0,0,0,.06);
  margin: 18px 0 10px;
  position: relative;
}
.chapter-title::before{
  content:"";
  position:absolute;
  width:90px; height:18px;
  top:-10px; left:12px;
  background: linear-gradient(90deg, #f2e5c2, #efe2c0);
  transform: rotate(-2deg);
  box-shadow: 0 4px 8px rgba(0,0,0,.12);
  opacity:.9;
  border-radius:4px;
}       
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.chapter-title{
  background: transparent !important;
  color: var(--text) !important;
  border: 1px dashed var(--line) !important;
  box-shadow: none !important;
}
.chapter-title::before{ display:none !important; }
</style>
""", unsafe_allow_html=True)


st.markdown("""
<style>
:root{
  --navy-900:#0b1220;
  --navy-800:#0e172a;
  --navy-700:#111827;
  --card:#0f172a;
  --text:#e5e7eb;
  --muted:#9ca3af;
  --line:rgba(255,255,255,.10);
  /* repurpose 'gold' as primary accent */
  --gold:#6366F1; /* indigo-500 */
}
.stButton>button{
  background: var(--gold) !important;
  color: #fff !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.brandbar{
  max-width:1100px;
  margin:6px auto 6px;
  display:flex;
  align-items:center;
  gap:10px;
}
.brandbar img{
  width:44px; height:auto;
  filter: drop-shadow(0 2px 8px rgba(0,0,0,.25));
}
.brandbar .wordmark{
  font-weight:900;
  font-size:26px;
  letter-spacing:.2px;
  color: var(--text);
}
.brandbar .wordmark b{ color: var(--gold); }
</style>
""", unsafe_allow_html=True)


st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Patrick+Hand&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)





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


def _ours_blob_path(u: str) -> str | None:
    """
    If u is our Azure HTTPS URL or a raw blob-path, return the blob-path.
    Else return None.
    """
    if not isinstance(u, str) or not u.strip():
        return None
    u = u.strip()
    # raw blob-like "folder/images/x.jpg"
    if ("/" in u) and (not u.startswith("http")) and (not u.lower().startswith("app-assets/")):
        return u
    # https://<account>.blob.core.windows.net/backup/<blob_path>[?...]  -> <blob_path>
    return _to_blob_path_if_ours_https(u)

def _prefer_azure(images: list[str]) -> list[str]:
    """
    If any Azure blobs exist in `images`, return ONLY those (as blob-paths).
    Otherwise return the original list (non-empty items only).
    """
    azure_paths, others = [], []
    for s in images or []:
        if not _is_displayable_image_ref(s):
            continue
        bp = _ours_blob_path(s)
        if bp:
            azure_paths.append(bp)          # store as blob paths
        else:
            others.append(s)
    return azure_paths if azure_paths else others


def make_safe_key(chap, idx, img_url):
    """Generate a unique and safe Streamlit key using a hash."""
    base = f"{chap}_{idx}_{img_url}"
    return hashlib.md5(base.encode("utf-8")).hexdigest()


# 🆕 Normalize URLs to remove query params for deduplication
def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    clean = parsed._replace(query="", fragment="")
    return urlunparse(clean)
# Canonical key for duplicate detection (handles fbcdn size buckets & Azure)
def _canon_for_dedupe(u: str) -> str:
    s = (u or "").strip()
    if not s:
        return ""
    # Map our Azure HTTPS back to a stable blob path
    blob_path = _to_blob_path_if_ours_https(s)
    if blob_path:
        s = blob_path

    from urllib.parse import urlparse, urlunparse
    pu = urlparse(s)
    path = pu.path

    import re
    # Collapse fbcdn “size bucket” and crop segments
    path = re.sub(r"/(?:p|s)\d+x\d+/", "/", path)       # /p640x640/, /s720x720/
    path = re.sub(r"/c\d+\.\d+\.\d+\.\d+/", "/", path)  # /c0.0.720.720/
    path = re.sub(r"/(?:a|v)\d+/", "/", path)           # /a123/, /v123/

    # Normalize filename variant: *_n.jpg, *_o.jpg, *_b.jpg → .jpg
    path = re.sub(r"(_[a-z])\.(jpe?g|png|webp)$", r".\2", path, flags=re.I)

    # Normalize slashes & lowercase extension
    path = re.sub(r"/{2,}", "/", path)
    path = re.sub(r"\.(JPG|JPEG|PNG|WEBP)$", lambda m: "." + m.group(1).lower(), path)

    # Return just a stable, lowercase key (no query/fragment/host)
    return urlunparse(pu._replace(path=path, query="", fragment="", netloc="", scheme="")).lower()


def _cap(s) -> str:
    """Return a safe caption string; strip any 'None' artifacts and zero-width junk."""
    if not s:
        return ""
    s = str(s).strip()
    if not s or s.lower() in {"none", "null", "undefined"}:
        return ""
    if s.isdigit():                # <-- ADD THIS: drop digit-only captions like "0"
        return ""
    # strip trailing ‘🧠 None’ (various dashes/spaces) or standalone 🧠 with nothing useful
    s = re.sub(r"(?:\s*[–—-]\s*)?🧠\s*(?:none|null|undefined)?\s*$", "", s, flags=re.IGNORECASE).strip()
    # strip quoted empties
    s = re.sub(r"^[\"'“”]+|[\"'“”]+$", "", s).strip()
    return s


def _text(s) -> str:
    if s is None:
        return ""
    # treat numbers / number-like strings (e.g., "0", "1") as empty captions
    if isinstance(s, (int, float)):
        return "" if s == 0 else str(s).strip()
    s = str(s).strip()
    if s.lower() in {"none","null","undefined","na","n/a"}:
        return ""
    if s.isdigit() and len(s) <= 2:   # drop "0", "1", etc.
        return ""
    return s

def _is_numeric_only(x) -> bool:
    """True for 0, '0', ' 23 ', etc."""
    if x is None:
        return False
    if isinstance(x, (int, float)):
        return True
    s = str(x).strip()
    return s.isdigit()

def _safe_caption(c) -> str | None:
    """
    Normalize caption for st.image:
    - drop None / '', 'none', 'null', 'undefined'
    - drop numeric-only (0, '0', '12' etc.)
    - return a clean string otherwise (or None to suppress caption entirely)
    """
    if c is None:
        return None
    s = str(c).strip()
    if not s or s.lower() in {"none", "null", "undefined"}:
        return None
    if _is_numeric_only(s):
        return None
    return s

def _clean_images_list(values):
    """Remove empty / numeric-only entries from a post's images list."""
    out = []
    for v in (values or []):
        if v is None:
            continue
        s = str(v).strip()
        if not s or _is_numeric_only(s):
            continue
        out.append(v)
    return out

def compose_caption(message, context):
    m = _text(message)
    # extra guard in case something slips through
    if m.isdigit(): 
        m = ""
    c = _text(context)
    if m and c:
        return f"{m} — 🧠 {c}"
    return m or (f"🧠 {c}" if c else "📷")

def _craft_caption_via_function(message: str, context: str) -> str:
    # Pure local: stay compatible with older Function App (no /craft_caption route)
    return compose_caption(message, context)

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



# ── Session Restoration (Robust) ─────────────────────────────
def qp_get(name, default=None):
    try:
        return st.query_params.get(name)
    except Exception:
        return st.experimental_get_query_params().get(name, [default])[0]

def safe_token_hash(token: str) -> str:
    return hashlib.md5(token.encode()).hexdigest()

def restore_session():
    """
    Restore only from a per-user cache file identified by a URL query param (?cache=<hash>)
    or from the exact file for the current in-memory token. Never scan all users' files.
    """
    if st.session_state.get("fb_token") and st.session_state.get("fb_id") and st.session_state.get("fb_name"):
        return

    cache_dir = Path("cache")
    if not cache_dir.exists():
        return

    # 1) Prefer hash from URL
    token_hash = qp_get("cache")
    path = None
    if token_hash:
        cand = cache_dir / f"backup_cache_{token_hash}.json"
        if cand.exists():
            path = cand

    # 2) If we already have a token in memory, try its exact file
    if not path and st.session_state.get("fb_token"):
        cand = cache_dir / f"backup_cache_{safe_token_hash(st.session_state['fb_token'])}.json"
        if cand.exists():
            path = cand

    if not path:
        return

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        token = data.get("fb_token")
        if not token:
            return

        st.session_state["fb_token"] = token
        latest = data.get("latest_backup") or {}
        st.session_state["fb_id"] = str(latest.get("user_id") or "")
        st.session_state["fb_name"] = latest.get("Name")
        st.session_state["latest_backup"] = latest
        st.session_state["new_backup_done"] = data.get("new_backup_done")
        
        # Restore selection state
        if data.get("selected_backup"):
            st.session_state["selected_backup"] = data["selected_backup"]
        if data.get("selected_project"):
            st.session_state["selected_project"] = data["selected_project"]
    except Exception:
        pass

def persist_session():
    token = st.session_state.get("fb_token")
    if not token:
        return

    cache_dir = Path("cache")
    cache_dir.mkdir(exist_ok=True)
    
    cache = {
        "fb_token": token,
        "latest_backup": st.session_state.get("latest_backup"),
        "new_backup_done": st.session_state.get("new_backup_done"),
        "selected_backup": st.session_state.get("selected_backup"),
        "selected_project": st.session_state.get("selected_project"),
    }
    if st.session_state.get("fb_id") or st.session_state.get("fb_name"):
        cache["latest_backup"] = cache.get("latest_backup", {}) | {
            "user_id": st.session_state.get("fb_id"),
            "name": st.session_state.get("fb_name"),
        }
        
    # Save to user-specific cache file
    cache_file = cache_dir / f"backup_cache_{safe_token_hash(token)}.json"
    with open(cache_file, "w") as f:
        json.dump(cache, f)



restore_session()
if "fb_token" not in st.session_state:
    st.warning("Please login with Facebook first.")
    st.stop()

# ── Check for Posts Permission (Required for Storybook) ─────────────────────────────
def check_posts_permission(token: str) -> bool:
    """Check if the access token has user_posts permission using debug token endpoint."""
    try:
        # Method 1: Use Facebook's debug token endpoint to check actual permissions
        app_access_token = f"{st.secrets['FB_CLIENT_ID']}|{st.secrets['FB_CLIENT_SECRET']}"
        response = requests.get(
            f"https://graph.facebook.com/debug_token",
            params={
                "input_token": token,
                "access_token": app_access_token
            },
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if "data" in data:
                scopes = data.get("data", {}).get("scopes", [])
                # Check if user_posts is in the granted scopes
                has_posts = "user_posts" in scopes
                return has_posts
    except Exception as e:
        pass  # Fall through to fallback method
    
    # Fallback Method 2: Try to access posts endpoint directly
    try:
        response = requests.get(
            f"https://graph.facebook.com/me/posts?limit=1&access_token={token}",
            timeout=5
        )
        if response.status_code == 200:
            # Successfully accessed posts - permission exists
            return True
        # Check for permission error
        data = response.json()
        if "error" in data:
            error = data.get("error", {})
            error_code = error.get("code", 0)
            error_type = error.get("type", "")
            # Error code 200 or "OAuthException" with "permission denied" = no permission
            if error_code == 200 or (error_type == "OAuthException" and "permission" in error.get("message", "").lower()):
                return False
    except Exception:
        pass
    
    # If we can't determine, assume no permission (safer for App Review)
    return False

def build_posts_auth_url() -> str:
    """Build OAuth URL for requesting posts permission."""
    from urllib.parse import urlencode
    import hmac, hashlib, json, base64, time, secrets as pysecrets
    
    def _b64e(b: bytes) -> str:
        return base64.urlsafe_b64encode(b).decode().rstrip("=")
    
    def make_state(extra_data: dict = None) -> str:
        payload = {"ts": int(time.time()), "nonce": pysecrets.token_urlsafe(16)}
        if extra_data:
            payload.update(extra_data)
        raw = json.dumps(payload, separators=(",", ":")).encode()
        sig = hmac.new(st.secrets["STATE_SECRET"].encode(), raw, hashlib.sha256).digest()
        return _b64e(raw) + "." + _b64e(sig)
    
    CLIENT_ID = st.secrets["FB_CLIENT_ID"]
    REDIRECT_URI = st.secrets["FB_REDIRECT_URI"]
    
    # Request additional permission: user_posts
    scopes = "public_profile,user_photos,user_posts"
    
    # Capture current selection state to persist across redirect
    extra_data = {"return_to": "memories"}
    if st.session_state.get("selected_backup"):
        extra_data["selected_backup"] = st.session_state["selected_backup"]
    if st.session_state.get("selected_project"):
        extra_data["selected_project"] = st.session_state["selected_project"]

    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,  # Clean URI (no query params) to match whitelist
        "scope": scopes,
        "response_type": "code",
        "state": make_state(extra_data=extra_data), # Pass intent and selection in state
        "auth_type": "rerequest",  # Force re-request even if previously denied
    }
    return "https://www.facebook.com/v18.0/dialog/oauth?" + urlencode(params)

# Check if user has posts permission
has_posts_permission = False
try:
    has_posts_permission = check_posts_permission(st.session_state["fb_token"])
except Exception as e:
    # If check fails, assume no permission (safer for App Review)
    # This ensures we always show the permission request UI if we can't verify
    has_posts_permission = False

# Debug: Check if we should force permission request (for App Review compliance)
# Even if user has posts permission, we might want to show the flow for new logins
# But for now, we'll only request if they don't have it
force_permission_check = st.session_state.get("force_posts_permission_check", False)

# For testing: Add a button to force permission check
if st.session_state.get("show_debug", False):
    if st.button("🔍 Debug: Check Posts Permission"):
        try:
            result = check_posts_permission(st.session_state["fb_token"])
            st.info(f"Posts permission check result: {result}")
        except Exception as e:
            st.error(f"Error checking permission: {e}")

# Handle OAuth return for posts permission
qp = st.query_params
if qp.get("return_to") == "memories" and qp.get("code"):
    # User just granted posts permission, refresh token
    code = qp.get("code")
    if isinstance(code, list):
        code = code[0]
    
    try:
        response = requests.get(
            "https://graph.facebook.com/v18.0/oauth/access_token",
            params={
                "client_id": st.secrets["FB_CLIENT_ID"],
                "redirect_uri": st.secrets["FB_REDIRECT_URI"] + "?return_to=memories",
                "client_secret": st.secrets["FB_CLIENT_SECRET"],
                "code": code,
            },
            timeout=10,
        )
        if response.status_code == 200:
            new_token = response.json().get("access_token")
            if new_token:
                st.session_state["fb_token"] = new_token
                st.success("✅ Posts permission granted! You can now create your storybook.")
                # Clear query params
                try:
                    st.query_params.clear()
                except:
                    pass
                st.rerun()
    except Exception as e:
        st.error(f"Failed to update permissions: {e}")

# Show permission request UI if user doesn't have posts permission
# For App Review: This demonstrates the two-stage permission flow
# If user already has permission (from old login), they can proceed directly
# 
# Test mode: Add ?test_permission=1 to URL to force permission request UI
test_mode = st.query_params.get("test_permission") == "1"
show_permission_ui = not has_posts_permission or test_mode

# Debug: Show permission status
st.sidebar.markdown("### 🔍 Permission Debug Info")
st.sidebar.info(f"Has posts permission: **{has_posts_permission}**")
st.sidebar.info(f"Test mode: **{test_mode}**")
st.sidebar.info(f"Show permission UI: **{show_permission_ui}**")

if show_permission_ui:
    st.markdown("""
    <div class="card" style="text-align:center; padding:40px;">
        <h2>📘 Create Your Storybook</h2>
        <p style="font-size:1.1rem; margin:20px 0;">
            To create your personalized Facebook storybook, we need access to your posts and photos.
        </p>
        <p style="color:var(--muted); margin-bottom:30px;">
            This allows us to organize your memories into beautiful chapters and create a meaningful storybook for you.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    auth_url = build_posts_auth_url()
    st.markdown(f"""
    <div style="text-align:center; margin:20px 0;">
        <a href="{auth_url}" class="fb-button" style="display:inline-block; padding:14px 28px; font-size:18px;">
            🔐 Grant Posts Permission to Create Storybook
        </a>
    </div>
    """, unsafe_allow_html=True)
    
    st.info("💡 **Why we need this:** Your posts contain the stories and context that make your storybook meaningful. We only use this data to create your personalized storybook.")
    st.stop()

# --- Session defaults ---
if "undo_stack" not in st.session_state:
    st.session_state["undo_stack"] = {}
# --- PDF state (do NOT auto-regenerate on every rerun) ---
st.session_state.setdefault("pdf_bytes", None)     # last built PDF bytes
st.session_state.setdefault("pdf_dirty", True)     # mark needs rebuild



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
#blob_names = [blob.name for blob in container_client.list_blobs()]

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
    """
    Return a SAS URL for a blob path, but keep it STABLE for this session
    so the browser can cache images across reruns.
    """
    allowed = list(st.session_state.get("_allowed_prefixes") or [])
    if allowed and not any(str(blob_path).startswith(p) for p in allowed):
        return "https://via.placeholder.com/600x400?text=Not+Your+File"

    # 👇 per-session memoization (stable URL prevents re-downloads)
    sas_cache = st.session_state.setdefault("_sas_cache", {})
    if blob_path in sas_cache:
        return sas_cache[blob_path]

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
        url = f"https://{account_name}.blob.core.windows.net/{CONTAINER}/{quote(blob_path, safe='/')}?{sas}"
        sas_cache[blob_path] = url
        return url
    except Exception:
        return "https://via.placeholder.com/600x400?text=Image+Unavailable"

from urllib.parse import unquote

def _to_blob_path_if_ours_https(raw_url: str) -> str | None:
    """
    If raw_url is like:
    https://<account>.blob.core.windows.net/backup/<blob_path>[?...]  → return <blob_path>
    Otherwise return None.
    """
    try:
        u = urlparse(str(raw_url))
        if u.scheme in ("http", "https") and u.netloc.split(".")[0] == blob_service_client.account_name:
            if u.path.startswith(f"/{CONTAINER}/"):
                return u.path[len(f"/{CONTAINER}/"):].lstrip("/")
    except Exception:
        return None
    return None

def to_display_url(u: str) -> str:
    """
    Always return a displayable URL:
    - blob paths (e.g. 'fbid/folder/images/x.jpg') → SAS via sign_blob_url(...)
    - our Azure HTTPS URLs (no SAS) → convert to blob path and sign
    - non-Azure HTTP URLs → return unchanged
    - already-signed (?sig=) → return unchanged
    """
    if not u:
        return ""
    s = str(u)
    if s.startswith("http"):
        # already has a SAS?
        if "sig=" in s:
            return s
        # our storage account & container → re-sign
        blob_path = _to_blob_path_if_ours_https(s)
        return sign_blob_url(blob_path) if blob_path else s
    # plain blob path → sign
    return sign_blob_url(s)
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

# Limit what this session is allowed to render/sign:
#  - the current user's folder (blob_folder)
#  - the shared "app-assets" folder used by themes
st.session_state["_allowed_prefixes"] = [
    f"{str(blob_folder).strip('/')}/",
    "app-assets/"
]
# Extra guard: a backup must start with fb_id/
fb_id = str(st.session_state.get("fb_id") or "")
if not is_project and fb_id:
    if not str(blob_folder).startswith(f"{fb_id}/"):
        st.error("⚠️ This backup does not belong to your account.")
        st.stop()
#st.write("📂 Trying to load from blob folder:", blob_folder)
# Reset per-folder state when the folder changes (prevents cross-user/project bleed)
_prev = st.session_state.get("_blob_folder")
if _prev != blob_folder:
    st.session_state["_blob_folder"] = blob_folder
    st.session_state.pop("classification", None)
    st.session_state.pop("chapters", None)
    st.session_state["pdf_bytes"] = None
    st.session_state["pdf_dirty"] = True
    st.session_state.pop("_sas_cache", None)  # 👈 also reset SAS memoization





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

#st.markdown(f"<div class='section-title'>📘 {project_name}</div>", unsafe_allow_html=True)
#st.caption(f"Project: {project_name}")





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

def fetch_posts_from_api(token: str, max_pages: int = 50) -> list[dict]:
    """Fetch posts from Facebook Graph API."""
    url = f"https://graph.facebook.com/me/posts?fields=id,message,created_time,full_picture,attachments{{media}}&limit=100&access_token={token}"
    all_posts = []
    pages = 0
    
    while url and pages < max_pages:
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            data = response.json()
            
            if "error" in data:
                st.error(f"Error fetching posts: {data['error'].get('message')}")
                break
            
            all_posts.extend(data.get("data", []))
            url = data.get("paging", {}).get("next")
            pages += 1
        except Exception as e:
            st.error(f"Error fetching posts: {e}")
            break
    
    return all_posts

def save_posts_to_blob(posts: list[dict], blob_folder: str):
    """Save fetched posts to Azure Blob Storage."""
    try:
        blob_path = f"{blob_folder}/posts+cap.json"
        data = json.dumps(posts, indent=2, ensure_ascii=False)
        container_client.get_blob_client(blob_path).upload_blob(data, overwrite=True)
    except Exception as e:
        st.error(f"Failed to save posts to storage: {e}")



def call_function(endpoint:str, payload:dict, timeout:int=90):
    url = f"{FUNCTION_BASE}/{endpoint}"
    try:
        res = requests.post(url, json=payload, timeout=timeout)
        res.raise_for_status()
        return res
    except requests.exceptions.Timeout:
        if advanced_mode:
            st.error(f"❌ Azure Function timeout: The AI service took longer than {timeout} seconds to respond. Please try again.")
            st.code(f"Debug info: URL={url}, Payload size={len(str(payload))} chars")
        else:
            st.error(f"❌ Azure Function timeout: The AI service took longer than {timeout} seconds to respond. Please try again.")
        st.stop()
    except requests.exceptions.ConnectionError:
        if advanced_mode:
            st.error("❌ Azure Function connection error: Unable to reach the AI service. Please check your internet connection and try again.")
            st.code(f"Debug info: URL={url}")
        else:
            st.error("❌ Azure Function connection error: Unable to reach the AI service. Please check your internet connection and try again.")
        st.stop()
    except requests.exceptions.HTTPError as err:
        if err.response.status_code == 500:
            st.error("❌ Azure Function server error: The AI service encountered an internal error. Please try again in a few minutes.")
            if advanced_mode:
                st.code(f"Debug info: URL={url}, Response: {err.response.text[:200]}")
        elif err.response.status_code == 429:
            st.error("❌ Azure Function rate limit: Too many requests. Please wait a moment and try again.")
        else:
            st.error(f"❌ Azure Function HTTP error ({err.response.status_code}): {err}")
            if advanced_mode:
                st.code(f"Debug info: URL={url}, Response: {err.response.text[:200]}")
        st.stop()
    except requests.exceptions.RequestException as err:
        if advanced_mode:
            st.error(f"❌ Azure Function error: {err}")
            st.code(f"Debug info: URL={url}")
        else:
            st.error(f"❌ Azure Function error: {err}")
        st.stop()

# --- FORCE-JSON chapter parser ---
def parse_chapters_strict(raw: str) -> list[str]:
    """
    Expect JSON like {"chapters": ["A", "B", ...]}.
    If the model wrapped it in text or code fences, try to extract the JSON.
    Falls back to a loose parser as a last resort.
    """
    raw = (raw or "").strip()

    # A) direct JSON
    try:
        data = json.loads(raw)
    except Exception:
        data = None

    # B) JSON fenced/embedded somewhere in the text
    if not isinstance(data, (dict, list)):
        m = re.search(r"\{[\s\S]*\}", raw)  # first {...}
        if m:
            try:
                data = json.loads(m.group(0))
            except Exception:
                data = None

    chapters: list[str] = []
    if isinstance(data, dict) and isinstance(data.get("chapters"), list):
        chapters = [str(t).strip() for t in data["chapters"] if isinstance(t, str) and str(t).strip()]
    elif isinstance(data, list):  # rare case: model returned a bare list
        chapters = [str(t).strip() for t in data if isinstance(t, str) and str(t).strip()]

    # C) Last-resort fallback: your loose text extractor
    if not chapters:
        chapters = extract_titles(raw)

    # normalize/clean
    out, seen = [], set()
    for t in chapters:
        t = re.sub(r"\s+", " ", t).strip(' "\'“”')
        if len(t) < 3 or t.lower() in {"none", "null", "undefined"}:
            continue
        if t not in seen:
            seen.add(t); out.append(t)

    # enforce a reasonable count
    return out[:12]
# ── HELPERS ────────────────────────────────────────────────
def _is_displayable_image_ref(u) -> bool:
    if not isinstance(u, str):
        return False
    s = u.strip()
    if not s or s.lower() in {"none","null","undefined","download failed"}:
        return False
    if s.isdigit():
        return False
    if s.lower().startswith("app-assets/"):
        return False
    return s.startswith("http") or ("/" in s)
def _scrub_classification(cls: dict) -> dict:
    """
    Make sure every post has:
      - images: list[str] with only real URLs/blob paths (no '0', 'None', app-assets)
      - message/context_caption: cleaned text (no numeric-only like '0')
    Drop empty/bad posts and normalise single-image fields.
    """
    def _ok_img(u):
        if not isinstance(u, str): return False
        s = u.strip()
        if not s or s.lower() in {"none","null","undefined","download failed"}: return False
        if s.isdigit(): return False
        if s.lower().startswith("app-assets/"): return False
        return s.startswith("http") or ("/" in s)

    out = {}
    for chap, items in (cls or {}).items():
        new_items = []
        for p in (items or []):
            q = dict(p)  # shallow copy so we can preserve created_time/why, etc.

            # normalise images
            imgs = q.get("images")
            if imgs is None and "image" in q:
                imgs = [q.get("image")]
            if not isinstance(imgs, list):
                imgs = [imgs] if imgs is not None else []
            imgs = [u for u in imgs if _ok_img(u)]
            q["images"] = imgs
            q.pop("image", None)

            # clean captions
            q["message"] = _text(q.get("message"))
            q["context_caption"] = _text(q.get("context_caption"))

            # keep only meaningful entries
            if imgs or q["message"] or q["context_caption"]:
                new_items.append(q)

        if new_items:
            out[chap] = new_items
    return out

def _post_key(p: dict) -> str:
    """Stable key for a post (prefer true id; otherwise hash of message+created_time+image keys)."""
    pid = p.get("id") or p.get("post_id") or p.get("status_id")
    if pid:
        return str(pid)
    msg = str(p.get("message") or "")
    ct  = str(p.get("created_time") or "")
    img_keys = ",".join(sorted(_canon_for_dedupe(u) for u in (p.get("images") or []) if _is_displayable_image_ref(u)))
    import hashlib
    return hashlib.md5(f"{msg}|{ct}|{img_keys}".encode("utf-8")).hexdigest()

def _dedupe_images_in_post(p: dict) -> dict:
    """Within a single post, drop duplicate image variants (fbcdn sizes, signed URLs, etc.)."""
    seen, keep = set(), []
    for u in (p.get("images") or []):
        if not _is_displayable_image_ref(u):
            continue
        k = _image_key(u)
        if not k or k in seen:
            continue
        seen.add(k)
        keep.append(u)
    q = dict(p)
    q["images"] = keep
    return q

def _dedupe_classification_global(cls: dict, chapter_order: list[str]) -> dict:
    """
    Enforce uniqueness across the WHOLE scrapbook.
    - A post appears in at most one chapter.
    - Any photo appears at most once globally (even if different posts reference it).
    """
    seen_posts, seen_imgs = set(), set()
    out = {}
    for chap in chapter_order:
        filtered = []
        for p in cls.get(chap, []) or []:
            q = _dedupe_images_in_post(p)
            pk = _post_key(q)
            img_keys = [_image_key(u) for u in q.get("images") or [] if _is_displayable_image_ref(u)]


            # If we've already used this post OR any of its images, skip it here
            if pk in seen_posts or any(k in seen_imgs for k in img_keys):
                continue

            seen_posts.add(pk)
            for k in img_keys:
                seen_imgs.add(k)
            filtered.append(q)

        if filtered:
            out[chap] = filtered
    return out
# ---- Stronger de-dupe: prefer content fingerprint for our Azure blobs ----
def _blob_fingerprint(blob_path: str) -> str | None:
    """Return a stable 'md5:<hex>' or 'etag:<value>' for a blob path; cache per session."""
    cache = st.session_state.setdefault("_blob_fp_cache", {})
    if blob_path in cache:
        return cache[blob_path]
    try:
        bc = container_client.get_blob_client(blob_path)
        if not bc.exists():
            return None
        props = bc.get_blob_properties()
        # azure-storage-blob exposes MD5 either at props.content_settings.content_md5 (bytes) or props.content_md5
        md5 = getattr(getattr(props, "content_settings", None), "content_md5", None) or getattr(props, "content_md5", None)
        if md5:
            fp = "md5:" + (md5.hex() if isinstance(md5, (bytes, bytearray)) else str(md5))
        else:
            etag = getattr(props, "etag", None)
            fp = "etag:" + str(etag).strip('"') if etag else None
        if fp:
            cache[blob_path] = fp
        return fp
    except Exception:
        return None

def _image_key(u: str) -> str:
    """
    Stable key for dedupe:
    1) If it's our Azure blob (URL or raw path), use content fingerprint (md5/etag).
    2) Otherwise, fall back to path-based canonicalization.
    """
    s = (u or "").strip()
    if not s:
        return ""
    # Map our https → blob path, or accept raw blob path; ignore app-assets
    blob_path = _to_blob_path_if_ours_https(s) or (s if ("/" in s and not s.startswith("http")) else None)
    if blob_path and not blob_path.lower().startswith("app-assets/"):
        fp = _blob_fingerprint(blob_path)
        if fp:
            return fp
    return "path:" + _canon_for_dedupe(s)

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
        why = p.get("why", {})
        if isinstance(why, dict) and "score" in why and advanced_mode:
            caption = f"{caption}  | 🧭 match={why['score']}"



        images = p.get("images", [])
        if not images:
            images = ["https://via.placeholder.com/300x200?text=No+Image+Available"]
        # ✅ SANITIZE

        raw_images = p.get("images") or []
        images = _prefer_azure([u for u in raw_images if _is_displayable_image_ref(u)])
        if not images:
            images = ["https://via.placeholder.com/300x200?text=No+Image+Available"]


        for img in images:
            if not img:
                continue
            # keep the original for display (preserves SAS/query)
            display_url = to_display_url(img)



            # use a normalized key ONLY for dedupe
            # use a content fingerprint (md5/etag) when available
            key = _image_key(img)
            if key in seen_urls:
                continue
            seen_urls.add(key)


            all_items.append(("image", display_url, caption))



    # 4-column grid layout
    cols = st.columns([1, 1, 1, 1])
    for idx, (kind, img_url, caption) in enumerate(all_items):
        with cols[idx % 4]:
            if kind == "image":
                try:
                    #st.image(img_url, caption=_cap(caption), use_container_width=True)
                    cap = _safe_caption(caption)
                    st.image(img_url, caption=cap, use_container_width=True)

                except:
                    _cap_text = _cap(caption)[:80]
                    if _cap_text:
                        st.image("https://via.placeholder.com/600x400?text=Image+Unavailable",
                                caption=_cap_text, use_container_width=True)
                    else:
                        st.image("https://via.placeholder.com/600x400?text=Image+Unavailable",
                                use_container_width=True)





# 🆕 CHANGE: Dynamic max_per_chapter calculation
def calculate_max_per_chapter(chapters, posts):
    posts_per_page = 3
    target_pages = 50
    total_posts = posts_per_page * target_pages
    chapters_count = len(chapters)
    return total_posts // chapters_count

def render_chapter_post_images(chap_title, chapter_posts, classification, FUNCTION_BASE):
    import json, requests
    st.markdown("<div class='card'><div class='grid-3'>", unsafe_allow_html=True)

    # always 3 columns (we’re ignoring minimal UI now)
    cols = st.columns(3)

    seen_urls: set[str] = set()

    for post_idx, post in enumerate(chapter_posts):
        images = post.get("images", []) or ([post.get("image")] if "image" in post else [])
        images = _prefer_azure([u for u in images if _is_displayable_image_ref(u)])
            
        if not images:
            continue

        caption = _unique_caption(_craft_caption_via_function(post.get("message"), post.get("context_caption")))

        why = post.get("why", {})
        if isinstance(why, dict) and "score" in why and advanced_mode:
            caption = f"{caption}  | 🧭 match={why['score']}"

        for img_idx, img_url in enumerate(images):
            with cols[post_idx % len(cols)]:   # ✅ safe modulo (fixes IndexError)
                display_url = to_display_url(img_url)
                key = _image_key(img_url)
                if key in seen_urls:
                    continue
                seen_urls.add(key)


                try:
                    cap = _safe_caption(caption)
                    # --- final guard (prevents lone '0' from ever showing) ---
                    if isinstance(cap, (int, float)):
                        cap = None
                    elif isinstance(cap, str):
                        s = cap.strip()
                        if (s.replace(".", "", 1).isdigit() and float(s or 0) == 0.0):
                            cap = None
                    st.image(display_url, caption=cap, use_container_width=True)

                except Exception:
                    _cap_text = _cap(caption)[:80]
                    if _cap_text:
                        st.image("https://via.placeholder.com/600x400?text=Image+Unavailable",
                                caption=_cap_text, use_container_width=True)
                    else:
                        st.image("https://via.placeholder.com/600x400?text=Image+Unavailable",
                                use_container_width=True)


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
    def _coverage(posts_all, classification):
        all_keys, used = set(), set()
        for p in posts_all:
            for u in (p.get("images") or p.get("normalized_images") or []):
                if _is_displayable_image_ref(u):
                    all_keys.add(_image_key(u))
        for plist in classification.values():
            for p in plist:
                for u in p.get("images", []):
                    if _is_displayable_image_ref(u):
                        used.add(_image_key(u))
        return len(used), max(1, len(all_keys))
    for p in classification.get(chap, []):
        imgs = p.get("images", []) or ([p.get("image")] if "image" in p else [])
        # ✅ SANITIZE
        imgs = [u for u in imgs if _is_displayable_image_ref(u)]
        if not imgs:
            continue

        crafted = _unique_caption(_craft_caption_via_function(p.get("message"), p.get("context_caption")))

        date_s = _nice_date(p.get("created_time"))
        for u in imgs:
            items.append({"img": u, "caption": crafted, "date": date_s})

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
    url = to_display_url(url)


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

def _preview_asset(name: str) -> str:
    """
    Return a guaranteed-displayable URL for the design preview tiles.
    Uses the real blob if present; otherwise a placeholder image.
    """
    try:
        blob_path = f"app-assets/{name}"
        bc = container_client.get_blob_client(blob_path)
        if bc.exists():
            return sign_blob_url(blob_path)
    except Exception:
        pass
    return "https://via.placeholder.com/800x500?text=Preview+Not+Found"

# ---- Asset URLs (define AFTER _preview_asset & container_client exist) ----
# Use an existing high-res brand tile as the header mark (no broken ALT).
LOGO_URL = _preview_asset("promo_liveon.png")
PROMO1   = _preview_asset("promo_liveon.png")
PROMO2   = _preview_asset("promo_zip_to_story.png")
PROMO3   = _preview_asset("promo_crafted.png")

PROMO1_2x = _preview_asset("promo_liveon@2x.png")

# only add a srcset tag if the @2x file actually exists
PROMO1_2x_TAG = f' srcset="{PROMO1_2x} 2x"' if ("Preview+Not+Found" not in PROMO1_2x and PROMO1_2x != PROMO1) else ""

# ---------- EXTRA HEADER ASSETS (add right below LOGO_URL / PROMOs) ----------
PAPER_TXT = _preview_asset("paper_bg.jpg")
TAPE_URL  = _preview_asset("tape.png")
HERO_IMG1 = _preview_asset("preview_polaroid.png")  # left/top photo
HERO_IMG2 = _preview_asset("promo_liveon.png")      # right/bottom photo

# brand row (replaces .header-container)
st.markdown(f"""
<div class="brandbar">
  <img src="{LOGO_URL}" alt="LiveOn">
  <div class="wordmark">Facebook <b>Memories</b></div>
</div>
""", unsafe_allow_html=True)





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
                cap = (_safe_caption(it.get("caption","")) or "")[:90]
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
                    caption=_cap(it.get("caption",""))[:90],
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
        items, seen = [], set()
        for p in classification.get(chap, []):
            imgs = p.get("images", []) or ([p.get("image")] if "image" in p else [])
            imgs = [u for u in imgs if _is_displayable_image_ref(u)]
            if not imgs:
                continue
            crafted = _unique_caption(_craft_caption_via_function(p.get("message"), p.get("context_caption")))
            date_s  = _nice_date(p.get("created_time"))
            for u in imgs:
                k = _image_key(u)
                if k in seen: 
                    continue
                seen.add(k)
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

def _scrapbook_ck(
    classification: dict,
    chapters: list[str],
    blob_folder: str,
    template: str
) -> str:
    """
    Stable content key for caching, based on the *actual* scrapbook content.
    """
    def _norm(u):
        # use the same key we dedupe on, so blob variants don’t change the cache key
        try:
            return _image_key(str(u))
        except Exception:
            return str(u) if u is not None else ""

    sig = []
    for chap in chapters or []:
        for p in (classification or {}).get(chap, []):
            imgs = p.get("images", []) or ([p.get("image")] if p.get("image") else [])
            for u in imgs:
                sig.append(_norm(u))
    raw = json.dumps([sig, chapters, blob_folder, template], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

@st.cache_data(show_spinner=False)
def _build_pdf_cached(
    classification: dict,
    chapters: list[str],
    blob_folder: str,
    show_empty_chapters: bool,
    profile_summary: str,
    template: str,
    _ck: str  # content key to control caching
) -> bytes:
    return build_pdf_bytes(
        classification=classification,
        chapters=chapters,
        blob_folder=blob_folder,
        show_empty_chapters=show_empty_chapters,
        profile_summary=profile_summary,
        template=template
    )


# ── UI ─────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚙️ Settings")
    advanced_mode = st.checkbox("Enable Advanced Mode (debug)", value=False)
    
    if advanced_mode:
        if st.button("🧪 Test Permission UI"):
            st.query_params["test_permission"] = "1"
            st.rerun()
            
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
    
    # 🆕 Auto-fetch if empty but permission exists
    if not posts and has_posts_permission:
        with st.spinner("📥 Fetching your posts from Facebook..."):
            try:
                # We need to define this helper or move it up. 
                # Since we can't easily move the existing one without messing up line numbers, 
                # I'll define a robust one here or use the one I'm about to add.
                # Let's assume I added the helper above.
                posts = fetch_posts_from_api(st.session_state["fb_token"])
                if posts:
                    save_posts_to_blob(posts, blob_folder)
                    # Clear cache so the next load sees the new data
                    load_all_posts_from_blob.clear()
                    st.success(f"✅ Fetched {len(posts)} posts!")
                    st.rerun()
                else:
                    st.warning("⚠️ No posts found on your Facebook timeline.")
                    st.stop()
            except Exception as e:
                st.error(f"Failed to fetch posts: {e}")
                st.stop()

    if not posts:
        st.warning("⚠️ No posts found in blob storage. Upload some and try again.")
        st.stop()
    # Clean, true count (after dedupe), no folder/chapters noise
    st.success(f"✅ Loaded {len(posts)} unique posts")
    st.session_state["all_posts_raw"] = posts
    for p in posts:
        # clean text
        if _is_numeric_only(p.get("message")):
            p["message"] = ""
        else:
            p["message"] = _text(p.get("message"))

        if _is_numeric_only(p.get("context_caption")):
            p["context_caption"] = ""
        else:
            p["context_caption"] = _text(p.get("context_caption"))

        # collect images from common fields
        imgs = []
        if "images" in p and isinstance(p["images"], list):
            imgs = p["images"]
        elif isinstance(p.get("full_picture"), str) and p["full_picture"].startswith("http"):
            imgs = [p["full_picture"]]
        elif isinstance(p.get("picture"), str) and p["picture"].startswith("http"):
            imgs = [p["picture"]]

        # sanitize, then prefer Azure versions and drop external fbcdn if any Azure exists
        imgs = _clean_images_list(imgs)
        imgs = _prefer_azure(imgs)

        # store as blob-paths when possible; display signing happens later
        p["images"] = imgs
        p["normalized_images"] = imgs

        # a combined text that never shows lone zeros
        message = p.get("message") or ""
        caption = p.get("context_caption") or ""
        combined = message
        if caption and caption not in message:
            combined += f" — {caption}"
        p["combined_text"] = combined or "📷"


    # --- Minimal 3-image hero (now uses promo images) ---
    h1, h2, h3 = PROMO1, PROMO2, PROMO3  # <- use your promo tiles

    st.markdown(f"""
    <div class="hero-min">
    <div class="copy">
        <h1>Facebook <span>Memories</span></h1>
        <p class="sub">Relive your favorite moments in a beautiful, organized view.</p>
    </div>
    <div class="tri">
        <img src="{h1}" class="card c1" alt="promo 1">
        <img src="{h2}" class="card c2" alt="promo 2">
        <img src="{h3}" class="card c3" alt="promo 3">
        <div class="dots"><span></span><span></span><span></span></div>
    </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <style>
    .hero-min{
    max-width:1100px; margin:12px auto 22px;
    display:grid; grid-template-columns: 1.1fr 1fr; gap:28px; align-items:center;
    }
    .hero-min .copy h1{
    margin:0; font-weight:900; font-size:48px; letter-spacing:.2px; color:var(--text); /* bigger middle title */
    }
    .hero-min .copy h1 span{ color:var(--gold); }
    .hero-min .copy .sub{ color:var(--muted); margin-top:6px; font-size:1.06rem; }
    .hero-min .tri{ position:relative; height:280px; }
    .hero-min .tri .card{
    position:absolute; width:58%; aspect-ratio:4/3; object-fit:cover;
    border-radius:14px; box-shadow:0 14px 32px rgba(0,0,0,.35);
    border:1px solid var(--line); background:#111827;
    }
    .hero-min .tri .c1{ left:0; top:18px; transform:rotate(-3deg); }
    .hero-min .tri .c2{ left:22%; top:-8px; transform:rotate(.8deg); z-index:2; }
    .hero-min .tri .c3{ right:0; bottom:0; transform:rotate(3deg); }
    .hero-min .dots{
    position:absolute; left:50%; bottom:-14px; transform:translateX(-50%);
    display:flex; gap:8px;
    }
    .hero-min .dots span{
    width:8px; height:8px; border-radius:50%; background:rgba(255,255,255,.35); display:block;
    }
    @media (max-width: 900px){ .hero-min{ grid-template-columns:1fr; } .hero-min .tri{ height:220px; } }
    </style>
    """, unsafe_allow_html=True)



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

    # ✅ SANITIZE: drop null/placeholder entries to avoid 'None' render
    imgs = [u for u in imgs if _is_displayable_image_ref(u)]

    post["normalized_images"] = imgs

    post["message"] = _text(post.get("message"))
    post["context_caption"] = _text(post.get("context_caption"))
# ── PRIMARY ACTION ────────────────────────────────────────────────────────────
if "classification" not in st.session_state:
    if st.button("📘 Generate Scrapbook",use_container_width=True):
        # Fetch posts from API (since initial backup only has photos)
        # This is needed to create the storybook with posts data
        st.info("📥 Fetching your posts to create your storybook...")
        
        def fetch_posts_from_api(token: str, max_pages: int = 50):
            """Fetch posts from Facebook Graph API."""
            url = f"https://graph.facebook.com/me/posts?fields=id,message,created_time,full_picture,attachments{{media}}&limit=100&access_token={token}"
            all_posts = []
            pages = 0
            
            while url and pages < max_pages:
                try:
                    response = requests.get(url, timeout=20)
                    response.raise_for_status()
                    data = response.json()
                    
                    if "error" in data:
                        st.error(f"Error fetching posts: {data['error'].get('message')}")
                        break
                    
                    all_posts.extend(data.get("data", []))
                    url = data.get("paging", {}).get("next")
                    pages += 1
                except Exception as e:
                    st.error(f"Error fetching posts: {e}")
                    break
            
            return all_posts
        
        # Fetch posts from API
        api_posts = fetch_posts_from_api(st.session_state["fb_token"])
        
        if not api_posts:
            st.error("❌ Could not fetch posts. Please ensure you have granted posts permission.")
            st.stop()
        
        # Merge API posts with existing posts from blob (if any)
        # API posts take precedence
        existing_posts = {p.get("id"): p for p in posts if p.get("id")}
        for api_post in api_posts:
            existing_posts[api_post.get("id")] = api_post
        
        # Update posts list with merged data
        posts = list(existing_posts.values())
        st.session_state["all_posts_raw"] = posts
        st.success(f"✅ Fetched {len(posts)} posts for your storybook")
        
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
            #eval_res  = call_function("ask_about_blob",{"question":eval_prompt,"posts":posts})
            eval_res = call_function("ask_about_blob", {
                "question": eval_prompt,
                "posts": posts,                                 # still send posts
                "filename": f"{blob_folder}/posts.json"         # enables [tenant:<fb_id>] tagging in backend logs
            })
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
                "question": f"""
        You are helping structure a scrapbook. Suggest 6–12 practical, post-grounded chapter titles.

        RULES
        - Only suggest chapters that are clearly supported by the user’s posts.
        - Avoid abstract/philosophical themes.
        - Keep titles short and relatable (3–5 words each). No numbering/bullets.

        RETURN FORMAT (IMPORTANT)
        Return **JSON only**, with exactly this shape and nothing else:
        {{
        "chapters": [
            "Family First",
            "Celebrating Love",
            "Simple Pleasures"
        ]
        }}
        """,
                "format": "json",
            })

        followup_text = followup_res.text
        st.markdown("### 🗂️ Suggested Chapter Themes")
        # Show raw once (useful during debugging)
        if advanced_mode: st.code(followup_text)

        # Parse strictly (JSON-first, with robust fallbacks)
        chapters = parse_chapters_strict(followup_text)

        if advanced_mode: st.write("**Parsed chapters:**", chapters)
        if not chapters:
            st.warning("We couldn't organize these memories yet. Try uploading more posts.")
            st.stop()

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

            try:
                classification = classify_res.json()
                if not isinstance(classification, dict):
                    st.error("Invalid response format from AI classification service.")
                    st.stop()
            except ValueError as e:
                st.error(f"Failed to parse AI classification response: {e}")
                st.stop()

            # 🔒 Clean once up-front
            classification = _scrub_classification(classification)
            classification = _dedupe_classification_global(classification, chapters)

            # Validate before storing
            if "error" in classification:
                st.error("GPT classification failed.")
                if advanced_mode:
                    st.code(classification.get("raw_response", ""))
                st.stop()

            non_empty_chapters = [c for c in chapters if classification.get(c)]
            if not non_empty_chapters:
                st.warning("No chapters had matching posts.")
                st.stop()

            # ✅ Store and rerun
            st.session_state["classification"] = {c: classification[c] for c in chapters if classification.get(c)}
            st.session_state["chapters"] = [c for c in chapters if classification.get(c)]
            st.rerun()


else:
    classification = st.session_state["classification"]
    # ---- DIAG 1: scan classification for bad image values ----
    def _bad_img(u):
        # anything that is not a non-empty string URL/blob-path
        if not isinstance(u, str):
            return True
        s = u.strip()
        if not s or s.lower() in {"none","null","undefined","download failed"}:
            return True
        if s.isdigit():
            return True
        # allow http(s) or blob-ish paths with a slash
        return not (s.startswith("http") or ("/" in s))

    bad = []
    for chap, plist in classification.items():
        for pi, post in enumerate(plist):
            imgs = post.get("images") or []
            for ii, u in enumerate(imgs):
                if _bad_img(u):
                    bad.append({
                        "chapter": chap,
                        "post_index": pi,
                        "img_index": ii,
                        "value_repr": repr(u),
                        "value_type": type(u).__name__,
                    })

    st.sidebar.write(f"🔎 Bad image values: {len(bad)}")
    if bad:
        import json
        st.sidebar.code(json.dumps(bad[:8], indent=2))
        st.download_button("Download bad-items.json",
                        data=json.dumps(bad, indent=2),
                        file_name="bad-items.json",
                        mime="application/json")

    chapters = st.session_state["chapters"]
    st.success("🎉 Scrapbook complete!") 

# ── RENDER SCRAPBOOK IF ALREADY GENERATED ─────────────────────────────
if "classification" in st.session_state:
    chapters = st.session_state["chapters"]
    classification = _scrub_classification(st.session_state["classification"])
    classification = _dedupe_classification_global(classification, st.session_state["chapters"])
    st.session_state["classification"] = classification
    # ---- DIAG 1: scan classification for bad image values ----
    def _bad_img(u):
        # anything that is not a non-empty string URL/blob-path
        if not isinstance(u, str):
            return True
        s = u.strip()
        if not s or s.lower() in {"none","null","undefined","download failed"}:
            return True
        if s.isdigit():
            return True
        # allow http(s) or blob-ish paths with a slash
        return not (s.startswith("http") or ("/" in s))

    bad = []
    for chap, plist in classification.items():
        for pi, post in enumerate(plist):
            imgs = post.get("images") or []
            for ii, u in enumerate(imgs):
                if _bad_img(u):
                    bad.append({
                        "chapter": chap,
                        "post_index": pi,
                        "img_index": ii,
                        "value_repr": repr(u),
                        "value_type": type(u).__name__,
                    })

    if bad:
        import json
        st.sidebar.code(json.dumps(bad[:8], indent=2))
        st.download_button("Download bad-items.json",
                        data=json.dumps(bad, indent=2),
                        file_name="bad-items.json",
                        mime="application/json")

    st.balloons()
    st.markdown("""
    <div class="card" style="text-align:center">
    <div class="section-title" style="margin-top:0">🎉 Your scrapbook is ready</div>
    <p class="muted">Replace any photo, undo, and download the scrapbook as a PDF.</p>
    </div>
    """, unsafe_allow_html=True)
        # Coverage meter (unique images used / available)
    def _coverage(posts_all, classification):
        all_keys, used = set(), set()
        for p in posts_all:
            for u in (p.get("images") or p.get("normalized_images") or []):
                if _is_displayable_image_ref(u):
                    all_keys.add(_image_key(u))
        for plist in classification.values():
            for p in plist:
                for u in p.get("images", []):
                    if _is_displayable_image_ref(u):
                        used.add(_image_key(u))
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
            template = st.session_state.get("pdf_template", "natural")
            classification = st.session_state["classification"]
            chapters = st.session_state["chapters"]
            classification = _scrub_classification(st.session_state["classification"])
            chapters = st.session_state["chapters"]
            ck = _scrapbook_ck(classification, chapters, blob_folder, template)

            st.session_state["pdf_bytes"] = _build_pdf_cached(
                classification, chapters, blob_folder, show_empty_chapters,
                st.session_state.get("profile_summary",""),
                template,
                ck
            )
            st.session_state["pdf_dirty"] = False
            # Sanity check so we don't silently end up with no button
            if not st.session_state["pdf_bytes"]:
                st.error("PDF builder returned empty bytes. Check that app-assets/* are readable and chapter items have images.")


    # ✅ Then (dedented!) place ONE download button after the loop
    # ---- 🎨 Design picker (3 choices) ----
    st.markdown("<div class='section-title'>🎨 Choose your download design</div>", unsafe_allow_html=True)



    TPL_PREV_1 = _preview_asset("preview_polaroid.png")
    TPL_PREV_2 = _preview_asset("preview_travel.png")
    TPL_PREV_3 = _preview_asset("preview_natural.png")


    #st.session_state.setdefault("pdf_template", "natural")
    st.session_state.setdefault("pdf_template", None)   # no default until user picks
    st.session_state.setdefault("want_pdf", False)      # build gate
    


    cc1, cc2, cc3 = st.columns(3)


    with cc1:
        st.image(TPL_PREV_1, use_container_width=True)     # <-- no caption=""
        if st.button("Use Classic Polaroid", key="tpl_polaroid"):
            st.session_state["pdf_template"] = "polaroid"
            st.session_state["want_pdf"] = True
            st.session_state["_last_built_ck"] = None
            st.rerun()

    with cc2:
        st.image(TPL_PREV_2, use_container_width=True)     # <-- no caption=""
        if st.button("Use Travel Scrapbook", key="tpl_travel"):
            st.session_state["pdf_template"] = "travel"
            st.session_state["want_pdf"] = True
            st.session_state["_last_built_ck"] = None
            st.rerun()

    with cc3:
        st.image(TPL_PREV_3, use_container_width=True)     # <-- no caption=""
        if st.button("Use Natural Moodboard", key="tpl_natural"):
            st.session_state["pdf_template"] = "natural"
            st.session_state["want_pdf"] = True
            st.session_state["_last_built_ck"] = None
            st.rerun()


    # --- Build PDF only after a template is selected ---
    template = st.session_state.get("pdf_template")
    ready_now = False

    if template:
        ck = _scrapbook_ck(classification, chapters, blob_folder, template)
        needs_build = (
            st.session_state.get("_last_built_ck") != ck
            or st.session_state.get("pdf_bytes") is None
        )

        if st.session_state.get("want_pdf") and needs_build:
            with st.spinner("Rebuilding your PDF…"):
                st.session_state["pdf_bytes"] = _build_pdf_cached(
                    classification,
                    chapters,
                    blob_folder,
                    show_empty_chapters,
                    st.session_state.get("profile_summary",""),
                    template,
                    ck
                )
                st.session_state["_last_built_ck"] = ck

        # up-to-date?
        ready_now = (
            st.session_state.get("pdf_bytes") is not None
            and st.session_state.get("_last_built_ck") == ck
        )

        if template and st.session_state.get("want_pdf"):
            st.caption("Rebuilding your PDF…")
        else:
            st.caption("Pick a design above to generate your PDF.")
    st.markdown('</div>', unsafe_allow_html=True)







