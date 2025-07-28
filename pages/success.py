import streamlit as st
import time, json, hashlib
from pathlib import Path

st.set_page_config(page_title="Payment Success", page_icon="✅")

st.title("✅ Payment Successful")
st.markdown("Thank you for your purchase! Your order has been processed.")

# ✅ Add image below the message
st.image("media/success_banner.png", use_container_width=True)

# ✅ Save fb_token to per-user cache (if available)
if "fb_token" in st.session_state:
    cache_dir = Path("cache")
    cache_dir.mkdir(exist_ok=True)
    token_hash = hashlib.md5(st.session_state["fb_token"].encode()).hexdigest()
    cache_file = cache_dir / f"backup_cache_{token_hash}.json"

    with open(cache_file, "w") as f:
        json.dump({"fb_token": st.session_state["fb_token"]}, f)

# ✅ Add a button for instant redirect
if st.button("➡️ Go to Memories Now"):
    st.switch_page("pages/FbMemories.py")

# ✅ Countdown with placeholder
placeholder = st.empty()

for i in range(15, 0, -1):
    placeholder.markdown(f"🔄 Redirecting to Memories in **{i}** seconds...")
    time.sleep(1)

st.switch_page("pages/FbMemories.py")
