# ======================
# FILE: Projects.py
# ======================
import streamlit as st
import os
import json
from datetime import datetime, timezone
from pandas import DataFrame
from azure.storage.blob import BlobServiceClient
import requests
import hashlib
from pathlib import Path
from urllib.parse import quote_plus, urlencode
import shutil, zipfile, concurrent.futures, random
import time
from io import BytesIO
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from datetime import timedelta
import stripe

DEBUG = str(st.secrets.get("DEBUG", "false")).strip().lower() == "true"
SHOW_MEMORIES_BUTTON = str(
    st.secrets.get("SHOW_MEMORIES_BUTTON", os.getenv("SHOW_MEMORIES_BUTTON", "true"))
).strip().lower() in ("1", "true", "yes", "on")
st.set_page_config(
    page_title="My Projects | Facebook Scrapbook",
    layout="wide",
    page_icon="📚",
    initial_sidebar_state="collapsed"
)
try:
    p = Path("cache") / "session_cache.json"
    if p.exists():
        p.unlink()
except Exception:
    pass

def qp_get(name, default=None):
    try:
        return st.query_params.get(name)  # >= 1.31
    except Exception:
        if DEBUG:
            st.sidebar.info("Using deprecated query_params API for compatibility")
        return st.experimental_get_query_params().get(name, [default])[0]

def qp_set(**kwargs):
    try:
        st.query_params.update(kwargs)  # >= 1.31
    except Exception:
        if DEBUG:
            st.sidebar.info("Using deprecated query_params API for compatibility")
        st.experimental_set_query_params(**kwargs)

# ---------------------------
# Utilities / session restore
# ---------------------------
def safe_token_hash(token: str) -> str:
    return hashlib.md5(token.encode()).hexdigest()

def ensure_cache_dir():
    """Centralized cache directory initialization to avoid race conditions."""
    cache_dir = Path("cache")
    cache_dir.mkdir(exist_ok=True)
    return cache_dir

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
        st.session_state["new_project_added"] = data.get("new_project_added")
    except Exception:
        pass


restore_session()

# creator collapsed by default + running flag
st.session_state.setdefault("show_creator", False)
st.session_state.setdefault("backup_running", False)
# Persistent banner while a backup is running
if st.session_state.get("backup_running"):
    st.info(
        "⏳ We’re creating your backup now. This process can take a few minutes depending on your Facebook data size. "
        "Please keep this tab open and be patient."
    )
for key in ["fb_token", "fb_id", "fb_name"]:
    if key not in st.session_state:
        st.session_state[key] = None

@st.cache_resource
def get_blob_service_client():
    AZ_CONN = st.secrets.get("AZURE_CONNECTION_STRING") or os.getenv("AZURE_CONNECTION_STRING")
    if AZ_CONN:
        return BlobServiceClient.from_connection_string(AZ_CONN)
    return None

if get_blob_service_client() is None:
    st.error("Missing AZURE_CONNECTION_STRING in Secrets. Set it in Streamlit Cloud → Settings → Secrets.")
    st.stop()

blob_service_client = get_blob_service_client()
container_client = blob_service_client.get_container_client("backup")

# ---------------------------
# Stripe Payment Configuration
# ---------------------------
def _get_secret(name: str, default: str | None = None) -> str | None:
    try:
        return st.secrets[name]
    except Exception:
        return os.environ.get(name, default)

# Stripe config
STRIPE_SECRET_KEY = _get_secret("STRIPE_SECRET_KEY")
RAW_PRICE_OR_PRODUCT_ID = _get_secret("STRIPE_PRICE_ID", "price_1234567890placeholder")
SUCCESS_URL = _get_secret("STRIPE_SUCCESS_URL", "http://localhost:8501/Projects")
CANCEL_URL = _get_secret("STRIPE_CANCEL_URL", "http://localhost:8501/Projects")

BILLING_READY = bool(STRIPE_SECRET_KEY)
if BILLING_READY:
    stripe.api_key = STRIPE_SECRET_KEY

def _resolve_price_id(price_or_prod: str | None) -> str | None:
    """Return a Price ID for either a Price or Product input; None if not resolvable."""
    if not price_or_prod:
        return None
    if price_or_prod.startswith("price_"):
        return price_or_prod
    if price_or_prod.startswith("prod_"):
        try:
            prod = stripe.Product.retrieve(price_or_prod)
            default_price = prod.get("default_price")
            if default_price:
                return default_price
            prices = stripe.Price.list(product=price_or_prod, active=True, limit=1)
            if prices.data:
                return prices.data[0].id
            st.error("This Product has no active Prices in this Stripe mode (test/live).")
            return None
        except Exception as e:
            st.error(f"Could not resolve a Price for Product '{price_or_prod}': {e}")
            return None
    st.error("STRIPE_PRICE_ID must be a 'price_...' or 'prod_...' value.")
    return None

RESOLVED_PRICE_ID = _resolve_price_id(RAW_PRICE_OR_PRODUCT_ID)

# ---------------------------------------
# Fb profile (ensures name/id in session)
# ---------------------------------------
if "fb_token" in st.session_state and st.session_state["fb_token"]:
    try:
        response = requests.get(
            f"https://graph.facebook.com/me?fields=id,name,email&access_token={st.session_state['fb_token']}",
            timeout=10
        )
        response.raise_for_status()
        profile = response.json()
        st.session_state["fb_id"] = str(profile.get("id")).strip()
        st.session_state["fb_name"] = profile.get("name")
        # NEW: persist token + minimal profile so refresh can restore (per-user file only)
        cache_dir = ensure_cache_dir()
        token = st.session_state["fb_token"]
        token_hash = hashlib.md5(token.encode()).hexdigest()
        payload = {
            "fb_token": token,
            "latest_backup": {
                "user_id": st.session_state.get("fb_id", ""),
                "Name": st.session_state.get("fb_name", "")
            }
        }
        (cache_dir / f"backup_cache_{token_hash}.json").write_text(json.dumps(payload), encoding="utf-8")
        qp_set(cache=token_hash)

    except Exception as e:
        if DEBUG:
            st.error(f"Failed to refresh Facebook user info: {e}")
            st.code(f"Debug info: Token length={len(st.session_state.get('fb_token', ''))}")
        else:
            st.error(f"Failed to refresh Facebook user info: {e}")
        st.stop()

