# ======================
# FILE: FB_Backup.py
# ======================
import os, json
from pathlib import Path
import streamlit as st
import stripe
from urllib.parse import urlencode
import hashlib
from azure.storage.blob import BlobServiceClient
from datetime import datetime, timezone
# ----------------- MUST BE FIRST -----------------
st.set_page_config(
    page_title="LiveOn · Facebook Backup",
    page_icon="💾",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Optional: your global theme (won't change behavior)
try:
    from utils.theme import inject_global_styles
except ModuleNotFoundError:
    inject_global_styles = None
if inject_global_styles:
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
RAW_PRICE_OR_PRODUCT_ID = _get_secret("STRIPE_PRICE_ID", "price_1234567890placeholder")
SUCCESS_URL = _get_secret("STRIPE_SUCCESS_URL", "http://localhost:8501/Projects")
CANCEL_URL  = _get_secret("STRIPE_CANCEL_URL",  "http://localhost:8501/cancel")

BILLING_READY = bool(STRIPE_SECRET_KEY)
if BILLING_READY:
    stripe.api_key = STRIPE_SECRET_KEY  # type: ignore[arg-type]

# ---- Azure Blob (to store entitlements) ----
AZURE_CONN = _get_secret("AZURE_CONNECTION_STRING")
if not AZURE_CONN:
    st.error("Missing AZURE_CONNECTION_STRING in Secrets.")
    st.stop()

_blob = BlobServiceClient.from_connection_string(AZURE_CONN)
_container = _blob.get_container_client("backup")

def _backup_prefix_from_blob_path(blob_path: str) -> str:
    """
    '12345/John_20250101_120000/posts+cap.json' -> '12345/John_20250101_120000'
    '12345/John_20250101_120000/some.zip'       -> '12345/John_20250101_120000'
    """
    return str(blob_path).rsplit("/", 1)[0].strip("/")

def _write_entitlements(prefix: str, session: dict) -> None:
    """
    Write (or update) entitlements.json in the given backup prefix and
    drop tiny marker files for memories & download.
    """
    ent = {
        "memories": True,
        "download": True,
        "paid": True,
        "paid_at": datetime.now(timezone.utc).isoformat(),
        "checkout_id": session.get("id"),
        "amount": (session.get("amount_total") or 0) / 100.0,
        "currency": session.get("currency"),
        "fb_id": (session.get("metadata") or {}).get("fb_id"),
        "fb_name": (session.get("metadata") or {}).get("fb_name"),
    }
    bc = _container.get_blob_client(f"{prefix}/entitlements.json")
    bc.upload_blob(json.dumps(ent, ensure_ascii=False).encode("utf-8"), overwrite=True)

    # markers (zero-byte files are fine)
    _container.get_blob_client(f"{prefix}/.paid.memories").upload_blob(b"", overwrite=True)
    _container.get_blob_client(f"{prefix}/.paid.download").upload_blob(b"", overwrite=True)  # 👈 NEW


# --- NEW: accept prod_ or price_ and resolve to a Price ID
def _resolve_price_id(price_or_prod: str | None) -> str | None:
    """Return a Price ID for either a Price or Product input; None if not resolvable."""
    if not price_or_prod:
        return None
    if price_or_prod.startswith("price_"):
        return price_or_prod
    if price_or_prod.startswith("prod_"):
        try:
            prod = stripe.Product.retrieve(price_or_prod)
            # Use default price if set
            default_price = prod.get("default_price")
            if default_price:
                return default_price
            # Otherwise, take the first active price
            prices = stripe.Price.list(product=price_or_prod, active=True, limit=1)
            if prices.data:
                return prices.data[0].id
            st.error("This Product has no active Prices in this Stripe mode (test/live).")
            return None
        except Exception as e:
            st.error(f"Could not resolve a Price for Product '{price_or_prod}': {e}")
            return None
    st.error("STRIPE_PRICE_ID must be a 'price_...' or 'prod_...' value.")
    return None

RESOLVED_PRICE_ID = _resolve_price_id(RAW_PRICE_OR_PRODUCT_ID)

pending = st.session_state.get("pending_download")  # set in Projects.py
display_name = (pending or {}).get("file_name") or "backup.zip"
if not display_name.lower().endswith(".zip"):
    display_name = display_name.rsplit(".", 1)[0] + ".zip"

# compute per-user cache hash so Projects.py can restore the session by ?cache=
token = st.session_state.get("fb_token", "")
token_hash = hashlib.md5(token.encode()).hexdigest() if token else ""

success_url_for_item = SUCCESS_URL
if pending and isinstance(pending, dict) and pending.get("blob_path"):
    base_params = {
        "blob": pending["blob_path"],
        "name": display_name,
    }
    if token_hash:
        base_params["cache"] = token_hash
    sep0 = '&' if '?' in SUCCESS_URL else '?'
    success_url_for_item = f"{SUCCESS_URL}{sep0}{urlencode(base_params)}"
    st.caption(f"After payment, your download of **{display_name}** will start automatically.")

# ---- Success return handler (runs when Stripe redirects back with ?session_id=...) ----
try:
    qp = st.query_params
    session_id = qp.get("session_id")
    if isinstance(session_id, list):
        session_id = session_id[0]

    if BILLING_READY and session_id:
        try:
            sess = stripe.checkout.Session.retrieve(session_id)
        except stripe.error.StripeError as e:
            st.error(f"Stripe API error: {e}")
            st.stop()
        except Exception as e:
            st.error(f"Unexpected error retrieving payment session: {e}")
            st.stop()
        
        if (sess.get("payment_status") or "").lower() == "paid":
            md = sess.get("metadata") or {}
            blob_path = md.get("blob") or qp.get("blob") or ""
            backup_prefix = md.get("backup_prefix") or (_backup_prefix_from_blob_path(blob_path) if blob_path else "")

            if not backup_prefix:
                st.error("Paid, but couldn't resolve the backup prefix. Contact support.")
            else:
                _write_entitlements(backup_prefix, sess)
                
                # Redirect to Projects.py instead of showing success message here
                st.session_state["selected_backup"] = backup_prefix
                st.session_state["payment_success"] = True
                st.switch_page("pages/Projects.py")

                # keep the cache token alive as we go back to Projects
                cache = qp.get("cache")
                if isinstance(cache, list):
                    cache = cache[0]

                # Prefer a link (ensures ?cache=… is preserved). If switch_page works in your env, it’s fine too.
                proj_url = f"/Projects?cache={cache or ''}"
                st.link_button("📘 Open Projects", proj_url)
                st.stop()
        else:
            payment_status = sess.get("payment_status", "unknown")
            if payment_status == "unpaid":
                st.warning("Payment was not completed. Please try again or contact support if you were charged.")
            elif payment_status == "no_payment_required":
                st.info("No payment was required for this session.")
            else:
                st.warning(f"Payment status is '{payment_status}'. Please contact support if you were charged.")
except Exception as e:
    st.warning(f"Post-payment handler error: {e}")

# ----------------- Page CSS (Minedco look) -----------------
st.markdown("""
<style>
:root{ --navy:#0F253D; --navy-2:#12304B; --ink:#1A2B3A; --bg:#F6FAFF; --gold:#F6C35D; --muted:#5E738A; --line:#E8EEF5; }
html,body,.stApp{ background:var(--bg); color:var(--ink); font-family:Inter,system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial }
.page{ display:flex; flex-direction:column; align-items:center; gap:14px; margin-top:8px }
.hero-title{ font-weight:800; color:var(--navy); text-align:center; margin:0 }
.hero-sub{ text-align:center; margin-top:4px; color:var(--muted) }
.card{ background:#fff; padding:18px 18px 22px; border-radius:14px; border:1px solid var(--line); box-shadow:0 6px 16px rgba(0,0,0,.06); text-align:center; width:360px; }
.center-image img{ display:block; margin:0 auto; width:260px; border-radius:10px; border:1px solid var(--line); }
.stButton>button{ width:100%; background:var(--gold); color:var(--navy-2)!important; font-size:16px; padding:12px 14px; border-radius:10px; font-weight:800; border:none; box-shadow:0 4px 12px rgba(246,195,93,.28); transition:transform .12s ease, filter .12s ease; }
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
    st.info("⚠️ Stripe is not configured (missing STRIPE_SECRET_KEY). The checkout button is disabled.\n\nAdd STRIPE_SECRET_KEY to Streamlit Secrets. You can also set STRIPE_PRICE_ID / STRIPE_SUCCESS_URL / STRIPE_CANCEL_URL.")

# Disable the button if we could not resolve a valid Price
price_is_placeholder = (not RESOLVED_PRICE_ID) or RESOLVED_PRICE_ID.endswith("placeholder")

if st.button("💳 Buy Now for $9.99", disabled=(not BILLING_READY or price_is_placeholder)):
    try:
        # add session_id to success url (works whether or not there are existing params)
        sep = '&' if '?' in success_url_for_item else '?'
        success_url_with_session = f"{success_url_for_item}{sep}session_id={{CHECKOUT_SESSION_ID}}"

        try:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{"price": RESOLVED_PRICE_ID, "quantity": 1}],
                mode="payment",
                success_url=success_url_with_session,
                cancel_url=CANCEL_URL,
                allow_promotion_codes=True,
                metadata={
                    "fb_id": st.session_state.get("fb_id", ""),
                    "fb_name": st.session_state.get("fb_name", ""),
                    "blob": (pending or {}).get("blob_path", ""),
                    "name": (pending or {}).get("file_name", ""),
                    "backup_prefix": _backup_prefix_from_blob_path((pending or {}).get("blob_path", "")),  # 👈 add this
                },
                customer_email=st.session_state.get("fb_email")
            )
        except stripe.error.StripeError as e:
            st.error(f"Stripe checkout error: {e}")
            st.stop()
        except Exception as e:
            st.error(f"Unexpected error creating checkout session: {e}")
            st.stop()
        st.success("✅ Checkout session created!")
        st.link_button("👉 Continue to Secure Checkout", session.url)
        st.session_state.pop("pending_download", None)
        st.caption("You’ll be taken to Stripe to complete your payment.")
    except Exception as e:
        st.error(f"❌ Error creating Stripe Checkout session:\n\n{e}")

if price_is_placeholder and BILLING_READY:
    st.caption("Set a real STRIPE_PRICE_ID (price_… or prod_… with an active price) in Secrets to enable the button.")

st.markdown("</div></div>", unsafe_allow_html=True)
