import streamlit as st  # type: ignore
from PIL import Image
import base64

st.set_page_config(page_title="LiveOn Fb", page_icon="📘", layout="wide")

# ✅ Use modern query param API
query_params = st.query_params
if "token" in query_params and "fb_token" not in st.session_state:
    st.session_state["fb_token"] = query_params["token"][0]
    st.query_params.clear()  # Clears query params from URL

# Sidebar message
with st.sidebar:
    if "fb_token" in st.session_state:
        st.success("🔐 Facebook Token: Stored ✅")
    else:
        st.warning("🔐 Facebook Token: Missing")

# Dark theme styling
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    h1, h3, .stMarkdown {
        text-align: center;
        color: white;
    }
    .header-container {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 1rem;
        margin-bottom: 1rem;
    }
    .header-container img {
        width: 60px;
    }
    </style>
""", unsafe_allow_html=True)

def get_image_base64(path):
    with open(path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

# Load and display header image
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