import streamlit as st
import stripe
import json
from pathlib import Path
import time

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

st.set_page_config(page_title="Stripe Checkout Demo", page_icon="💳")
st.title("🧾 Stripe Checkout Test Harness")

PRICE_ID = "price_1RnjFTP1KF2yA8BHkENSPqlp"  
SUCCESS_URL = "https://liveonfb.streamlit.app/success"
CANCEL_URL = "https://liveonfb.streamlit.app/cancel"

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

        # Poll Stripe API for payment status
        placeholder = st.empty()
        for i in range(2):  # Poll for ~30 seconds
            time.sleep(3)
            try:
                checkout_session = stripe.checkout.Session.retrieve(session.id)
                status = checkout_session["status"]
                payment_status = checkout_session["payment_status"]

                if payment_status == "paid":
                    st.switch_page("pages/success.py")
                elif status == "expired":
                    st.switch_page("pages/cancel.py")

                placeholder.write(f"⌛ Waiting for payment... (Check {i+1}/30)")
            except Exception as e:
                placeholder.error(f"Error checking status: {e}")
                break

    except Exception as e:
        st.error(f"❌ Error creating Stripe Checkout session:\n\n{e}")
