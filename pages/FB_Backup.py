import os
import json
from pathlib import Path

import streamlit as st
import stripe

from utils.theme import inject_global_styles

inject_global_styles()


# ── Helpers ─────────────────────────────────────────────────────────────────

def _get_secret(name: str, default: str | None = None) -> str | None:
    """Return a secret from Streamlit or env vars without crashing locally.
    Usage: _get_secret("STRIPE_SECRET_KEY")
    """
    try:
        return st.secrets[name]  # type: ignore[index]
    except Exception:
        return os.environ.get(name, default)


def restore_session() -> None:
    """Restore fb_token / fb_id / fb_name from a cached file if needed."""
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
                st.session_state["fb_id"] = (
                    cached.get("fb_id")
                    or cached.get("latest_backup", {}).get("user_id")
                )
                st.session_state["fb_name"] = (
                    cached.get("fb_name")
                    or cached.get("latest_backup", {}).get("name")
                )
                return
        except Exception:
            # Ignore malformed cache files and try the next
            continue


# ── Bootstrap ────────────────────────────────────────────────────────────────
restore_session()

if "fb_token" not in st.session_state:
    st.warning("🔐 Please login with Facebook first.")
    st.stop()

# Stripe config — safe access via secrets OR env vars
STRIPE_SECRET_KEY = _get_secret("STRIPE_SECRET_KEY")
PRICE_ID = _get_secret("STRIPE_PRICE_ID", "price_1234567890placeholder")
SUCCESS_URL = _get_secret("STRIPE_SUCCESS_URL", "http://localhost:8501/success")
CANCEL_URL = _get_secret("STRIPE_CANCEL_URL", "http://localhost:8501/cancel")

BILLING_READY = bool(STRIPE_SECRET_KEY)
if BILLING_READY:
    stripe.api_key = STRIPE_SECRET_KEY  # type: ignore[arg-type]


# ── Page UI ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LiveOn · Facebook Backup",
    page_icon="💾",
    layout="centered",
)

st.markdown(
    """
<style>
.page-container { display:flex; flex-direction:column; align-items:center; gap:14px; margin-top:0px; }
.center-image img { display:block; margin-left:auto; margin-right:auto; width:250px; border-radius:6px; }
.card { background:white; padding:16px; border-radius:10px; box-shadow:0 4px 10px rgba(0,0,0,0.08); text-align:center; width:340px; }
.stButton>button { width:100%; background-color:#1877F2; color:white; font-size:16px; padding:12px; border-radius:6px; font-weight:600; }
.stButton>button:hover { background-color:#0f5bb5; }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown("<div class='page-container'>", unsafe_allow_html=True)

st.markdown("<h2 style='text-align:center;'>💾 Secure Facebook Backup</h2>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align:center; margin-top:-6px;'>Purchase your backup securely and get instant access to your Facebook memories.</p>",
    unsafe_allow_html=True,
)

# Center image
st.markdown(
    "<div class='center-image'><img src='https://raw.githubusercontent.com/rahul0776/liveon_fb_checkout/main/media/liveon_image.png' alt='LiveOn'></div>",
    unsafe_allow_html=True,
)

st.markdown("<div class='card'>", unsafe_allow_html=True)

if not BILLING_READY:
    st.info(
        "⚠️ Stripe is not configured (missing STRIPE_SECRET_KEY). The checkout button is disabled.\n\n"
        "Add STRIPE_SECRET_KEY to .streamlit/secrets.toml or set the environment variable."
        " Optionally set STRIPE_PRICE_ID / STRIPE_SUCCESS_URL / STRIPE_CANCEL_URL as well."
    )

# Disabled unless billing is ready
if st.button("💳 Buy Now for $9.99", disabled=not BILLING_READY):
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