missing_keys = [k for k in ["fb_id", "fb_name", "fb_token"] if not st.session_state.get(k)]
if missing_keys:
    st.warning(f"⚠️ Missing session keys: {missing_keys}")
    st.stop()

# ---------------------------
# Stripe Payment Return Handler
# ---------------------------
def handle_stripe_return():
    """Handle Stripe payment return in Projects.py instead of separate success page."""
    qp = st.query_params
    session_id = qp.get("session_id")
    if isinstance(session_id, list):
        session_id = session_id[0]

    if BILLING_READY and session_id:
        try:
            sess = stripe.checkout.Session.retrieve(session_id)
        except stripe.error.StripeError as e:
            st.error(f"Stripe API error: {e}")
            return False
        except Exception as e:
            st.error(f"Unexpected error retrieving payment session: {e}")
            return False
        
        if (sess.get("payment_status") or "").lower() == "paid":
            md = sess.get("metadata") or {}
            blob_path = md.get("blob") or qp.get("blob") or ""
            backup_prefix = md.get("backup_prefix") or (_backup_prefix_from_blob_path(blob_path) if blob_path else "")

            if not backup_prefix:
                st.error("Paid, but couldn't resolve the backup prefix. Contact support.")
                return False
            else:
                _write_entitlements(backup_prefix, sess)
                st.success("✅ Payment confirmed — Memories unlocked for this backup!")
                st.session_state["selected_backup"] = backup_prefix
                return True
        else:
            payment_status = sess.get("payment_status", "unknown")
            if payment_status == "unpaid":
                st.warning("Payment was not completed. Please try again or contact support if you were charged.")
            elif payment_status == "no_payment_required":
                st.info("No payment was required for this session.")
            else:
                st.warning(f"Payment status is '{payment_status}'. Please contact support if you were charged.")
            return False
    return False

def _backup_prefix_from_blob_path(blob_path: str) -> str:
    """Extract backup prefix from blob path."""
    return str(blob_path).rsplit("/", 1)[0].strip("/")

def _write_entitlements(prefix: str, session: dict) -> None:
    """Write entitlements.json and marker files for paid backup."""
    ent = {
        "memories": True,
        "download": True,
        "paid": True,
        "paid_at": datetime.now(timezone.utc).isoformat(),
        "checkout_id": session.get("id"),
        "amount": (session.get("amount_total") or 0) / 100.0,
        "currency": session.get("currency"),
        "fb_id": (session.get("metadata") or {}).get("fb_id"),
        "fb_name": (session.get("metadata") or {}).get("fb_name"),
    }
    bc = container_client.get_blob_client(f"{prefix}/entitlements.json")
    bc.upload_blob(json.dumps(ent, ensure_ascii=False).encode("utf-8"), overwrite=True)
    
    # markers (zero-byte files are fine)
    container_client.get_blob_client(f"{prefix}/.paid.memories").upload_blob(b"", overwrite=True)
    container_client.get_blob_client(f"{prefix}/.paid.download").upload_blob(b"", overwrite=True)

fb_id = st.session_state["fb_id"]
fb_name = st.session_state.get("fb_name")
fb_token = st.session_state["fb_token"]

