import os
import base64
import time
import secrets as pysecrets
from urllib.parse import urlencode

import requests
import streamlit as st
from PIL import Image
import hmac, hashlib, json, base64

def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")

def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * ((4 - len(s) % 4) % 4))

def make_state() -> str:
    """Create a signed, time-limited state token (no session needed)."""
    payload = {"ts": int(time.time()), "nonce": pysecrets.token_urlsafe(16)}
    raw = json.dumps(payload, separators=(",", ":")).encode()
    sig = hmac.new(st.secrets["STATE_SECRET"].encode(), raw, hashlib.sha256).digest()
    return _b64e(raw) + "." + _b64e(sig)

def verify_state(s: str, max_age: int = 600) -> bool:
    """Verify signature and max age (seconds)."""
    try:
        raw_b64, sig_b64 = s.split(".", 1)
        raw = _b64d(raw_b64)
        expected = hmac.new(st.secrets["STATE_SECRET"].encode(), raw, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64d(sig_b64)):
            return False
        data = json.loads(raw.decode())
        return int(time.time()) - int(data["ts"]) <= max_age
    except Exception:
        return False

# ── Page config ─────────────────────────────────────────────
st.set_page_config(
    page_title="LiveOn Fb",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="collapsed"
)

try:
    qp = st.query_params
    ping = qp.get("ping")
    ping = ping[0] if isinstance(ping, list) else ping
    if ping == "1":
        st.write("ok")
        st.stop()
except Exception:
    pass
# ── Settings ────────────────────────────────────────────────
TIMEOUT = 10
DEST_PAGE = "pages/Projects.py"  
DEBUG = str(st.secrets.get("DEBUG", "false")).strip().lower() == "true"

def dev(msg):
    if DEBUG:
        st.info(msg)

# ── Secrets (fail fast with clear guidance) ─────────────────
try:
    CLIENT_ID = st.secrets["FB_CLIENT_ID"]
    CLIENT_SECRET = st.secrets["FB_CLIENT_SECRET"]
    REDIRECT_URI = st.secrets["FB_REDIRECT_URI"]  
except KeyError as e:
    st.error(f"Missing secret: {e}. Add it in Streamlit → Settings → Secrets.")
    st.stop()

SCOPES = "email,public_profile,user_posts"

# ── Helpers ────────────────────────────────────────────────
def build_auth_url() -> str:
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "response_type": "code",
        "state": make_state(),         
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

# ── UI THEME (navy + gold, Minedco-style) ──────────────────
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
  font-weight:800; font-size: 34px; line-height:1;
}
.header-title .accent{ color: var(--gold); }

/* Hero card */
.hero-box{
  text-align:center; max-width:560px; margin: 0 auto;
  padding: 2.4rem 2rem;
  background: rgba(255,255,255,.06);
  border: 1px solid var(--line);
  border-radius: 16px;
  box-shadow: 0 10px 24px rgba(0,0,0,.18);
}
.hero-box h1{
  font-size: 2.2rem; font-weight: 800; margin-bottom:.6rem;
}
.hero-box p{
  font-size: 1.05rem; color: var(--muted); margin-bottom: 1.6rem;
}

/* Primary CTA (gold like site) */
.fb-button{
  background: var(--gold);
  color: var(--navy-900); font-weight:800; font-size:17px;
  padding: 12px 24px; border-radius: 8px; text-decoration:none; display:inline-block;
  border: none; box-shadow: 0 4px 14px rgba(246,195,93,.22);
  transition: transform .15s ease, box-shadow .15s ease, filter .15s ease;
}
.fb-button:hover{
  filter: brightness(.95);
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(246,195,93,.28);
}

/* Small subtext */
.subtext{ font-size:.95rem; margin-top:.9rem; color: var(--muted); }

/* Optional navbar look if you add one later */
.navbar{
  display:flex; justify-content:space-between; align-items:center;
  padding: 1rem 2rem; background: rgba(255,255,255,.04);
  border-bottom: 1px solid var(--line);
  box-shadow: 0 2px 6px rgba(0,0,0,.12);
}
.navbar a{ color: var(--text); text-decoration:none; margin-left:1.2rem; }
.navbar a:hover{ color: var(--gold); }

/* Streamlit alerts blending with theme */
div[data-testid="stAlert"]{
  border:1px solid var(--line); background: rgba(255,255,255,.06);
}
</style>
""", unsafe_allow_html=True)

# ── Header Logo/Banner (resilient) ─────────────────────────
logo_b64 = get_image_base64("media/logo.png")
if logo_b64:
    st.markdown(f"""
        <div class="header-container">
            <img src="data:image/png;base64,{logo_b64}" alt="Logo" />
            <div class="header-title">LiveOn <span class="accent">Fb</span></div>
        </div>
    """, unsafe_allow_html=True)
else:
    st.markdown('<h1 class="header-title">LiveOn <span class="accent">Fb</span></h1>', unsafe_allow_html=True)

try:
    banner = Image.open("media/banner.png")
    st.image(banner, use_container_width=True)
except Exception:
    pass  # banner optional

st.markdown("### Explore Facebook Post & Page Data Instantly")

# ── Query param helpers ─────────────────────────────────────
def get_qparam(name: str) -> str | None:
    qp = st.query_params
    if name not in qp:
        return None
    v = qp.get(name)
    return v[0] if isinstance(v, list) else v

# ── Main Login Logic (unchanged) ───────────────────────────
error = get_qparam("error")
error_desc = get_qparam("error_description")
code = get_qparam("code")
returned_state = get_qparam("state")

if error:
    st.error("Facebook login was not completed. Please try again.")
    dev(f"FB error: {error} - {error_desc}")
    st.query_params.clear()

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
            <h1>Let's Back Up Your <span class="accent">Facebook Memories</span></h1>
            <p>Link your Facebook account to get started—we’ll securely back up your posts, photos, and more.</p>
            <a href="{auth_url}" class="fb-button">🔗 Link Facebook Account</a>
            <div class="subtext">Already linked Facebook? <strong>Start New Backup</strong></div>
        </div>
    """, unsafe_allow_html=True)
