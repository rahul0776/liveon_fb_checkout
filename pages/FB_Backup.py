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
    # 1. If already in memory, done
    if all(k in st.session_state for k in ["fb_id", "fb_name", "fb_token"]):
        return

    # 2. If 'cache' param exists in URL, try to load that SPECIFIC file
    qp = st.query_params
    token_hash = qp.get("cache")
    if isinstance(token_hash, list): token_hash = token_hash[0]

    if not token_hash:
        return

    cache_dir = Path("cache")
    if not cache_dir.exists():
        return
        
    cand = cache_dir / f"backup_cache_{token_hash}.json"
    if cand.exists():
        try:
            with open(cand, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if "fb_token" in cached:
                st.session_state["fb_token"] = cached.get("fb_token")
                st.session_state["fb_id"] = cached.get("fb_id") or cached.get("latest_backup", {}).get("user_id")
                st.session_state["fb_name"] = cached.get("fb_name") or cached.get("latest_backup", {}).get("name")
        except Exception:
            pass

# ----------------- Bootstrap -----------------
restore_session()

# Early Azure Blob session restore (in case local cache was wiped by Streamlit
# Cloud container rotation, e.g. after the Stripe redirect).
if "fb_token" not in st.session_state:
    _cache_hash_fb = None
    try:
        _cache_hash_fb = st.query_params.get("cache")
    except Exception:
        pass
    if _cache_hash_fb:
        try:
            import time as _time_fb
            from azure.storage.blob import BlobServiceClient as _BSC_fb
            _conn_fb = st.secrets.get("AZURE_CONNECTION_STRING") or os.environ.get("AZURE_CONNECTION_STRING")
            if _conn_fb:
                _bc_fb = _BSC_fb.from_connection_string(_conn_fb) \
                    .get_container_client("backup") \
                    .get_blob_client(f"_sessions/{_cache_hash_fb}.json")
                if _bc_fb.exists():
                    _d_fb = json.loads(_bc_fb.download_blob().readall().decode("utf-8"))
                    if (int(_time_fb.time()) - int(_d_fb.get("ts", 0)) <= 7 * 86400) and _d_fb.get("fb_token"):
                        st.session_state["fb_token"] = _d_fb["fb_token"]
                        if _d_fb.get("fb_id"):
                            st.session_state["fb_id"] = _d_fb["fb_id"]
                        if _d_fb.get("fb_name"):
                            st.session_state["fb_name"] = _d_fb["fb_name"]
        except Exception:
            pass

if "fb_token" not in st.session_state:
    st.warning("🔐 Please login with Facebook first.")
    st.stop()

# Stripe config
STRIPE_SECRET_KEY = _get_secret("STRIPE_SECRET_KEY")
RAW_PRICE_OR_PRODUCT_ID = _get_secret("STRIPE_PRICE_ID", "price_1234567890placeholder")
SUCCESS_URL = _get_secret("STRIPE_SUCCESS_URL", "https://liveonfb.streamlit.app/FB_Backup")
CANCEL_URL  = _get_secret("STRIPE_CANCEL_URL",  "https://liveonfb.streamlit.app/Projects")

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

# ── Azure Blob session persistence ──────────────────────────
# Streamlit Cloud's local fs cache is ephemeral. We persist fb_token to Blob
# so post-Stripe-payment pages can always restore the session.
import time as _time_mod
def _save_session_to_blob():
    token = st.session_state.get("fb_token")
    if not token:
        return
    try:
        th = hashlib.md5(token.encode()).hexdigest()
        payload = {
            "fb_token": token,
            "fb_id": st.session_state.get("fb_id") or "",
            "fb_name": st.session_state.get("fb_name") or "",
            "selected_backup": st.session_state.get("selected_backup") or "",
            "ts": int(_time_mod.time()),
        }
        _container.get_blob_client(f"_sessions/{th}.json").upload_blob(
            json.dumps(payload).encode("utf-8"), overwrite=True
        )
    except Exception:
        pass

def _backup_prefix_from_blob_path(blob_path: str) -> str:
    """
    '12345/John_20250101_120000/posts+cap.json' -> '12345/John_20250101_120000'
    '12345/John_20250101_120000/some.zip'       -> '12345/John_20250101_120000'
    """
    return str(blob_path).rsplit("/", 1)[0].strip("/")

def _stripe_pick(obj, key, default=None):
    """
    Safely pull a value from a Stripe StripeObject, plain dict, or attr-style object.
    Avoids .get() because newer stripe-python's StripeObject routes .get through
    __getattr__ and treats it as a key lookup (raises AttributeError: get).
    """
    if obj is None:
        return default
    try:
        val = obj[key]
        return val if val is not None else default
    except (KeyError, TypeError, IndexError):
        pass
    try:
        val = getattr(obj, key, default)
        return val if val is not None else default
    except Exception:
        return default


def _write_entitlements(prefix: str, session) -> None:
    """
    Write (or update) entitlements.json in the given backup prefix and
    drop tiny marker files for memories & download.
    """
    md = _stripe_pick(session, "metadata") or {}
    ent = {
        "memories": True,
        "download": True,
        "paid": True,
        "paid_at": datetime.now(timezone.utc).isoformat(),
        "checkout_id": _stripe_pick(session, "id"),
        "amount": (_stripe_pick(session, "amount_total") or 0) / 100.0,
        "currency": _stripe_pick(session, "currency"),
        "fb_id": _stripe_pick(md, "fb_id"),
        "fb_name": _stripe_pick(md, "fb_name"),
    }
    bc = _container.get_blob_client(f"{prefix}/entitlements.json")
    bc.upload_blob(json.dumps(ent, ensure_ascii=False).encode("utf-8"), overwrite=True)

    # markers (zero-byte files are fine)
    _container.get_blob_client(f"{prefix}/.paid.memories").upload_blob(b"", overwrite=True)
    _container.get_blob_client(f"{prefix}/.paid.download").upload_blob(b"", overwrite=True)


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
            # Use default price if set (use subscript — StripeObject.get() is broken)
            default_price = prod["default_price"] if "default_price" in prod else None
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
import traceback as _tb

try:
    qp = st.query_params
    # st.query_params supports .get() (it's not a StripeObject), but be defensive
    try:
        session_id = qp.get("session_id")
    except Exception:
        session_id = qp["session_id"] if "session_id" in qp else None
    if isinstance(session_id, list):
        session_id = session_id[0]

    if BILLING_READY and session_id:
        try:
            sess = stripe.checkout.Session.retrieve(session_id)
        except Exception as e:
            st.error(f"Stripe API error retrieving session: {type(e).__name__}: {e}")
            st.stop()

        pay_status = (_stripe_pick(sess, "payment_status") or "").lower()

        if pay_status == "paid":
            md = _stripe_pick(sess, "metadata") or {}
            try:
                qp_blob = qp.get("blob")
            except Exception:
                qp_blob = qp["blob"] if "blob" in qp else None
            blob_path = _stripe_pick(md, "blob") or qp_blob or ""
            backup_prefix = (
                _stripe_pick(md, "backup_prefix")
                or (_backup_prefix_from_blob_path(blob_path) if blob_path else "")
            )

            if not backup_prefix:
                st.error("Paid, but couldn't resolve the backup prefix. Contact support.")
            else:
                try:
                    _write_entitlements(backup_prefix, sess)
                except Exception as e:
                    st.error(f"Failed to write entitlements: {type(e).__name__}: {e}")
                    st.code(_tb.format_exc())
                    st.stop()

                # Carry cache param over via session_state so Projects.py can restore session
                try:
                    cache = qp.get("cache")
                except Exception:
                    cache = qp["cache"] if "cache" in qp else None
                if isinstance(cache, list):
                    cache = cache[0]
                if cache:
                    st.session_state["_pending_cache"] = cache

                st.session_state["selected_backup"] = backup_prefix
                st.session_state["payment_success"] = True
                st.switch_page("pages/Projects.py")
        else:
            if pay_status == "unpaid":
                st.warning("Payment was not completed. Please try again or contact support if you were charged.")
            elif pay_status == "no_payment_required":
                st.info("No payment was required for this session.")
            elif pay_status:
                st.warning(f"Payment status is '{pay_status}'. Please contact support if you were charged.")
except Exception as e:
    # Ignore Streamlit's internal page-switch exception so it doesn't look like a real error
    _etype = type(e).__name__
    if _etype in ("RerunException", "RerunData", "StopException"):
        raise
    st.warning(f"Post-payment handler error: {_etype}: {e}")
    st.code(_tb.format_exc())

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
        # Persist session to Blob so the post-payment redirect can restore it
        # (Streamlit Cloud's local cache may not survive the round-trip).
        _save_session_to_blob()
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
