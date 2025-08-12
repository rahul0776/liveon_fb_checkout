import base64
import time
import hmac
import hashlib
import secrets as pysecrets
from urllib.parse import urlencode

import requests
import streamlit as st
from PIL import Image

# ── Page config ─────────────────────────────────────────────
st.set_page_config(
    page_title="LiveOn Fb",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Settings ────────────────────────────────────────────────
TIMEOUT = 10
DEST_PAGE = "pages/Projects.py"
DEBUG = str(st.secrets.get("DEBUG", "false")).strip().lower() == "true"

def dev(msg: str):
    if DEBUG:
        st.info(msg)

# ── Required secrets ───────────────────────────────────────
try:
    CLIENT_ID = st.secrets["FB_CLIENT_ID"]
    CLIENT_SECRET = st.secrets["FB_CLIENT_SECRET"]
    REDIRECT_URI = st.secrets["FB_REDIRECT_URI"]  # must match FB app "Valid OAuth Redirect URIs"
    STATE_SECRET = st.secrets["STATE_SECRET"]     # new: used to sign OAuth state
except KeyError as e:
    st.error(f"Missing secret: {e}. Add it in Streamlit → Settings → Secrets.")
    st.stop()

SCOPES = "email,public_profile,user_posts"

# ── Stateless CSRF helpers (HMAC signed state) ─────────────
def make_state() -> str:
    ts = str(int(time.time()))
    nonce = pysecrets.token_urlsafe(8)
    msg = f"{ts}.{nonce}".encode()
    sig = hmac.new(STATE_SECRET.encode(), msg, hashlib.sha256).hexdigest()
    return f"{ts}.{nonce}.{sig}"

def verify_state(state: str, max_age_sec: int = 600) -> bool:
    try:
        ts, nonce, sig = state.split(".")
        msg = f"{ts}.{nonce}".encode()
        expected = hmac.new(STATE_SECRET.encode(), msg, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return False
        # freshness check
        age = int(time.time()) - int(ts)
        return 0 <= age <= max_age_sec
    except Exception:
        return False

# ── Helpers ────────────────────────────────────────────────
def build_auth_url() -> str:
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "response_type": "code",
        "state": make_state(),  # stateless
    }
    return "https://www.facebook.com/v18.0/dialog/oauth?" + urlencode(params)

def exchange_code_for_token(code: str) -> str | None:
    try:
        resp = requests.get(
            "https://graph.facebook.com/v18.0/oauth/access_token",
            params={
                "client_id": CLIENT_ID,
                "redirect_uri": REDIRECT_URI,
                "client_secret": CLIENT_SECRET,
                "code": code,
            },
            timeout=TIMEOUT,
        )
        if resp.status_code != 200:
            dev(f"Token exchange failed: {resp.status_code} {resp.text[:200]}")
            return None
        return resp.json().get("access_token")
    except Exception as e:
        dev(f"Token exchange error: {e}")
        return None

def get_image_base64(path: str) -> str | None:
    try:
        with open(path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception as e:
        dev(f"Image load failed for {path}: {e}")
        return None

def get_qparam(name: str) -> str | None:
    qp = st.query_params
    if name not in qp:
        return None
    v = qp.get(name)
    return v[0] if isinstance(v, list) else v

# ── Brand CSS (navy + gold) ────────────────────────────────
st.markdown("""
<style>
:root{
  --navy-900:#0F253D; --navy-700:#1E3A5F; --navy-500:#2E5984; --navy-300:#3B75A6;
  --accent:#F6C35D; --text:#F2F4F8; --muted:#B9C6D6; --card:#122B46; --card-border:rgba(255,255,255,.14);
}
html, body, .stApp{
  background: linear-gradient(180deg, var(--navy-900) 0%, #183354 55%, #1C4063 100%);
  color: var(--text);
  font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
}
h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3{ color: var(--text) !important; letter-spacing:.2px; }
.header-container{ display:flex; align-items:center; justify-content:center; gap:1rem; margin-bottom:1rem; }
.header-container img{ width:56px; filter: drop-shadow(0 2px 8px rgba(0,0,0,.25)); }
.hero-box{
  text-align:center; max-width:560px; margin: 0 auto; padding: 2.5rem 2rem;
  background: rgba(255,255,255,.06); border: 1px solid var(--card-border); border-radius: 16px;
  box-shadow: 0 10px 24px rgba(0,0,0,0.18); color: var(--text);
}
.hero-box h1{ font-size: 2.3rem; font-weight: 800; margin-bottom: .6rem; color: var(--text); }
.hero-box h1 .accent{ color: var(--accent); }
.hero-box p{ font-size: 1.05rem; color: var(--muted); margin-bottom: 1.6rem; }
.fb-button{
  background: var(--navy-500); color: #fff; padding: 12px 24px; font-size: 17px; font-weight: 700;
  border: 1px solid var(--card-border); border-radius: 8px; text-decoration:none; display:inline-block; transition: all .18s ease;
}
.fb-button:hover{ background: var(--navy-700); transform: translateY(-1px); }
.subtext{ font-size: .95rem; margin-top: .9rem; color: var(--muted); }
</style>
""", unsafe_allow_html=True)

# ── Header Logo/Banner ─────────────────────────────────────
logo_b64 = get_image_base64("media/logo.png")
if logo_b64:
    st.markdown(f"""
        <div class="header-container">
            <img src="data:image/png;base64,{logo_b64}" />
            <h1>LiveOn <span class="accent">Fb</span></h1>
        </div>
    """, unsafe_allow_html=True)
else:
    st.markdown('<h1 style="text-align:center;color:#F2F4F8;">LiveOn <span style="color:#F6C35D;">Fb</span></h1>', unsafe_allow_html=True)

try:
    banner = Image.open("media/banner.png")
    st.image(banner, use_container_width=True)
except Exception:
    pass

# ── OAuth flow ─────────────────────────────────────────────
error = get_qparam("error")
error_desc = get_qparam("error_description")
code = get_qparam("code")
returned_state = get_qparam("state")

if error:
    st.error("Facebook login was not completed. Please try again.")
    dev(f"FB error: {error} - {error_desc}")
    try: st.query_params.clear()
    except Exception: pass

elif code:
    if not returned_state or not verify_state(returned_state):
        st.error("Security check failed. Please start the login again.")
    else:
        st.info("🔄 Connecting to Facebook…")
        access_token = exchange_code_for_token(code)
        if access_token:
            st.session_state["fb_token"] = access_token
            st.session_state["token_issued_at"] = int(time.time())
            st.success("✅ Login successful! Redirecting…")
            try: st.query_params.clear()
            except Exception: pass
            time.sleep(0.8)
            st.switch_page(DEST_PAGE)
        else:
            st.error("❌ Could not sign you in. Please try again.")

elif "fb_token" in st.session_state:
    st.success("✅ Already linked. Taking you to your dashboard…")
    time.sleep(0.6)
    st.switch_page(DEST_PAGE)

else:
    auth_url = build_auth_url()
    st.markdown(f"""
        <div class="hero-box">
            <h1>Back Up Your <span class="accent">Memories</span></h1>
            <p>Link your Facebook account to securely back up your posts, photos, and more.</p>
            <a href="{auth_url}" class="fb-button">🔗 Link Facebook Account</a>
            <div class="subtext">Already linked? <strong>Start New Backup</strong></div>
        </div>
    """, unsafe_allow_html=True)
