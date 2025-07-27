import streamlit as st
import time

st.set_page_config(page_title="Payment Success", page_icon="✅")

st.title("✅ Payment Successful")
st.markdown("Thank you for your purchase! Your order has been processed.")

# Countdown from 5 to 1
for i in range(5, 0, -1):
    st.markdown(f"🔄 Redirecting to Memories in **{i}** seconds...")
    time.sleep(1)

# Redirect to FbMemories page
st.switch_page("pages/FbMemories.py")
