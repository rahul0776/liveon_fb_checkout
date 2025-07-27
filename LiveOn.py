import streamlit as st
import requests
import time
from urllib.parse import urlencode
from PIL import Image
import base64

st.set_page_config(page_title="LiveOn Fb", page_icon="📘", layout="wide")

# ── CREDENTIAL SETUP ─────────────────────────────────────────────
CLIENT_ID = st.secrets["FB_CLIENT_ID"]
CLIENT_SECRET = st.secrets["FB_CLIENT_SECRET"]
REDIRECT_URI = st.secrets["FB_REDIRECT_URI"]

auth_url = "https://www.facebook.com/v18.0/dialog/oauth?" + urlencode({
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "scope": "email,public_profile,user_posts",
    "response_type": "code",
    "state": "fb_login"
})

# ── CSS + HEADER ─────────────────────────────────────────────
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

# ── Header Logo ─────────────────────────────────────────────
def get_image_base64(path):
    with open(path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

logo_base64 = get_image_base64("media/logo.png")
banner = Image.open("media/banner.png")

st.markdown(f"""
    <div class="header-container">
        <img src="data:image/png;base64,{logo_base64}" />
        <h1>LiveOn Fb</h1>
    </div>
""", unsafe_allow_html=True)

st.image(banner, use_container_width=True)

st.markdown("### Explore Facebook Post & Page Data Instantly")

# Sidebar token status
with st.sidebar:
    if "fb_token" in st.session_state:
        st.success("🔐 Facebook Token: Stored ✅")
    else:
        st.warning("🔐 Facebook Token: Missing")

# ── Helper to exchange code for token ─────────────────────────────
def exchange_code_for_token(code: str) -> str | None:
    try:
        response = requests.get("https://graph.facebook.com/v18.0/oauth/access_token", params={
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "client_secret": CLIENT_SECRET,
            "code": code
        }, timeout=6)
        response.raise_for_status()
        return response.json().get("access_token")
    except Exception as e:
        st.error("❌ Error while exchanging code for token.")
        st.exception(e)
        return None

# ── Main Login Logic ─────────────────────────────────────────────
if "code" in st.query_params:
    code = st.query_params["code"]
    st.info("🔄 Received code, exchanging for access token…")

    access_token = exchange_code_for_token(code)

    if access_token:
        st.session_state["fb_token"] = access_token
        st.success("✅ Login successful! Redirecting to start your backup…")
        time.sleep(1)
        st.switch_page("pages/Projects.py")
    else:
        st.error("❌ Failed to obtain access token.")

elif "fb_token" in st.session_state:
    st.success("✅ Already logged in. Redirecting to your Facebook Backup page…")
    time.sleep(1)
    st.switch_page("pages/Projects.py")

else:
    st.markdown(f"""
        <div class="hero-box">
            <h1>Let's Back Up Your Facebook Memories</h1>
            <p>Looks like you haven’t created a memory vault yet.<br>
            Link your Facebook account to get started—we’ll securely back up your posts, photos, and more.</p>
            <a href="{auth_url}" class="fb-button">🔗 Link Facebook Account</a>
            <div class="subtext">Already linked Facebook? <strong>Start New Backup</strong></div>
        </div>
    """, unsafe_allow_html=True)
