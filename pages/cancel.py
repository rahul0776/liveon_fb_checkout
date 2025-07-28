import streamlit as st

st.set_page_config(page_title="Payment Cancelled", page_icon="❌")

st.title("❌ Payment Cancelled")
st.markdown("Your payment was not completed. No worries, you can try again anytime!")

# Add a Retry button
if st.button("🔄 Try Again"):
    st.switch_page("pages/FB_Backup.py") 