# -----------------
# CSS / Header
# -----------------
st.markdown("""
<style>
:root{
  --navy-900:#0F253D;
  --navy-800:#143150;
  --navy-700:#1E3A5F;
  --navy-500:#2F5A83;
  --gold:#F6C35D;
  --text:#F3F6FA;
  --muted:#B9C6D6;
  --card:#112A45;
  --line:rgba(255,255,255,.14);
}
html, body, .stApp{
  background: linear-gradient(180deg, var(--navy-900) 0%, var(--navy-800) 55%, var(--navy-700) 100%);
  color: var(--text);
  font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3{
  color: var(--text) !important; letter-spacing:.25px;
}
.stButton>button, .stDownloadButton button{
  background: var(--gold) !important; color:#111 !important; border:none !important;
  border-radius:10px !important; padding:10px 16px !important; font-weight:800 !important;
  box-shadow:0 4px 14px rgba(246,195,93,.22) !important;
  transition: transform .15s ease, filter .15s ease, box-shadow .15s ease !important;
}
.stButton>button:hover, .stDownloadButton button:hover{ transform: translateY(-1px); filter: brightness(.97); box-shadow:0 6px 18px rgba(246,195,93,.28) !important; }
/* Make st.link_button look like our primary buttons */
.stLinkButton > a{
  background: var(--gold) !important;
  color: #111 !important;
  border: none !important;
  border-radius: 10px !important;
  padding: 10px 16px !important;
  font-weight: 800 !important;
  box-shadow: 0 4px 14px rgba(246,195,93,.22) !important;
  transition: transform .15s ease, filter .15s ease, box-shadow .15s ease !important;
  width: 100% !important;
  display: inline-flex; justify-content: center; align-items: center;
  text-decoration: none !important;
}
.stLinkButton > a:hover{
  transform: translateY(-1px);
  filter: brightness(.97);
  box-shadow: 0 6px 18px rgba(246,195,93,.28) !important;
}
.card{ background:var(--card); border:1px solid var(--line); border-radius:12px; box-shadow:0 10px 24px rgba(0,0,0,.18); padding:24px; margin-bottom:24px; transition:.2s; }
.card:hover{ transform: translateY(-2px); }
.header{ display:flex; justify-content:space-between; align-items:center; margin-bottom:32px; padding-bottom:16px; border-bottom:1px solid var(--line); }
.header p{ color: var(--muted) !important; }
.user-badge{ display:flex; align-items:center; gap:12px; background: rgba(255,255,255,.06); padding:10px 16px; border-radius: 50px; box-shadow: 0 2px 8px rgba(0,0,0,.12); }
.avatar{ width:40px; height:40px; border-radius:50%; background: var(--gold); display:flex; align-items:center; justify-content:center; color: var(--navy-900); font-weight: 900; }
.empty-state{ text-align:center; padding: 40px 20px; background: rgba(255,255,255,.06); border-radius: 12px; border: 1px dashed var(--line); color: var(--muted); }
.empty-state-icon{ font-size:48px; margin-bottom:16px; color: var(--gold); }
.stProgress [role="progressbar"] > div{ background: var(--gold) !important; }
input, textarea, select{ background: rgba(255,255,255,.06) !important; border:1px solid var(--line) !important; color: var(--text) !important; border-radius:10px !important; }

/* Status panel / checklist */
div[data-testid="stStatus"]{
  background: rgba(255,255,255,.06) !important;
  border: 1px solid var(--line) !important;
  border-radius: 12px !important;
  padding: 16px 18px !important;
  margin: 12px 0 8px 0 !important;
}
div[data-testid="stStatus"] .stMarkdown p{ margin: 6px 0 !important; }
.progress-steps{ color: var(--muted); line-height: 1.45; font-size: 0.95rem; }

/* Danger (delete) button style */
button[data-testid="baseButton-secondary"].danger {
  background: transparent !important;
  border: 1px solid rgba(255,99,99,.35) !important;
  color: #ff7b7b !important;
}
button[data-testid="baseButton-secondary"].danger:hover{
  border-color:#ff8e8e !important; color:#ff9d9d !important;
}
</style>
""", unsafe_allow_html=True)

# Handle Stripe return after session state is initialized
if handle_stripe_return():
    st.rerun()

