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

def make_state(extra_data: dict = None) -> str:
    """Create a signed, time-limited state token (no session needed)."""
    payload = {"ts": int(time.time()), "nonce": pysecrets.token_urlsafe(16)}
    if extra_data:
        payload.update(extra_data)
    raw = json.dumps(payload, separators=(",", ":")).encode()
    sig = hmac.new(st.secrets["STATE_SECRET"].encode(), raw, hashlib.sha256).digest()
    return _b64e(raw) + "." + _b64e(sig)

def verify_state(s: str, max_age: int = 600) -> dict | None:
    """Verify signature and max age (seconds). Returns payload if valid, None otherwise."""
    try:
        raw_b64, sig_b64 = s.split(".", 1)
        raw = _b64d(raw_b64)
        expected = hmac.new(st.secrets["STATE_SECRET"].encode(), raw, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64d(sig_b64)):
            return None
        data = json.loads(raw.decode())
        if int(time.time()) - int(data["ts"]) > max_age:
            return None
        return data
    except Exception:
        return None

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

# Initial login: Only request basic profile and photos (NO posts yet)
# Posts permission will be requested later when user wants to create storybook
INITIAL_SCOPES = "public_profile,user_photos"
POSTS_SCOPES = "public_profile,user_photos,user_posts"  # Additional permission for storybook

# Default to initial scopes
SCOPES = INITIAL_SCOPES

# ── Helpers ────────────────────────────────────────────────
def build_auth_url(additional_scopes="") -> str:
    """
    Build OAuth URL for Facebook login.
    
    Args:
        additional_scopes: Additional scopes to request (e.g., "user_posts" for storybook creation)
    """
    scopes = INITIAL_SCOPES
    if additional_scopes:
        # Add additional scopes if provided
        scopes = f"{INITIAL_SCOPES},{additional_scopes}"
    
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": scopes,
        "response_type": "code",
        "state": make_state(),         
    }
    return "https://www.facebook.com/v18.0/dialog/oauth?" + urlencode(params)

def build_posts_auth_url() -> str:
    """
    Build OAuth URL specifically for requesting posts permission.
    This is used when user wants to create a storybook and needs posts access.
    """
    return build_auth_url("user_posts")


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

/* Enhanced Primary Button Styling */
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #F6C35D 0%, #F4B942 100%) !important;
  color: var(--navy-900) !important;
  font-weight: 800 !important;
  font-size: 15px !important;
  padding: 11px 28px !important;
  border-radius: 10px !important;
  border: none !important;
  box-shadow: 0 6px 20px rgba(246, 195, 93, 0.35), 
              0 2px 8px rgba(0, 0, 0, 0.15) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
  position: relative !important;
  overflow: hidden !important;
}

.stButton > button[kind="primary"]::before {
  content: '' !important;
  position: absolute !important;
  top: 0 !important;
  left: -100% !important;
  width: 100% !important;
  height: 100% !important;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent) !important;
  transition: left 0.5s !important;
}

.stButton > button[kind="primary"]:hover {
  transform: translateY(-2px) scale(1.02) !important;
  box-shadow: 0 8px 28px rgba(246, 195, 93, 0.45), 
              0 4px 12px rgba(0, 0, 0, 0.2) !important;
  background: linear-gradient(135deg, #F8CA6D 0%, #F6C152 100%) !important;
}

.stButton > button[kind="primary"]:hover::before {
  left: 100% !important;
}

.stButton > button[kind="primary"]:active {
  transform: translateY(0px) scale(0.98) !important;
  box-shadow: 0 4px 12px rgba(246, 195, 93, 0.3) !important;
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
    state_data = verify_state(returned_state)
    if not returned_state or not state_data:
        st.error("Security check failed. Please start the login again.")
    else:
        st.info("🔄 Connecting to Facebook…")
        access_token = exchange_code_for_token(code)
        if access_token:
            st.session_state["fb_token"] = access_token
            st.session_state["token_issued_at"] = int(time.time())
            # Check if this is a return from memories permission request
            # Now we check the state payload instead of query param
            return_to = state_data.get("return_to")
            if return_to == "memories":
                # Restore selection state if present
                if state_data.get("selected_backup"):
                    st.session_state["selected_backup"] = state_data["selected_backup"]
                if state_data.get("selected_project"):
                    st.session_state["selected_project"] = state_data["selected_project"]
                    
                st.success("✅ Permission granted! Redirecting to Memories…")
                try: st.query_params.clear()
                except: pass
                time.sleep(0.8)
                st.switch_page("pages/FbMemories.py")
            else:
                st.success("✅ Login successful! Redirecting…")
                try: st.query_params.clear()
                except: pass
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
    
    # Session state for showing the permission explanation modal/container
    if "show_auth_modal" not in st.session_state:
        st.session_state["show_auth_modal"] = False

    def show_modal():
        st.session_state["show_auth_modal"] = True

    def hide_modal():
        st.session_state["show_auth_modal"] = False

    if st.session_state["show_auth_modal"]:
        # Show the explanation "box"
        st.markdown("""
            <div class="hero-box">
                <h2>🔒 Permission Request</h2>
                <p style="margin-bottom: 20px;">
                    To securely back up your photos, we need the following permissions:
                </p>
                <ul style="text-align: left; display: inline-block; margin-bottom: 20px; color: var(--muted);">
                    <li><strong>Public Profile:</strong> To identify your account.</li>
                    <li><strong>Photos:</strong> To back up your uploaded photos.</li>
                </ul>
                <p style="font-size: 0.9rem; color: var(--gold); margin-bottom: 24px;">
                    ⚠️ We will <strong>NOT</strong> access your posts at this stage.
                </p>
                <div style="display: flex; gap: 12px; justify-content: center;">
                    <a href="{auth_url}" class="fb-button">✅ Proceed to Facebook</a>
                </div>
                <div style="margin-top: 16px;">
                    <button onclick="parent.window.location.reload()" style="background:transparent; border:none; color:var(--muted); cursor:pointer; text-decoration:underline;">Cancel</button>
                </div>
            </div>
        """.format(auth_url=auth_url), unsafe_allow_html=True)
        
        # Streamlit button for cancel (hidden but functional if we wanted pure python, 
        # but the HTML button above with reload is a quick hack to reset state if JS allowed, 
        # otherwise we use a streamlit button below for robustness)
        if st.button("Cancel", type="secondary"):
            hide_modal()
            st.rerun()

    else:
        # Default Hero UI
        st.markdown(f"""
            <div class="hero-box">
                <h1>Let's Back Up Your <span class="accent">Facebook Photos</span></h1>
                <p>Link your Facebook account to get started—we'll securely back up your photos and create a downloadable archive.</p>
            </div>
        """, unsafe_allow_html=True)
        
        # We use a streamlit button here to trigger the state change
        # We style it to look like the link or just place it inside the box logic
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔗 Link Facebook Account", use_container_width=True, type="primary"):
                show_modal()
                st.rerun()

        st.markdown("""
            <div class="hero-box" style="border:none; box-shadow:none; background:transparent; padding-top:0;">
                <div class="subtext">We'll request posts permission later when you create your storybook.</div>
            </div>
        """, unsafe_allow_html=True)
