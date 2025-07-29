import streamlit as st
import stripe
import json
from pathlib import Path

# Restore session function
def restore_session():
    if all(k in st.session_state for k in ["fb_id", "fb_name", "fb_token"]):
        return
    cache_dir = Path("cache")
    if cache_dir.exists():
        for file in cache_dir.glob("backup_cache_*.json"):
            try:
                with open(file, "r") as f:
                    cached = json.load(f)
                    if "fb_token" in cached:
                        st.session_state["fb_token"] = cached.get("fb_token")
                        st.session_state["fb_id"] = cached.get("fb_id") or cached.get("latest_backup", {}).get("user_id")
                        st.session_state["fb_name"] = cached.get("fb_name") or cached.get("latest_backup", {}).get("name")
                        return
            except:
                continue

restore_session()

if "fb_token" not in st.session_state:
    st.warning("🔐 Please login with Facebook first.")
    st.stop()

stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]
PRICE_ID = "price_1RnjFTP1KF2yA8BHkENSPqlp"
SUCCESS_URL = "https://liveonfb.streamlit.app/success"
CANCEL_URL = "https://liveonfb.streamlit.app/cancel"

st.set_page_config(page_title="LiveOn · Facebook Backup", page_icon="💳", layout="centered")

st.markdown("""
<style>
.main {
    padding-top: 0rem;
}
.page-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    margin-top: 5px;
}
.center-image {
    display: flex;
    justify-content: center;
}
.card {
    background: white;
    padding: 16px;
    border-radius: 10px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.08);
    text-align: center;
    width: 340px;
}
.stButton>button {
    width: 100%;
    background-color: #1877F2;
    color: white;
    font-size: 16px;
    padding: 12px;
    border-radius: 6px;
    font-weight: 600;
}
.stButton>button:hover {
    background-color: #0f5bb5;
}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='page-container'>", unsafe_allow_html=True)

st.markdown("<h2 style='text-align:center;'>💾 Secure Facebook Backup</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; margin-top:-6px;'>Purchase your backup securely and get instant access to your Facebook memories.</p>", unsafe_allow_html=True)

# ✅ Center the image properly
st.markdown("<div class='center-image'>", unsafe_allow_html=True)
st.image("media/liveon_image.png", width=260)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='card'>", unsafe_allow_html=True)

if st.button("💳 Buy Now for $9.99"):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": PRICE_ID, "quantity": 1}],
            mode="payment",
            success_url=SUCCESS_URL,
            cancel_url=CANCEL_URL,
        )
        st.success("✅ Checkout session created!")
        st.markdown(f"[👉 Click here to pay with Stripe]({session.url})", unsafe_allow_html=True)
    except Exception as e:
        st.error(f"❌ Error creating Stripe Checkout session:\n\n{e}")

st.markdown("</div></div>", unsafe_allow_html=True)
