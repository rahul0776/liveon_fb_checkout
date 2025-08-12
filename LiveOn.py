import os
import base64
import time
import secrets as pysecrets
from urllib.parse import urlencode

import requests
import streamlit as st
from PIL import Image

# ── Page config ─────────────────────────────────────────────
st.set_page_config(page_title="LiveOn Fb", page_icon="📘", layout="wide")

# ── Settings ────────────────────────────────────────────────
TIMEOUT = 10
DEST_PAGE = "pages/Projects.py"  # keep consistent across the app
DEBUG = str(st.secrets.get("DEBUG", "false")).strip().lower() == "true"

def dev(msg):
    if DEBUG:
        st.info(msg)

# ── Secrets (fail fast with clear guidance) ─────────────────
try:
    CLIENT_ID = st.secrets["FB_CLIENT_ID"]
    CLIENT_SECRET = st.secrets["FB_CLIENT_SECRET"]
    REDIRECT_URI = st.secrets["FB_REDIRECT_URI"]  # must EXACTLY match in Facebook App settings
except KeyError as e:
    st.error(f"Missing secret: {e}. Add it in Streamlit → Settings → Secrets.")
    st.stop()

SCOPES = "email,public_profile,user_posts"

# ── Helpers ────────────────────────────────────────────────
def build_auth_url() -> str:
    # CSRF state
    if "oauth_state" not in st.session_state:
        st.session_state["oauth_state"] = pysecrets.token_urlsafe(24)

    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "response_type": "code",
        "state": st.session_state["oauth_state"],
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

# ── CSS + Header ───────────────────────────────────────────
st.markdown("""
<style>
.main { background-color: #0e1117; }
h1, h3, .stMarkdown { text-align: center; color: white; }
.header-container { display: flex; align-items: center; justify-content: center; gap: 1rem; margin-bottom: 1rem; }
.header-container img { width: 60px; }
.navbar { display: flex; justify-content: space-between; align-items: center; padding: 1.2rem 2rem; background-color: #fdfdfd;
          box-shadow: 0 2px 6px rgba(0,0,0,0.05); margin-bottom: 3rem; border-bottom: 1px solid #ddd; }
.navbar a { margin-left: 1.5rem; text-decoration: none; color: #222; font-weight: 500; }
.hero-box { text-align: center; max-width: 480px; margin: 0 auto; padding: 3rem 2rem; background: #fff; border-radius: 16px;
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.08); }
.hero-box h1 { font-size: 2.4rem; font-weight: 700; margin-bottom: 1.2rem; color: #111; }
.hero-box p { font-size: 1.05rem; color: #333; margin-bottom: 2rem; }
.fb-button { background-color: #1877f2; color: white; padding: 12px 24px; font-size: 17px; font-weight: 600; border: none;
             border-radius: 6px; text-decoration: none; display: inline-block; }
.fb-button:hover { background-color: #155edb; }
.subtext { font-size: 0.95rem; margin-top: 1rem; color: #444; }
</style>
""", unsafe_allow_html=True)

# ── Header Logo/Banner (resilient) ─────────────────────────
logo_b64 = get_image_base64("media/logo.png")
if logo_b64:
    st.markdown(f"""
        <div class="header-container">
            <img src="data:image/png;base64,{logo_b64}" />
            <h1>LiveOn Fb</h1>
        </div>
    """, unsafe_allow_html=True)
else:
    st.markdown('<h1 style="text-align:center;color:white;">LiveOn Fb</h1>', unsafe_allow_html=True)

try:
    banner = Image.open("media/banner.png")
    st.image(banner, use_container_width=True)
except Exception:
    pass  # banner optional

st.markdown("### Explore Facebook Post & Page Data Instantly")

# Sidebar token status (non-sensitive)
with st.sidebar:
    if "fb_token" in st.session_state:
        st.success("🔐 Facebook Token: Stored ✅")
    else:
        st.warning("🔐 Facebook Token: Missing")

# ── Query param helpers ─────────────────────────────────────
def get_qparam(name: str) -> str | None:
    qp = st.query_params
    if name not in qp:
        return None
    v = qp.get(name)
    # st.query_params can return str or list[str]
    return v[0] if isinstance(v, list) else v

# ── Main Login Logic ───────────────────────────────────────
error = get_qparam("error")
error_desc = get_qparam("error_description")
code = get_qparam("code")
returned_state = get_qparam("state")

if error:
    # User cancelled or FB returned an error
    st.error("Facebook login was not completed. Please try again.")
    dev(f"FB error: {error} - {error_desc}")
    # Clear error params so refresh is clean
    st.query_params.clear()

elif code:
    if not returned_state or returned_state != st.session_state.get("oauth_state"):
        st.error("Security check failed. Please start the login again.")
    else:
        st.info("🔄 Connecting to Facebook…")
        access_token = exchange_code_for_token(code)

        if access_token:
            # Store token for subsequent pages (do not print)
            st.session_state["fb_token"] = access_token
            st.session_state["token_issued_at"] = int(time.time())
            st.success("✅ Login successful! Redirecting…")
            # Clear query params to avoid reprocessing on refresh
            try:
                st.query_params.clear()
            except Exception:
                pass
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
            <h1>Let's Back Up Your Facebook Memories</h1>
            <p>Looks like you haven’t created a memory vault yet.<br>
            Link your Facebook account to get started—we’ll securely back up your posts, photos, and more.</p>
            <a href="{auth_url}" class="fb-button">🔗 Link Facebook Account</a>
            <div class="subtext">Already linked Facebook? <strong>Start New Backup</strong></div>
        </div>
    """, unsafe_allow_html=True)