st.markdown(f"""
<div class="header">
  <div>
    <h1 style="margin:0;">Backup Manager</h1>
    <p style="margin:4px 0 0 0;">Manage your Facebook backups</p>
  </div>
  <div class="user-badge">
    <div class="avatar">{(fb_name or 'U')[0].upper()}</div>
    <div>
      <div style="font-weight:600;">{fb_name}</div>
      <div style="font-size:.8em; color:#B9C6D6;">Account active</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------
# FbFullProfile helpers
# ---------------------------------------------
CONTAINER = "backup"
BACKUP_DIR = Path("facebook_data"); BACKUP_DIR.mkdir(exist_ok=True)
IMG_DIR = BACKUP_DIR / "images"; IMG_DIR.mkdir(exist_ok=True)
MAX_FB_PAGES = int(st.secrets.get("FB_MAX_PAGES", os.getenv("FB_MAX_PAGES", "1000")))
DEFAULT_PAGE_SIZE = int(st.secrets.get("FB_PAGE_SIZE", os.getenv("FB_PAGE_SIZE", "100")))
def fetch_data(endpoint, token, since=None, until=None, fields=None):
    if endpoint is None: return {}
    # add limit param
    url = f"https://graph.facebook.com/me/{endpoint}?access_token={token}&limit={DEFAULT_PAGE_SIZE}"
    if fields: url += f"&fields={fields}"
    if since:  url += f"&since={since}"
    if until:  url += f"&until={until}"

    data, pages = [], 0
    # remove hard 20-page cap; use high configurable max instead
    while url and pages < MAX_FB_PAGES:
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            res = response.json()
            if "error" in res:
                error_msg = res.get("error", {}).get("message", "Unknown Facebook API error")
                st.warning(f"Skipping {endpoint}: {error_msg}")
                break
            data.extend(res.get("data", []))
            url = res.get("paging", {}).get("next")
            pages += 1
        except requests.exceptions.RequestException as e:
            st.warning(f"Network error on {endpoint}: {e}")
            break
        except Exception as e:
            st.warning(f"Unexpected error on {endpoint}: {e}")
            break

    # optional heads-up if you actually hit the max and still had a next page
    if url and pages >= MAX_FB_PAGES:
        st.warning(f"Stopped at FB_MAX_PAGES={MAX_FB_PAGES}. Increase FB_MAX_PAGES if you need more.")

    return data

def save_json(obj, name):
    fp = BACKUP_DIR / f"{name}.json"
    fp.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    return fp

def upload_folder(BACKUP_DIR, blob_prefix):
    container = blob_service_client.get_container_client(CONTAINER)
    try:
        container.create_container()
    except Exception:
        pass

    # Collect files first
    files = []
    for root, _, filenames in os.walk(BACKUP_DIR):
        for file in filenames:
            local_path = Path(root) / file
            relative_path = str(local_path.relative_to(BACKUP_DIR))
            blob_path = f"{blob_prefix}/{relative_path}".replace("\\", "/")
            files.append((local_path, blob_path))

    # Ensure posts+cap.json is uploaded LAST (this is what the worker should process)
    def _order(t):
        _, blob_path = t
        return 1 if blob_path.endswith("posts+cap.json") else 0
    files.sort(key=_order)

    # Upload
    for local_path, blob_path in files:
        with open(local_path, "rb") as f:
            container.get_blob_client(blob_path).upload_blob(f, overwrite=True)

def download_image(url, name_id):
    ext = url.split(".")[-1].split("?")[0]
    if len(ext) > 5 or "/" in ext: ext = "jpg"
    fname = f"{name_id}.{ext}"
    local_path = IMG_DIR / fname
    r = requests.get(url, stream=True, timeout=10)
    if r.status_code == 200:
        with open(local_path, 'wb') as f: shutil.copyfileobj(r.raw, f)
    else:
        raise Exception(f"Image download failed: {r.status_code}")
    return local_path

def generate_blob_url(folder_prefix: str, image_name: str) -> str:
    account_name = blob_service_client.account_name
    return f"https://{account_name}.blob.core.windows.net/{CONTAINER}/{folder_prefix}/images/{quote_plus(image_name)}"

def dense_caption(img_path):
    # Validate required secrets
    vision_endpoint = st.secrets.get("AZURE_VISION_ENDPOINT")
    vision_key = st.secrets.get("AZURE_VISION_KEY")
    
    if not vision_endpoint or not vision_key:
        return "No caption (Azure Vision API not configured)"
    
    endpoint = vision_endpoint.rstrip("/") + "/vision/v3.2/analyze?visualFeatures=Description,Tags,Objects"
    headers = {"Ocp-Apim-Subscription-Key": vision_key, "Content-Type": "application/octet-stream"}
    try:
        with open(img_path, "rb") as f: data = f.read()
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
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
        # 1) summary.json at the root (if it exists)
        summary_fp = BACKUP_DIR / "summary.json"
        if summary_fp.exists():
            zipf.write(summary_fp, arcname="summary.json")

        # 2) everything under images/ (preserve folder structure)
        if IMG_DIR.exists():
            for folder, _, files in os.walk(IMG_DIR):
                for file in files:
                    fp = Path(folder) / file
                    # arcname relative to BACKUP_DIR ensures "images/..." in the zip
                    arcname = os.path.relpath(fp, BACKUP_DIR)
                    zipf.write(fp, arcname)

    return zip_path

def extract_image_urls(post):
    urls = set()
    def add(url):
        if url and isinstance(url, str) and url.startswith("http"):
            urls.add(url)
    add(post.get("full_picture"))
    add(post.get("picture"))
    att = (post.get("attachments") or {}).get("data", [])
    for a in att:
        media = (a.get("media") or {}).get("image", {})
        add(media.get("src"))
        subs = (a.get("subattachments") or {}).get("data", [])
        for s in subs:
            m = (s.get("media") or {}).get("image", {})
            add(m.get("src"))
    return list(urls)

def _render_steps(ph, steps):
    lines = []
    for s in steps:
        icon = "✅" if s["done"] else ("⏳" if s.get("active") else "•")
        lines.append(f"{icon} {s['label']}")
    ph.markdown("<div class='progress-steps'>" + "<br/>".join(lines) + "</div>", unsafe_allow_html=True)

# ---------- Backup prefix helpers ----------
def list_user_backup_prefixes(user_id: str):
    prefixes = {}
    for blob in container_client.list_blobs(name_starts_with=f"{user_id}/"):
        parts = blob.name.split("/")
        if len(parts) < 3:
            continue
        uid, folder, filename = parts[0], parts[1], "/".join(parts[2:])
        if uid != user_id or folder.startswith("projects/"):
            continue
        pfx = f"{uid}/{folder}"
        rec = prefixes.setdefault(pfx, {"has_summary": False, "has_posts": False, "ts": None})
        if filename == "summary.json":
            try:
                raw = container_client.get_blob_client(blob.name).download_blob().readall().decode("utf-8")
                summary = json.loads(raw)
                ts = summary.get("timestamp")
                if ts:
                    rec["ts"] = datetime.fromisoformat(ts)
                else:
                    rec["ts"] = getattr(blob, "last_modified", datetime.now(timezone.utc))
            except Exception:
                rec["ts"] = getattr(blob, "last_modified", datetime.now(timezone.utc))
            rec["has_summary"] = True
        elif filename == "posts+cap.json":
            rec["has_posts"] = True
    valid = []
    for pfx, info in prefixes.items():
        if info["has_summary"] and info["has_posts"]:
            valid.append((pfx, info["ts"] or datetime.now(timezone.utc)))
    valid.sort(key=lambda x: x[1], reverse=True)
    return [p for p, _ in valid]

def _delete_prefix_silent(prefix: str):
    try:
        to_delete = list(container_client.list_blobs(name_starts_with=f"{prefix}/"))
        for b in to_delete:
            try:
                container_client.get_blob_client(b.name).delete_blob(delete_snapshots="include")
            except Exception:
                if DEBUG:
                    st.write(f"Silent delete error for {b.name}")
    except Exception as e:
        if DEBUG:
            st.write(f"Silent delete failed: {e}")

def enforce_single_backup(user_id: str):
    prefixes = list_user_backup_prefixes(user_id)
    if len(prefixes) <= 1:
        return
    for pfx in prefixes[1:]:
        _delete_prefix_silent(pfx)

def delete_backup_prefix(prefix: str):
    try:
        to_delete = list(container_client.list_blobs(name_starts_with=f"{prefix}/"))
        for b in to_delete:
            try:
                container_client.get_blob_client(b.name).delete_blob(delete_snapshots="include")
            except Exception as e:
                if DEBUG:
                    st.write(f"Delete error for {b.name}: {e}")

        lb = st.session_state.get("latest_backup")
        if lb and str(lb.get("Folder", "")).lower().rstrip("/") == prefix.lower().rstrip("/"):
            st.session_state.pop("latest_backup", None)
            st.session_state.pop("new_backup_done", None)

        cache_file = Path(f"cache/backup_cache_{hashlib.md5(st.session_state['fb_token'].encode()).hexdigest()}.json")
        if cache_file.exists():
            try:
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump({"fb_token": st.session_state["fb_token"]}, f)
            except Exception:
                pass

        st.toast(f"🗑️ Deleted {prefix}", icon="🗑️")
    except Exception as e:
        st.error(f"Delete failed: {e}")

# ---------- Payment / entitlement helpers ----------
def _memories_is_paid(prefix: str) -> bool:
    """
    Returns True if this backup prefix is paid for Memories.
    Looks for:
      - entitlements.json  (preferred)
      - project_meta.json  (legacy)
      - tiny marker files: .paid.memories / .paid / paid.flag  (fallback)
    """
    try:
        # Preferred: entitlements.json
        bc = container_client.get_blob_client(f"{prefix}/entitlements.json")
        if bc.exists():
            try:
                ent = json.loads(bc.download_blob().readall().decode("utf-8"))
            except Exception:
                ent = {}
            if bool(
                ent.get("memories") or
                ent.get("download") or
                ent.get("is_paid") or
                ent.get("paid")
            ):
                return True

        # Legacy JSON
        for name in ("project_meta.json", "project_meta.json.json"):
            bc = container_client.get_blob_client(f"{prefix}/{name}")
            if bc.exists():
                try:
                    meta = json.loads(bc.download_blob().readall().decode("utf-8"))
                except Exception:
                    meta = {}
                if bool(
                    meta.get("is_paid") or
                    meta.get("paid") or
                    (meta.get("entitlements", {}) or {}).get("memories")
                ):
                    return True

        # Fallback marker files (zero-byte files are fine)
        for name in (".paid.memories", ".paid", "paid.flag"):
            if container_client.get_blob_client(f"{prefix}/{name}").exists():
                return True
    except Exception:
        pass
    return False

def _download_is_paid(prefix: str) -> bool:
    """
    True if user is entitled to DOWNLOAD this backup.
    Looks for:
      - entitlements.json with download/is_paid/paid flags
      - marker files: .paid.download / .paid.memories / .paid / paid.flag
    """
    try:
        bc = container_client.get_blob_client(f"{prefix}/entitlements.json")
        if bc.exists():
            try:
                ent = json.loads(bc.download_blob().readall().decode("utf-8"))
            except Exception:
                ent = {}
            if bool(ent.get("download") or ent.get("is_paid") or ent.get("paid")):
                return True

        for name in (".paid.download", ".paid.memories", ".paid", "paid.flag"):
            if container_client.get_blob_client(f"{prefix}/{name}").exists():
                return True
    except Exception:
        pass
    return False


def _sas_url_for_blob(blob_path: str, minutes: int = 20) -> str | None:
    """
    Build a time-limited (read-only) SAS URL to the given blob.
    Falls back to None if we can't access the account key.
    """
    try:
        conn = st.secrets.get("AZURE_CONNECTION_STRING") or os.getenv("AZURE_CONNECTION_STRING")
        parts = dict(p.split("=", 1) for p in conn.split(";") if "=" in p)
        account_name = parts.get("AccountName") or blob_service_client.account_name
        account_key = parts.get("AccountKey")
        if not account_key:
            return None  # connection string doesn't carry a key (e.g., SAS-based)
        sas = generate_blob_sas(
            account_name=account_name,
            container_name=CONTAINER,
            blob_name=blob_path,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(minutes=minutes),
        )
        return f"https://{account_name}.blob.core.windows.net/{CONTAINER}/{blob_path}?{sas}"
    except Exception:
        return None


# -----------------------
# Load existing backups (show only the most recent) + enforce single
# -----------------------
backups = []
try:
    user_id = str(st.session_state["fb_id"]).strip()
    enforce_single_backup(user_id)
    prefixes = list_user_backup_prefixes(user_id)
    if prefixes:
        pfx = prefixes[0]
        summary_blob = container_client.get_blob_client(f"{pfx}/summary.json")
        posts_blob = container_client.get_blob_client(f"{pfx}/posts+cap.json")
        if summary_blob.exists() and posts_blob.exists():
            try:
                summary = json.loads(summary_blob.download_blob().readall().decode("utf-8"))
                created_dt = datetime.fromisoformat(summary.get("timestamp", "2000-01-01"))
                backups.append({
                    "id": pfx,
                    "name": summary.get("user") or pfx.split("/", 1)[1].replace("_", " "),
                    "date": created_dt.strftime("%b %d, %Y"),
                    "posts": summary.get("posts", 0),
                    "status": "Completed",
                    "raw_date": created_dt
                })
            except Exception:
                pass
    has_backup = len(backups) == 1
except Exception as e:
    st.error(f"Azure connection error: {e}")
    has_backup = False

# If we just finished a backup, inject it (defensive)
if st.session_state.pop("new_backup_done", False):
    latest = st.session_state.pop("latest_backup", None)
    if latest and str(latest.get("user_id")).strip() == str(fb_id).strip():
        folder = latest.get("Folder").rstrip("/").lower()
        summary_blob = container_client.get_blob_client(f"{folder}/summary.json")
        posts_blob = container_client.get_blob_client(f"{folder}/posts+cap.json")
        if summary_blob.exists() and posts_blob.exists():
            if not any(b["id"].rstrip("/").lower() == folder for b in backups):
                backups.insert(0, {
                    "id": folder,
                    "name": latest.get("Name", "Unnamed Backup"),
                    "date": latest.get("Created On", "Unknown"),
                    "posts": latest.get("# Posts", 0),
                    "status": "Completed",
                    "raw_date": datetime.now()
                })
        has_backup = True

# --------------------------------------------
# Top section
# --------------------------------------------
if not st.session_state["show_creator"]:
    st.markdown(
        "<h3 style='margin-top:0; margin-bottom:8px;'>📦 My Backups</h3>"
        "<p style='color:var(--muted); margin-top:-4px;'>Create or download your Facebook backups.</p>",
        unsafe_allow_html=True,
    )
    left_btn_col, _ = st.columns([1, 3])
    with left_btn_col:
        if has_backup:
            st.info("You already have one backup. Delete it below to create a new one.")
        else:
            if st.button("＋ New Backup", type="primary", use_container_width=True, key="new_backup_btn"):
                st.session_state["show_creator"] = True
                st.rerun()   # CHANGED
else:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("📦 Create Facebook Backup")
    # Clear upfront warning about duration
    st.info(
        "Heads up: Creating your backup can take **several minutes**. "
        "Please keep this tab open; you’ll see live progress below."
    )

    st.markdown("""<div class="instructions">
    <strong>How to create your backup:</strong>
    <ol><li><strong>Click "Start My Backup"</strong></li></ol>
    <em>Large backups may take several minutes.</em></div>""", unsafe_allow_html=True)

    if has_backup:
        st.warning("You already have an active backup. Delete it first.")
    else:
        token = st.session_state["fb_token"]
        try:
            response = requests.get(f"https://graph.facebook.com/me?fields=id,name,email&access_token={token}", timeout=10)
            response.raise_for_status()
            fb_profile = response.json()
            fb_name_slug = (fb_profile.get("name", "user") or "user").replace(" ", "_")
            fb_id_val = fb_profile.get("id")
        except requests.exceptions.RequestException as e:
            if DEBUG:
                st.error(f"Failed to fetch Facebook profile: {e}")
                st.code(f"Debug info: Token length={len(token)}")
            else:
                st.error(f"Failed to fetch Facebook profile: {e}")
            st.stop()
        except Exception as e:
            if DEBUG:
                st.error(f"Unexpected error fetching profile: {e}")
                st.code(f"Debug info: Token length={len(token)}")
            else:
                st.error(f"Unexpected error fetching profile: {e}")
            st.stop()
        folder_prefix = f"{fb_id_val}/{fb_name_slug}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        start_disabled = st.session_state.get("backup_running", False)

        if st.button("⬇️ Start My Backup", disabled=start_disabled):
            st.session_state["backup_running"] = True

            # Immediate, explicit feedback about duration
            st.toast("Starting your backup… this can take several minutes. Please keep this tab open.", icon="⏳")
            st.caption("Tip: Don’t close this browser tab while we work. You’ll see each step complete below.")

            overall = st.progress(0, text="Preparing to start… (this can take a few minutes)")

            with st.status("Working on your backup…", state="running", expanded=True) as status:
                steps = [
                    {"label": "Fetched posts", "done": False},
                    {"label": "Processed posts & captions", "done": False},
                    {"label": "Files prepared", "done": False},
                    {"label": "Uploaded backup folder", "done": False},
                    {"label": "ZIP uploaded", "done": False},
                    {"label": "Cleanup complete", "done": False},
                ]
                step_ph = st.empty()
                _render_steps(step_ph, steps)

                steps[0]["active"] = True; _render_steps(step_ph, steps)
                posts = fetch_data("posts", token, fields="id,message,created_time,full_picture,attachments{media}")
                for post in posts:
                    post["images"] = extract_image_urls(post)
                save_json(posts, "posts")
                steps[0]["active"] = False; steps[0]["done"] = True; _render_steps(step_ph, steps)
                overall.progress(20, text=f"Fetched {len(posts)} posts")

                steps[1]["active"] = True; _render_steps(step_ph, steps)
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    futures = []
                    for post in posts:
                        # Safe array access: get first image if images array exists and is not empty
                        img_url = post.get("images")[0] if post.get("images") else None
                        if not img_url:
                            continue
                        try:
                            # Generate fallback ID if post doesn't have one
                            post_id = post.get("id", hashlib.md5(f"{post.get('message','')}{img_url}".encode()).hexdigest()[:12])
                            img_path = download_image(img_url, post_id)
                            futures.append((post, executor.submit(dense_caption, img_path)))
                            signed_url = generate_blob_url(folder_prefix, Path(img_path).name)
                            post["picture"] = signed_url
                            post.setdefault("images", [])
                            if signed_url not in post["images"]:
                                post["images"].insert(0, signed_url)
                        except Exception as e:
                            post["picture"] = "download failed"
                            post["context_caption"] = f"Image download failed: {e}"

                    total = max(1, len(futures))
                    done_count = 0
                    for post, fut in futures:
                        try:
                            post["context_caption"] = fut.result()
                        except Exception:
                            post["context_caption"] = "caption failed"
                        done_count += 1
                        pct = 20 + int(25 * (done_count / total))
                        overall.progress(pct, text=f"Processing images & captions… ({done_count}/{total})")

                steps[1]["active"] = False; steps[1]["done"] = True; _render_steps(step_ph, steps)
                overall.progress(45, text="Images & captions processed (this step can take a few minutes)")

                steps[2]["active"] = True; _render_steps(step_ph, steps)
                save_json(posts, "posts+cap")
                save_json({"comments": []}, "comments.json")
                save_json({"likes": []}, "likes.json")
                save_json({"videos": []}, "videos.json")
                save_json({"profile": {"name": fb_name_slug, "id": fb_id_val}}, "profile.json")
                summary = {"user": fb_name_slug, "user_id": fb_id_val, "timestamp": datetime.now(timezone.utc).isoformat(), "posts": len(posts)}
                save_json(summary, "summary")
                steps[2]["active"] = False; steps[2]["done"] = True; _render_steps(step_ph, steps)
                overall.progress(60, text="Files prepared")

                steps[3]["active"] = True; _render_steps(step_ph, steps)
                upload_folder(BACKUP_DIR, folder_prefix)
                # ── NEW: wait for worker's summary ─────────────────────────────
                results_prefix = "results"
                result_blob_name = f"{results_prefix}/{folder_prefix}/posts+cap.summary.json"
                cc = blob_service_client.get_container_client(CONTAINER)
                result_bc = cc.get_blob_client(result_blob_name)

                overall.progress(85, text="Waiting for AI summary from worker… this part may take a few minutes")

                wait_seconds = 60  # adjust if you like
                found = False
                for _ in range(wait_seconds):
                    try:
                        if result_bc.exists():
                            found = True
                            break
                    except Exception:
                        pass
                    time.sleep(1)

                worker_summary = None
                if found:
                    try:
                        worker_summary = json.loads(result_bc.download_blob().readall().decode("utf-8")).get("summary", "")
                        st.success("✅ AI summary ready!")
                        st.markdown(f"**Preview:**\n\n{worker_summary[:1200]}{'…' if len(worker_summary) > 1200 else ''}")
                    except Exception as e:
                        st.warning(f"Could not read worker result: {e}")
                else:
                    st.info("The background worker is still generating the summary. It will appear shortly in your results folder.")

                steps[3]["active"] = False; steps[3]["done"] = True; _render_steps(step_ph, steps)
                overall.progress(80, text="Uploaded backup folder")

                steps[4]["active"] = True; _render_steps(step_ph, steps)
                zip_path = zip_backup(f"{fb_name_slug}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")
                with open(zip_path, "rb") as f:
                    container = blob_service_client.get_container_client(CONTAINER)
                    container.get_blob_client(f"{folder_prefix}/{zip_path.name}").upload_blob(f, overwrite=True)
                steps[4]["active"] = False; steps[4]["done"] = True; _render_steps(step_ph, steps)
                overall.progress(90, text="ZIP uploaded")

                steps[5]["active"] = True; _render_steps(step_ph, steps)
                shutil.rmtree(BACKUP_DIR)
                BACKUP_DIR.mkdir(exist_ok=True); IMG_DIR.mkdir(exist_ok=True)
                steps[5]["active"] = False; steps[5]["done"] = True; _render_steps(step_ph, steps)
                overall.progress(95, text="Cleanup complete")

                cache_file = ensure_cache_dir() / f"backup_cache_{hashlib.md5(token.encode()).hexdigest()}.json"
                latest_backup = {
                    "Name": fb_name_slug,
                    "Created On": datetime.now().strftime("%b %d, %Y"),
                    "# Posts": len(posts),
                    "Folder": folder_prefix.rstrip("/"),
                    "user_id": fb_id_val
                }
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump({"fb_token": token, "latest_backup": latest_backup, "new_backup_done": True}, f, indent=2)

                overall.progress(100, text="Backup complete! 🎉")
                status.update(label="Backup complete! 🎉", state="complete")
                st.toast("✅ Backup complete! Your scrapbook is ready to preview.", icon="✅")

            st.session_state.update({
                "fb_token": token,
                "new_backup_done": True,
                "latest_backup": latest_backup,
                "show_creator": False,
                "backup_running": False,
            })
            st.rerun()   # CHANGED

    st.markdown('</div>', unsafe_allow_html=True)

# -----------------------
# Backups table
# -----------------------
if backups:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    hdr = st.columns([3, 1, 1, 1, 3])
    with hdr[0]: st.caption("Backup")
    with hdr[1]: st.caption("Posts")
    with hdr[2]: st.caption("Created")
    with hdr[3]: st.caption(" ")
    with hdr[4]: st.caption("Actions")
    st.divider()

    for backup in backups:
        cols = st.columns([3, 1, 1, 1.2, 3])
        with cols[0]:
            st.markdown(f"**{backup['name']}**")
            st.caption(f"{backup['id']}")
        with cols[1]:
            st.markdown(f"**{backup['posts']}**")
            st.caption("Posts")
        with cols[2]:
            st.markdown(f"**{backup['date']}**")
            st.caption("Created")

        # Immediate delete (one rerun only)
        with cols[3]:
            safe_id = backup["id"].replace("/", "__")
            if st.button("❌", key=f"del_{safe_id}", help="Delete this backup"):
                delete_backup_prefix(backup["id"])
                st.rerun()   # CHANGED

        with cols[4]:
            # Try to find a .zip under this backup prefix; fall back to the JSON if not found
            zip_blob_path, zip_name = None, None
            try:
                for b in container_client.list_blobs(name_starts_with=f"{backup['id']}/"):
                    if b.name.lower().endswith(".zip"):
                        zip_blob_path = b.name
                        zip_name = b.name.rsplit("/", 1)[-1]
                        break
            except Exception:
                pass

            # Fallback (we'll zip JSON on the fly if needed)
            posts_blob_path = f"{backup['id']}/posts+cap.json"

            # What we pass to checkout if unpaid
            blob_for_checkout = zip_blob_path or posts_blob_path
            # Name we want the user to get (prefer .zip)
            download_name = zip_name or f"{backup['id'].replace('/', '_')}.zip"

            # --- NEW: If paid, show a real download; else, show the pay button
            paid_for_download = _download_is_paid(backup["id"])

            if paid_for_download:
                try:
                    if zip_blob_path:
                        # Prefer a direct SAS link for reliability (large files)
                        sas = _sas_url_for_blob(zip_blob_path)
                        if sas:
                            st.link_button(
                                "📥 Download Backup",
                                sas,
                                use_container_width=True,
                            )
                        else:
                            # Fallback: stream bytes via Streamlit
                            data = container_client.get_blob_client(zip_blob_path).download_blob().readall()
                            st.download_button(
                                "📥 Download Backup",
                                data=data,
                                file_name=download_name,
                                mime="application/zip",
                                use_container_width=True,
                                key=f"dl_{safe_id}",
                            )

                    else:
                        # No .zip in storage yet — zip the JSON on the fly so the user still gets a .zip
                        posts_bc = container_client.get_blob_client(posts_blob_path)
                        if posts_bc.exists():
                            raw = posts_bc.download_blob().readall()
                            mem = BytesIO()
                            with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
                                zf.writestr("posts+cap.json", raw)
                            mem.seek(0)
                            st.download_button(
                                "📥 Download Backup",
                                data=mem.getvalue(),
                                file_name=download_name,
                                mime="application/zip",
                                use_container_width=True,
                                key=f"dl_{safe_id}",
                            )
                        else:
                            st.warning("Backup file isn’t available yet. Please try again in a moment.")
                except Exception as e:
                    st.error(f"Download failed: {e}")

            else:
                if st.button("📥 Download the Backup $9.99", key=f"pay_{safe_id}", use_container_width=True):
                    st.session_state["pending_download"] = {
                        "blob_path": blob_for_checkout,
                        "file_name": download_name,
                        "user_id": st.session_state.get("fb_id", "")
                    }
                    st.session_state["show_payment_modal"] = True
                    st.rerun()
            
            if DEBUG:
                st.caption(f"debug: paid_for_download={paid_for_download} • prefix={backup['id']}")





            is_paid_for_memories = _memories_is_paid(backup["id"])

            if SHOW_MEMORIES_BUTTON and is_paid_for_memories:
                if st.button("📘 Generate Memories", key=f"mem_{safe_id}", type="primary"):
                    st.session_state["selected_backup"] = backup['id']
                    st.switch_page("pages/FbMemories.py")
            elif SHOW_MEMORIES_BUTTON and not is_paid_for_memories:
                st.caption("🔒 Memories unlocks after purchase")

        st.divider()
    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="empty-state">
        <div class="empty-state-icon">📂</div>
        <h3>No backups yet</h3>
        <p>Create your first backup to get started.</p>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------
# Payment Modal (Inline)
# ---------------------------
if st.session_state.get("show_payment_modal"):
    pending = st.session_state.get("pending_download")
    display_name = (pending or {}).get("file_name") or "backup.zip"
    if not display_name.lower().endswith(".zip"):
        display_name = display_name.rsplit(".", 1)[0] + ".zip"

    # compute per-user cache hash
    token = st.session_state.get("fb_token", "")
    token_hash = hashlib.md5(token.encode()).hexdigest() if token else ""

    success_url_for_item = SUCCESS_URL
    if pending and isinstance(pending, dict) and pending.get("blob_path"):
        base_params = {
            "blob": pending["blob_path"],
            "name": display_name,
        }
        if token_hash:
            base_params["cache"] = token_hash
        sep0 = '&' if '?' in SUCCESS_URL else '?'
        success_url_for_item = f"{SUCCESS_URL}{sep0}{urlencode(base_params)}"

    st.markdown("---")
    st.markdown("### 💳 Complete Payment")
    st.caption(f"After payment, your download of **{display_name}** will start automatically.")
    
    # Payment UI
    if not BILLING_READY:
        st.info("⚠️ Stripe is not configured (missing STRIPE_SECRET_KEY). The checkout button is disabled.\n\nAdd STRIPE_SECRET_KEY to Streamlit Secrets. You can also set STRIPE_PRICE_ID / STRIPE_SUCCESS_URL / STRIPE_CANCEL_URL.")
    
    price_is_placeholder = (not RESOLVED_PRICE_ID) or RESOLVED_PRICE_ID.endswith("placeholder")
    
    if st.button("💳 Buy Now for $9.99", disabled=(not BILLING_READY or price_is_placeholder), key="payment_btn"):
        try:
            # add session_id to success url
            sep = '&' if '?' in success_url_for_item else '?'
            success_url_with_session = f"{success_url_for_item}{sep}session_id={{CHECKOUT_SESSION_ID}}"

            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{"price": RESOLVED_PRICE_ID, "quantity": 1}],
                mode="payment",
                success_url=success_url_with_session,
                cancel_url=CANCEL_URL,
                allow_promotion_codes=True,
                metadata={
                    "fb_id": st.session_state.get("fb_id", ""),
                    "fb_name": st.session_state.get("fb_name", ""),
                    "blob": (pending or {}).get("blob_path", ""),
                    "name": (pending or {}).get("file_name", ""),
                    "backup_prefix": _backup_prefix_from_blob_path((pending or {}).get("blob_path", "")),
                },
                customer_email=st.session_state.get("fb_email")
            )
            st.success("✅ Checkout session created!")
            
            # Use JavaScript redirect to keep same tab
            st.components.v1.html(f"""
            <script>
                window.location.href = "{session.url}";
            </script>
            """, height=0)
            
            st.session_state.pop("pending_download", None)
            st.session_state["show_payment_modal"] = False
            st.caption("You'll be taken to Stripe to complete your payment.")
        except stripe.error.StripeError as e:
            st.error(f"Stripe checkout error: {e}")
        except Exception as e:
            st.error(f"Unexpected error creating checkout session: {e}")

    if price_is_placeholder and BILLING_READY:
        st.caption("Set a real STRIPE_PRICE_ID (price_… or prod_… with an active price) in Secrets to enable the button.")
    
    if st.button("❌ Cancel Payment", key="cancel_payment"):
        st.session_state["show_payment_modal"] = False
        st.session_state.pop("pending_download", None)
        st.rerun()
