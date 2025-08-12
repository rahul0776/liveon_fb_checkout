import os, json
from pathlib import Path
import streamlit as st
import stripe

# ----------------- MUST BE FIRST -----------------
st.set_page_config(
    page_title="LiveOn · Facebook Backup",
    page_icon="💾",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Optional: your global theme (won't change behavior)
from utils.theme import inject_global_styles
inject_global_styles()

# ----------------- Helpers -----------------
def _get_secret(name: str, default: str | None = None) -> str | None:
    try:
        return st.secrets[name]  # type: ignore[index]
    except Exception:
        return os.environ.get(name, default)

def restore_session() -> None:
    if all(k in st.session_state for k in ["fb_id", "fb_name", "fb_token"]):
        return
    cache_dir = Path("cache")
    if not cache_dir.exists():
        return
    for file in cache_dir.glob("backup_cache_*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if "fb_token" in cached:
                st.session_state["fb_token"] = cached.get("fb_token")
                st.session_state["fb_id"] = cached.get("fb_id") or cached.get("latest_backup", {}).get("user_id")
                st.session_state["fb_name"] = cached.get("fb_name") or cached.get("latest_backup", {}).get("name")
                return
        except Exception:
            continue

# ----------------- Bootstrap -----------------
restore_session()
if "fb_token" not in st.session_state:
    st.warning("🔐 Please login with Facebook first.")
    st.stop()

# Stripe config
STRIPE_SECRET_KEY = _get_secret("STRIPE_SECRET_KEY")
PRICE_ID = _get_secret("STRIPE_PRICE_ID", "price_1234567890placeholder")
SUCCESS_URL = _get_secret("STRIPE_SUCCESS_URL", "http://localhost:8501/success")
CANCEL_URL  = _get_secret("STRIPE_CANCEL_URL",  "http://localhost:8501/cancel")

BILLING_READY = bool(STRIPE_SECRET_KEY)
if BILLING_READY:
    stripe.api_key = STRIPE_SECRET_KEY  # type: ignore[arg-type]

# ----------------- Page CSS (Minedco look) -----------------
st.markdown("""
<style>
:root{
  --navy:#0F253D; --navy-2:#12304B; --ink:#1A2B3A; --bg:#F6FAFF;
  --gold:#F6C35D; --muted:#5E738A; --line:#E8EEF5;
}
html,body,.stApp{ background:var(--bg); color:var(--ink); font-family:Inter,system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial }
.page{ display:flex; flex-direction:column; align-items:center; gap:14px; margin-top:8px }
.hero-title{ font-weight:800; color:var(--navy); text-align:center; margin:0 }
.hero-sub{ text-align:center; margin-top:4px; color:var(--muted) }
.card{
  background:#fff; padding:18px 18px 22px; border-radius:14px;
  border:1px solid var(--line); box-shadow:0 6px 16px rgba(0,0,0,.06);
  text-align:center; width:360px;
}
.center-image img{ display:block; margin:0 auto; width:260px; border-radius:10px; border:1px solid var(--line); }
.stButton>button{
  width:100%; background:var(--gold); color:var(--navy-2)!important;
  font-size:16px; padding:12px 14px; border-radius:10px; font-weight:800; border:none;
  box-shadow:0 4px 12px rgba(246,195,93,.28); transition:transform .12s ease, filter .12s ease;
}
.stButton>button:hover{ transform:translateY(-1px); filter:brightness(.97) }
.small{ color:var(--muted); font-size:13px; margin-top:8px }
</style>
""", unsafe_allow_html=True)

# ----------------- UI -----------------
st.markdown("<div class='page'>", unsafe_allow_html=True)

st.markdown("<h2 class='hero-title'>💾 Secure Facebook Backup</h2>", unsafe_allow_html=True)
st.markdown("<div class='hero-sub'>Purchase your backup securely and get instant access to your Facebook memories.</div>", unsafe_allow_html=True)

st.markdown("<div class='center-image'><img src='https://raw.githubusercontent.com/rahul0776/liveon_fb_checkout/main/media/liveon_image.png' alt='LiveOn'></div>", unsafe_allow_html=True)

st.markdown("<div class='card'>", unsafe_allow_html=True)

if not BILLING_READY:
    st.info(
        "⚠️ Stripe is not configured (missing STRIPE_SECRET_KEY). The checkout button is disabled.\n\n"
        "Add STRIPE_SECRET_KEY to Streamlit Secrets. You can also set STRIPE_PRICE_ID / STRIPE_SUCCESS_URL / STRIPE_CANCEL_URL."
    )

# Guard against placeholder price
price_is_placeholder = (PRICE_ID or "").endswith("placeholder")

# Button (disabled if Stripe not ready or price missing)
if st.button("💳 Buy Now for $9.99", disabled=(not BILLING_READY or price_is_placeholder)):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": PRICE_ID, "quantity": 1}],
            mode="payment",
            success_url=SUCCESS_URL,
            cancel_url=CANCEL_URL,
            allow_promotion_codes=True,
            metadata={
                "fb_id": st.session_state.get("fb_id", ""),
                "fb_name": st.session_state.get("fb_name", ""),
            },
            customer_email=st.session_state.get("fb_email")  # ok if None
        )
        st.success("✅ Checkout session created!")
        st.link_button("👉 Continue to Secure Checkout", session.url)
        st.caption("You’ll be taken to Stripe to complete your payment.")
    except Exception as e:
        st.error(f"❌ Error creating Stripe Checkout session:\n\n{e}")

if price_is_placeholder and BILLING_READY:
    st.caption("Set a real STRIPE_PRICE_ID in Secrets to enable the button.", help="Use the 'price_...' ID from your Stripe product.")

st.markdown("</div></div>", unsafe_allow_html=True)
