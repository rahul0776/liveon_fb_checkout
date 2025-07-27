import streamlit as st
import stripe

stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]

st.set_page_config(page_title="Stripe Checkout Demo", page_icon="💳")
st.title("🧾 Stripe Checkout Test Harness")

PRICE_ID = "price_1RnjFTP1KF2yA8BHkENSPqlp"  # Replace with your real price ID

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
    except Exception as e:
        st.error(f"❌ Error creating Stripe Checkout session:\n\n{e}")
