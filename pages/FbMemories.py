#Khushi's version
import streamlit as st  # type: ignore

# ── PAGE CONFIG (MUST BE FIRST) ────────────────────────────────────────────────
st.set_page_config(page_title="🧠 Facebook Memories", layout="wide", initial_sidebar_state="collapsed")

import requests
import json
import re
from datetime import datetime, timedelta
import os
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from urllib.parse import quote, unquote, urlparse, urlunparse
from azure.storage.blob import BlobServiceClient  # type: ignore
import hashlib
import time 
from io import BytesIO
# TOP OF FILE, with your other imports
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from uuid import uuid4
from pathlib import Path
from textwrap import wrap

try:
    from PIL import Image as PILImage
    _HAVE_PIL = True
except Exception:
    _HAVE_PIL = False

# ---- Debug guard to catch & suppress accidental "None" renders ----
import functools, inspect

def _is_junk_label(x):
    """
    Treat None, 'none/null/undefined', empty strings, and *numeric zeros* as junk.
    This prevents lone '0' from ever rendering as a caption/markdown line.
    """
    try:
        if x is None:
            return True
        if isinstance(x, (int, float)):
            return float(x) == 0.0
        s = str(x).strip()
        if not s:
            return True
        s_low = s.lower()
        if s_low in {"none", "null", "undefined"}:
            return True
        # '0', '00', '0.0' etc…
        if s.replace(".", "", 1).isdigit():
            try:
                return float(s) == 0.0
            except Exception:
                return False
        return False
    except Exception:
        return False

def _guard(fn_name):
    orig = getattr(st, fn_name)
    @functools.wraps(orig)
    def wrapped(*args, **kwargs):
        if args and _is_junk_label(args[0]):
            fr = inspect.stack()[1]
            where = f"{fr.filename.split('/')[-1]}:{fr.lineno}"
            st.sidebar.warning(f"Suppressed junk value passed to st.{fn_name} at {where}")
            return
        return orig(*args, **kwargs)
    return wrapped

for _fn in ("write", "text", "caption", "markdown", "code"):
    setattr(st, _fn, _guard(_fn))

# -------------------------------------------------------------------

from pages.utils.theme import inject_global_styles

inject_global_styles()
st.markdown("""
<style>
/* Force collapse sidebar on wide screens if needed */
[data-testid="stSidebar"][aria-expanded="true"] {
    display: none;
}
[data-testid="stSidebar"][aria-expanded="false"] {
    display: block;
}
:root{
  --navy-900:#0F253D;     /* deep background */
  --navy-800:#143150;
  --navy-700:#1E3A5F;     /* headers / hover */
  --navy-500:#2F5A83;     /* accents */
  --gold:#F6C35D;         /* brand accent */
  --text:#F3F6FA;         /* off-white */
  --muted:#B9C6D6;        /* secondary text */
  --card:#112A45;         /* card bg */
  --line:rgba(255,255,255,.14);
}
/* Page */
html, body, .stApp{
  background: linear-gradient(180deg, var(--navy-900) 0%, var(--navy-800) 55%, var(--navy-700) 100%);
  color: var(--text);
  font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
/* Headings */
h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3{
  color: var(--text) !important;
  letter-spacing:.25px;
  text-align:center;
}
/* Header brand row (logo + title) */
.header-container{
  display:flex; align-items:center; justify-content:center; gap:12px;
  margin: 8px 0 12px 0;
}
.header-container img{
  width:56px; height:auto; filter: drop-shadow(0 2px 8px rgba(0,0,0,.25));
}
.header-title{
  font-weight:800; font-size: 32px; line-height:1.05; letter-spacing:.2px;
}
.header-title .accent{ color: var(--gold); }
/* Hero card */
.hero-box{
  text-align:center; max-width:560px; margin: 6px auto 10px;
  padding: 2rem 2rem;
  background: rgba(255,255,255,.06);
  border: 1px solid var(--line);
  border-radius: 16px;
  box-shadow: 0 6px 16px rgba(0,0,0,.12);
}
.card{ box-shadow: 0 6px 16px rgba(0,0,0,.12); }
/* Primary CTA: style Streamlit buttons like gold CTA */
.stButton>button{
  background: var(--gold) !important;
  color: var(--navy-900) !important; font-weight:800 !important; font-size:17px !important;
  padding: 12px 24px !important; border-radius: 8px !important; border: none !important;
  box-shadow: 0 4px 14px rgba(246,195,93,.22) !important;
  transition: transform .15s ease, box-shadow .15s ease, filter .15s ease !important;
}
.stButton>button:hover{
  filter: brightness(.95);
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(246,195,93,.28) !important;
}
/* Subtext + alerts */
.subtext{ font-size:.95rem; margin-top:.9rem; color: var(--muted); }
div[data-testid="stAlert"]{ border:1px solid var(--line); background: rgba(255,255,255,.06); }
/* Navbar */
.navbar{
  display:flex; justify-content:space-between; align-items:center;
  padding: 1rem 2rem; background: rgba(255,255,255,.04);
  border-bottom: 1px solid var(--line);
  box-shadow: 0 2px 6px rgba(0,0,0,.12);
}
.navbar a{ color: var(--text); text-decoration:none; margin-left:1.2rem; }
.navbar a:hover{ color: var(--gold); }
/* Shared cards/grid/titles for this page */
.card{
  background: rgba(255,255,255,.06);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 18px;
  box-shadow: 0 10px 24px rgba(0,0,0,.18);
  margin-bottom: 18px;
}
.grid-3{ display:grid; grid-template-columns: repeat(3,1fr); gap:16px; }
@media (max-width: 1100px){ .grid-3{ grid-template-columns: repeat(2,1fr);} }
@media (max-width: 700px){ .grid-3{ grid-template-columns: 1fr; } }
.section-title{
  font-size: 1.25rem; font-weight: 800; margin: 22px 0 10px;
  text-align:left; color: var(--text);
}
.badge{ display:inline-block; padding:6px 12px; border-radius:999px;
  background: rgba(255,255,255,.08); color: var(--gold); font-weight:700; }
.muted{ color: var(--muted); }
/* --- Promo strip (small, non-dominant) --- */
.promo-wrap{
  max-width:1100px; margin:8px auto 18px;
  display:grid; grid-template-columns: 1fr 1.2fr; gap:18px;
}
@media (max-width: 900px){ .promo-wrap{ grid-template-columns: 1fr; } }

.promo-grid{ display:grid; grid-template-columns: repeat(2, 1fr); gap:16px; }
@media (max-width: 900px){ .promo-grid{ grid-template-columns: 1fr; } }

.promo-card{
  background: rgba(255,255,255,.06);
  border: 1px solid var(--line);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 6px 16px rgba(0,0,0,.15);
}
/* Promo tiles: show full image, keep aspect, avoid blur */
/* Promo tiles: large, crisp, and full-bleed */
.promo-card img{
  display:block;
  width:100% !important;
  height:220px !important;         /* larger uniform tiles */
  object-fit:cover !important;     /* fill without squish */
  border-bottom:1px solid var(--line);
  border-radius:12px 12px 0 0;
  image-rendering:-webkit-optimize-contrast;
}

.promo-card .caption{
  padding:8px 10px; font-weight:700; font-size:.9rem; color:var(--text);
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
}

.promo-copy{
  background: rgba(255,255,255,.06);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 16px 18px;
  box-shadow: 0 6px 16px rgba(0,0,0,.15);
}
.promo-copy .badge{ color: var(--gold); font-weight:800; }   
/* Scrapbook chapter title */
.chapter-title{
  display:inline-block;
  background:#fff8e6;
  color:#2a2a2a;
  font-weight:800;
  font-size:1.15rem;
  padding:10px 14px;
  border-radius:8px;
  box-shadow: 0 8px 18px rgba(0,0,0,.18);
  border: 1px solid rgba(0,0,0,.06);
  margin: 18px 0 10px;
  position: relative;
}
.chapter-title::before{
  content:"";
  position:absolute;
  width:90px; height:18px;
  top:-10px; left:12px;
  background: linear-gradient(90deg, #f2e5c2, #efe2c0);
  transform: rotate(-2deg);
  box-shadow: 0 4px 8px rgba(0,0,0,.12);
  opacity:.9;
  border-radius:4px;
}       
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Hide sidebar and its toggle completely */
section[data-testid="stSidebar"] { display: none !important; }
button[data-testid="stSidebarCollapsedControl"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.chapter-title{
  background: transparent !important;
  color: var(--text) !important;
  border: 1px dashed var(--line) !important;
  box-shadow: none !important;
}
.chapter-title::before{ display:none !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
:root{
  --navy-900:#0b1220;
  --navy-800:#0e172a;
  --navy-700:#111827;
  --card:#0f172a;
  --text:#e5e7eb;
  --muted:#9ca3af;
  --line:rgba(255,255,255,.10);
  /* repurpose 'gold' as primary accent */
  --gold:#6366F1; /* indigo-500 */
}
.stButton>button{
  background: var(--gold) !important;
  color: #fff !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.brandbar{
  max-width:1100px;
  margin:6px auto 6px;
  display:flex;
  align-items:center;
  gap:10px;
}
.brandbar img{
  width:44px; height:auto;
  filter: drop-shadow(0 2px 8px rgba(0,0,0,.25));
}
.brandbar .wordmark{
  font-weight:900;
  font-size:26px;
  letter-spacing:.2px;
  color: var(--text);
}
.brandbar .wordmark b{ color: var(--gold); }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Patrick+Hand&family=Playfair+Display:ital,wght@0,700;1,400&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* ── Sidebar: fully hidden ──────────────────────────────────── */
section[data-testid="stSidebar"],
[data-testid="stSidebarNav"],
[data-testid="collapsedControl"],
button[data-testid="stSidebarCollapsedControl"],
div[data-testid="stDecoration"]{ display:none !important; }

/* ── Page-wide reset ───────────────────────────────────────── */
html,body,.stApp{
  background: linear-gradient(160deg,#0a1628 0%,#0f1f3d 45%,#131c33 100%) !important;
  font-family:'Inter',system-ui,sans-serif;
  color:#e8edf5;
}
/* remove default top padding Streamlit adds */
.block-container{ padding-top:0 !important; max-width:1160px; }

/* ── Branded page header ─────────────────────────────────── */
.mem-header{
  text-align:center;
  padding:48px 20px 32px;
}
.mem-header .eyebrow{
  font-size:11px; font-weight:600; letter-spacing:3px; text-transform:uppercase;
  color:#C4923A; margin-bottom:10px;
}
.mem-header h1{
  font-family:'Playfair Display',serif;
  font-size:clamp(2.2rem,5vw,3.4rem);
  font-weight:700;
  color:#f0f4fa !important;
  line-height:1.15;
  margin:0 0 12px;
}
.mem-header h1 .gold{ color:#C4923A; font-style:italic; }
.mem-header .sub{
  font-size:1.05rem; color:#8a99b8; max-width:520px; margin:0 auto;
}

/* ── Pre-generate CTA card ───────────────────────────────── */
.gen-card{
  max-width:640px; margin:32px auto 0;
  background:rgba(255,255,255,.04);
  border:1px solid rgba(196,146,58,.25);
  border-radius:20px;
  padding:40px 36px 36px;
  text-align:center;
  box-shadow:0 20px 60px rgba(0,0,0,.3);
}
.gen-card .icon{ font-size:3rem; margin-bottom:14px; display:block; }
.gen-card h2{
  font-family:'Playfair Display',serif;
  font-size:1.6rem; color:#f0f4fa;
  margin:0 0 10px;
}
.gen-card p{ color:#8a99b8; font-size:.97rem; margin:0 0 28px; line-height:1.6; }
.gen-card .stat-row{
  display:flex; justify-content:center; gap:32px; margin-bottom:28px;
}
.gen-card .stat{ text-align:center; }
.gen-card .stat .val{
  font-size:1.9rem; font-weight:700; color:#C4923A; line-height:1;
}
.gen-card .stat .lbl{ font-size:.78rem; color:#6b7a96; text-transform:uppercase; letter-spacing:1px; }
.gen-card .steps{
  display:flex; justify-content:center; gap:6px;
  font-size:.8rem; color:#6b7a96; margin-bottom:28px;
}
.gen-card .steps span{
  background:rgba(255,255,255,.06); border-radius:20px; padding:4px 10px;
}

/* ── Memory Snapshot card ─────────────────────────────────── */
.snapshot-wrap{ position:relative; max-width:900px; margin:0 auto 24px; }
.snapshot-label{
  display:flex; align-items:center; gap:8px;
  font-size:.75rem; font-weight:600; letter-spacing:2.5px; text-transform:uppercase;
  color:#C4923A; margin-bottom:10px;
}
.snapshot-label::before,.snapshot-label::after{
  content:''; flex:1; height:1px;
  background:linear-gradient(90deg,transparent,rgba(196,146,58,.35));
}
.snapshot-label::after{
  background:linear-gradient(90deg,rgba(196,146,58,.35),transparent);
}
.snapshot-card{
  background:linear-gradient(135deg,rgba(196,146,58,.07) 0%,rgba(255,255,255,.03) 100%);
  border:1px solid rgba(196,146,58,.22);
  border-radius:16px;
  padding:32px 36px;
  position:relative;
  overflow:hidden;
}
.snapshot-card::before{
  content:'"';
  position:absolute; top:-10px; left:20px;
  font-family:'Playfair Display',serif;
  font-size:120px; color:rgba(196,146,58,.10); line-height:1;
  pointer-events:none;
}
.snapshot-card p{
  font-family:'Playfair Display',serif;
  font-style:italic; font-size:1.05rem;
  line-height:1.85; color:#c8d4e8;
  margin:0; position:relative; z-index:1;
}

/* ── Coverage bar ─────────────────────────────────────────── */
.coverage-wrap{
  max-width:900px; margin:20px auto 28px;
  background:rgba(255,255,255,.04);
  border:1px solid rgba(255,255,255,.08);
  border-radius:12px;
  padding:16px 22px;
  display:flex; align-items:center; gap:18px;
}
.coverage-wrap .icon{ font-size:1.4rem; flex-shrink:0; }
.coverage-wrap .text{ flex:1; }
.coverage-wrap .text .title{
  font-size:.8rem; font-weight:600; letter-spacing:1px; text-transform:uppercase;
  color:#8a99b8; margin-bottom:5px;
}
.coverage-track{
  height:6px; border-radius:3px;
  background:rgba(255,255,255,.1);
  overflow:hidden; margin-top:4px;
}
.coverage-fill{
  height:100%; border-radius:3px;
  background:linear-gradient(90deg,#C4923A,#e8b84b);
  transition:width .6s ease;
}
.coverage-count{
  font-size:1.3rem; font-weight:700; color:#C4923A; flex-shrink:0;
}

/* ── Heritage card ────────────────────────────────────────── */
.heritage-card{
  max-width:900px; margin:0 auto 24px;
  background:rgba(255,255,255,.03);
  border:1px solid rgba(255,255,255,.09);
  border-radius:14px;
  padding:20px 26px;
  display:grid; grid-template-columns:auto 1fr;
  gap:14px; align-items:start;
}
.heritage-card .icon-col{ font-size:2rem; }
.heritage-card .label{
  font-size:.72rem; font-weight:600; letter-spacing:1.5px; text-transform:uppercase;
  color:#C4923A; margin-bottom:6px;
}
.heritage-card .name{ font-size:1.2rem; font-weight:700; color:#f0f4fa; margin-bottom:6px; }
.heritage-card .detail{ font-size:.88rem; color:#8a99b8; line-height:1.6; }
.heritage-card .detail strong{ color:#b8c6d9; }

/* ── TOC / chapter pills section ─────────────────────────── */
.toc-section{ max-width:900px; margin:0 auto 32px; }
.toc-label{
  display:flex; align-items:center; gap:10px;
  font-size:.75rem; font-weight:600; letter-spacing:2.5px; text-transform:uppercase;
  color:#8a99b8; margin-bottom:16px;
}
.toc-label::after{ content:''; flex:1; height:1px; background:rgba(255,255,255,.08); }
.chapter-pills{
  display:flex; flex-wrap:wrap; gap:10px;
}
.chap-pill{
  display:inline-flex; align-items:center; gap:6px;
  background:rgba(255,255,255,.05);
  border:1px solid rgba(196,146,58,.18);
  border-radius:999px;
  padding:6px 16px;
  font-size:.88rem; color:#c8d4e8;
  transition:background .2s,border-color .2s;
}
.chap-pill .num{
  font-size:.72rem; font-weight:700; color:#C4923A;
  background:rgba(196,146,58,.15);
  border-radius:50%; width:18px; height:18px;
  display:flex; align-items:center; justify-content:center;
}

/* ── Chapter section divider ──────────────────────────────── */
.chapter-divider{
  max-width:1100px; margin:48px auto 20px;
  display:flex; align-items:center; gap:20px;
}
.chap-num-badge{
  flex-shrink:0;
  width:52px; height:52px; border-radius:50%;
  background:linear-gradient(135deg,#C4923A,#e8b84b);
  display:flex; align-items:center; justify-content:center;
  font-size:.9rem; font-weight:800; color:#0a1628;
  box-shadow:0 4px 16px rgba(196,146,58,.3);
}
.chap-title-text{
  font-family:'Playfair Display',serif;
  font-size:1.55rem; font-weight:700; color:#f0f4fa;
}
.chap-rule{
  flex:1; height:1px;
  background:linear-gradient(90deg,rgba(196,146,58,.35),transparent);
}

/* ── Photo grid card ──────────────────────────────────────── */
.photo-grid-wrap{
  max-width:1100px; margin:0 auto 12px;
  background:rgba(255,255,255,.025);
  border:1px solid rgba(255,255,255,.07);
  border-radius:16px;
  padding:20px;
}

/* ── Download CTA bar ─────────────────────────────────────── */
.dl-bar{
  max-width:900px; margin:40px auto 20px;
  background:linear-gradient(135deg,rgba(196,146,58,.12) 0%,rgba(196,146,58,.04) 100%);
  border:1px solid rgba(196,146,58,.3);
  border-radius:16px;
  padding:28px 32px;
  display:flex; align-items:center; gap:24px;
}
.dl-bar .dl-text h3{
  font-family:'Playfair Display',serif;
  font-size:1.25rem; color:#f0f4fa; margin:0 0 4px;
  text-align:left !important;
}
.dl-bar .dl-text p{ font-size:.88rem; color:#8a99b8; margin:0; }
.dl-bar .dl-icon{ font-size:2.4rem; flex-shrink:0; }
/* Streamlit download button inside bar */
.dl-bar + div .stDownloadButton > button,
.stDownloadButton > button{
  background:linear-gradient(135deg,#C4923A 0%,#e8b84b 100%) !important;
  color:#0a1628 !important;
  font-weight:800 !important;
  font-size:15px !important;
  border-radius:10px !important;
  border:none !important;
  padding:12px 28px !important;
  box-shadow:0 6px 24px rgba(196,146,58,.35) !important;
}

/* ── Replace button ───────────────────────────────────────── */
.stButton>button{
  background:rgba(255,255,255,.06) !important;
  color:#c8d4e8 !important;
  border:1px solid rgba(255,255,255,.12) !important;
  border-radius:8px !important;
  font-size:12px !important;
  font-weight:500 !important;
  padding:6px 12px !important;
  box-shadow:none !important;
}
.stButton>button:hover{
  background:rgba(255,255,255,.1) !important;
  border-color:rgba(196,146,58,.3) !important;
}

/* ── Streamlit misc overrides ──────────────────────────────── */
div[data-testid="stAlert"]{
  background:rgba(255,255,255,.04) !important;
  border:1px solid rgba(255,255,255,.09) !important;
  border-radius:10px !important;
}
.stCaption{ display:none; }
div[data-testid="stExpander"]{ display:none; }
</style>
""", unsafe_allow_html=True)

def make_button_key(prefix, *parts):
    raw = prefix + "|" + "|".join(str(p) for p in parts)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def generate_unique_key(*args):
    """Generate a unique key using hash of arguments and timestamp"""
    base = "_".join(str(arg) for arg in args) + f"_{time.time_ns()}"
    return hashlib.md5(base.encode('utf-8')).hexdigest()

def stable_uuid_suffix(chap: str, post_idx: int, img_idx: int, img_url: str) -> str:
    """Return a stable UUID suffix per (chapter, post, image, url)."""
    k = f"{chap}|{post_idx}|{img_idx}|{normalize_url(img_url)}"
    store = st.session_state.setdefault("_uuid_for_keys", {})
    if k not in store:
        store[k] = uuid4().hex[:8]  # short, readable, and stable after first assignment
    return store[k]

def _ours_blob_path(u: str) -> str | None:
    """
    If u is our Azure HTTPS URL or a raw blob-path, return the blob-path.
    Else return None.
    """
    if not isinstance(u, str) or not u.strip():
        return None
    u = u.strip()
    # raw blob-like "folder/images/x.jpg"
    if ("/" in u) and (not u.startswith("http")) and (not u.lower().startswith("app-assets/")):
        return u
    # https://<account>.blob.core.windows.net/backup/<blob_path>[?...]  -> <blob_path>
    return _to_blob_path_if_ours_https(u)

def _prefer_azure(images: list[str]) -> list[str]:
    """
    If any Azure blobs exist in `images`, return ONLY those (as blob-paths).
    Otherwise return the original list (non-empty items only).
    """
    azure_paths, others = [], []
    for s in images or []:
        if not _is_displayable_image_ref(s):
            continue
        bp = _ours_blob_path(s)
        if bp:
            azure_paths.append(bp)          # store as blob paths
        else:
            others.append(s)
    return azure_paths if azure_paths else others

def make_safe_key(chap, idx, img_url):
    """Generate a unique and safe Streamlit key using a hash."""
    base = f"{chap}_{idx}_{img_url}"
    return hashlib.md5(base.encode("utf-8")).hexdigest()

# 🆕 Normalize URLs to remove query params for deduplication
def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    clean = parsed._replace(query="", fragment="")
    return urlunparse(clean)

# Canonical key for duplicate detection (handles fbcdn size buckets & Azure)
def _canon_for_dedupe(u: str) -> str:
    s = (u or "").strip()
    if not s:
        return ""
    # Map our Azure HTTPS back to a stable blob path
    blob_path = _to_blob_path_if_ours_https(s)
    if blob_path:
        s = blob_path

    from urllib.parse import urlparse, urlunparse
    pu = urlparse(s)
    path = pu.path

    import re
    # Collapse fbcdn “size bucket” and crop segments
    path = re.sub(r"/(?:p|s)\d+x\d+/", "/", path)       # /p640x640/, /s720x720/
    path = re.sub(r"/c\d+\.\d+\.\d+\.\d+/", "/", path)  # /c0.0.720.720/
    path = re.sub(r"/(?:a|v)\d+/", "/", path)           # /a123/, /v123/

    # Normalize filename variant: *_n.jpg, *_o.jpg, *_b.jpg → .jpg
    path = re.sub(r"(_[a-z])\.(jpe?g|png|webp)$", r".\2", path, flags=re.I)

    # Normalize slashes & lowercase extension
    path = re.sub(r"/{2,}", "/", path)
    path = re.sub(r"\.(JPG|JPEG|PNG|WEBP)$", lambda m: "." + m.group(1).lower(), path)

    # Return just a stable, lowercase key (no query/fragment/host)
    return urlunparse(pu._replace(path=path, query="", fragment="", netloc="", scheme="")).lower()

def _cap(s) -> str:
    """Return a safe caption string; strip any 'None' artifacts and zero-width junk."""
    if not s:
        return ""
    s = str(s).strip()
    if not s or s.lower() in {"none", "null", "undefined"}:
        return ""
    if s.isdigit():                # <-- ADD THIS: drop digit-only captions like "0"
        return ""
    # strip trailing ‘🧠 None’ (various dashes/spaces) or standalone 🧠 with nothing useful
    s = re.sub(r"(?:\s*[–—-]\s*)?🧠\s*(?:none|null|undefined)?\s*$", "", s, flags=re.IGNORECASE).strip()
    # strip quoted empties
    s = re.sub(r"^[\"'“”]+|[\"'“”]+$", "", s).strip()
    return s

def _text(s) -> str:
    if s is None:
        return ""
    # treat numbers / number-like strings (e.g., "0", "1") as empty captions
    if isinstance(s, (int, float)):
        return "" if s == 0 else str(s).strip()
    s = str(s).strip()
    if s.lower() in {"none","null","undefined","na","n/a"}:
        return ""
    if s.isdigit() and len(s) <= 2:   # drop "0", "1", etc.
        return ""
    return s

def _is_numeric_only(x) -> bool:
    """True for 0, '0', ' 23 ', etc."""
    if x is None:
        return False
    if isinstance(x, (int, float)):
        return True
    s = str(x).strip()
    return s.isdigit()

def _safe_caption(c) -> str | None:
    """
    Normalize caption for st.image:
    - drop None / '', 'none', 'null', 'undefined'
    - drop numeric-only (0, '0', '12' etc.)
    - return a clean string otherwise (or None to suppress caption entirely)
    """
    if c is None:
        return None
    s = str(c).strip()
    if not s or s.lower() in {"none", "null", "undefined"}:
        return None
    if _is_numeric_only(s):
        return None
    return s

def _clean_images_list(values):
    """Remove empty / numeric-only entries from a post's images list."""
    out = []
    for v in (values or []):
        if v is None:
            continue
        s = str(v).strip()
        if not s or _is_numeric_only(s):
            continue
        out.append(v)
    return out

def compose_caption(message, context):
    m = _text(message)
    # extra guard in case something slips through
    if m.isdigit(): 
        m = ""
    c = _text(context)
    if m and c:
        return f"{m} — 🧠 {c}"
    return m or (f"🧠 {c}" if c else "📷")

def _craft_caption_via_function(message: str, context: str) -> str:
    # Pure local: stay compatible with older Function App (no /craft_caption route)
    return compose_caption(message, context)

# keep a session-scoped set of used captions to avoid dupes
def _unique_caption(raw: str, tries=2) -> str:
    used = st.session_state.setdefault("_used_captions", set())
    cap = _text(raw)
    if cap and cap not in used:
        used.add(cap); return cap
    # nudge for variety
    base = cap
    for t in range(tries):
        alt = (base + " ✨") if t == 0 else (base + " — a moment anew")
        if alt not in used:
            used.add(alt); return alt
    # last resort: add a tiny hash
    import hashlib
    tag = hashlib.md5((cap or "📷").encode("utf-8")).hexdigest()[:4]
    final = f"{cap} • {tag}" if cap else f"📷 • {tag}"
    used.add(final)
    return final

# ── Session Restoration (Robust) ─────────────────────────────
def qp_get(name, default=None):
    try:
        return st.query_params.get(name)
    except Exception:
        return st.experimental_get_query_params().get(name, [default])[0]

def safe_token_hash(token: str) -> str:
    return hashlib.md5(token.encode()).hexdigest()

def restore_session():
    """
    Restore only from a per-user cache file identified by a URL query param (?cache=<hash>)
    or from the exact file for the current in-memory token. Never scan all users' files.
    """
    if st.session_state.get("fb_token") and st.session_state.get("fb_id") and st.session_state.get("fb_name"):
        return

    cache_dir = Path("cache")
    if not cache_dir.exists():
        return

    # 1) Prefer hash from URL
    token_hash = qp_get("cache")
    path = None
    if token_hash:
        cand = cache_dir / f"backup_cache_{token_hash}.json"
        if cand.exists():
            path = cand

    # 2) If we already have a token in memory, try its exact file
    if not path and st.session_state.get("fb_token"):
        cand = cache_dir / f"backup_cache_{safe_token_hash(st.session_state['fb_token'])}.json"
        if cand.exists():
            path = cand

    # 3) Fallback: if coming back from Stripe with blob_folder, scan cache files for matching backup
    if not path:
        bf = qp_get("blob_folder")
        if bf:
            for cand in cache_dir.glob("backup_cache_*.json"):
                try:
                    d = json.loads(cand.read_text(encoding="utf-8"))
                    if d.get("selected_backup") == bf:
                        path = cand
                        break
                except Exception:
                    continue

    if not path:
        return

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        token = data.get("fb_token")
        if not token:
            return

        st.session_state["fb_token"] = token
        latest = data.get("latest_backup") or {}
        st.session_state["fb_id"] = str(latest.get("user_id") or "")
        st.session_state["fb_name"] = latest.get("Name")
        st.session_state["latest_backup"] = latest
        st.session_state["new_backup_done"] = data.get("new_backup_done")
        
        # Restore selection state
        if data.get("selected_backup"):
            st.session_state["selected_backup"] = data["selected_backup"]
        if data.get("selected_project"):
            st.session_state["selected_project"] = data["selected_project"]
    except Exception:
        pass

def persist_session():
    token = st.session_state.get("fb_token")
    if not token:
        return

    cache_dir = Path("cache")
    cache_dir.mkdir(exist_ok=True)
    
    cache = {
        "fb_token": token,
        "latest_backup": st.session_state.get("latest_backup"),
        "new_backup_done": st.session_state.get("new_backup_done"),
        "selected_backup": st.session_state.get("selected_backup"),
        "selected_project": st.session_state.get("selected_project"),
    }
    if st.session_state.get("fb_id") or st.session_state.get("fb_name"):
        cache["latest_backup"] = cache.get("latest_backup", {}) | {
            "user_id": st.session_state.get("fb_id"),
            "name": st.session_state.get("fb_name"),
        }
        
    # Save to user-specific cache file
    cache_file = cache_dir / f"backup_cache_{safe_token_hash(token)}.json"
    with open(cache_file, "w") as f:
        json.dump(cache, f)

restore_session()
if "fb_token" not in st.session_state:
    st.warning("Please login with Facebook first.")
    st.stop()

# ── Check for Posts Permission (Required for Storybook) ─────────────────────────────
def check_posts_permission(token: str) -> bool:
    """Check if the access token has user_posts permission using debug token endpoint."""
    try:
        # Method 1: Use Facebook's debug token endpoint to check actual permissions
        app_access_token = f"{st.secrets['FB_CLIENT_ID']}|{st.secrets['FB_CLIENT_SECRET']}"
        response = requests.get(
            f"https://graph.facebook.com/debug_token",
            params={
                "input_token": token,
                "access_token": app_access_token
            },
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if "data" in data:
                scopes = data.get("data", {}).get("scopes", [])
                # Check if user_posts is in the granted scopes
                has_posts = "user_posts" in scopes
                return has_posts
    except Exception as e:
        pass  # Fall through to fallback method
    
    # Fallback Method 2: Try to access posts endpoint directly
    try:
        response = requests.get(
            f"https://graph.facebook.com/me/posts?limit=1&access_token={token}",
            timeout=5
        )
        if response.status_code == 200:
            # Successfully accessed posts - permission exists
            return True
        # Check for permission error
        data = response.json()
        if "error" in data:
            error = data.get("error", {})
            error_code = error.get("code", 0)
            error_type = error.get("type", "")
            # Error code 200 or "OAuthException" with "permission denied" = no permission
            if error_code == 200 or (error_type == "OAuthException" and "permission" in error.get("message", "").lower()):
                return False
    except Exception:
        pass
    
    # If we can't determine, assume no permission (safer for App Review)
    return False

def build_posts_auth_url() -> str:
    """Build OAuth URL for requesting posts permission."""
    from urllib.parse import urlencode
    import hmac, hashlib, json, base64, time, secrets as pysecrets
    
    def _b64e(b: bytes) -> str:
        return base64.urlsafe_b64encode(b).decode().rstrip("=")
    
    def make_state(extra_data: dict = None) -> str:
        payload = {"ts": int(time.time()), "nonce": pysecrets.token_urlsafe(16)}
        if extra_data:
            payload.update(extra_data)
        raw = json.dumps(payload, separators=(",", ":")).encode()
        sig = hmac.new(st.secrets["STATE_SECRET"].encode(), raw, hashlib.sha256).digest()
        return _b64e(raw) + "." + _b64e(sig)
    
    CLIENT_ID = st.secrets["FB_CLIENT_ID"]
    REDIRECT_URI = st.secrets["FB_REDIRECT_URI"]
    
    # Request additional permission: user_posts
    scopes = "public_profile,user_photos,user_posts"
    
    # Capture current selection state to persist across redirect
    extra_data = {"return_to": "pages/FbMemories.py"}
    if st.session_state.get("selected_backup"):
        extra_data["selected_backup"] = st.session_state["selected_backup"]
    if st.session_state.get("selected_project"):
        extra_data["selected_project"] = st.session_state["selected_project"]

    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,  # Clean URI (no query params) to match whitelist
        "scope": scopes,
        "response_type": "code",
        "state": make_state(extra_data=extra_data), # Pass intent and selection in state
        "auth_type": "rerequest",  # Force re-request even if previously denied
    }
    return "https://www.facebook.com/v18.0/dialog/oauth?" + urlencode(params)

# Check if user has posts permission
has_posts_permission = False
try:
    has_posts_permission = check_posts_permission(st.session_state["fb_token"])
except Exception as e:
    has_posts_permission = False

# Handle OAuth return for posts permission
qp = st.query_params
if qp.get("return_to") == "pages/FbMemories.py" and qp.get("code"):
    # User just granted posts permission, refresh token
    code = qp.get("code")
    if isinstance(code, list):
        code = code[0]
    
    try:
        response = requests.get(
            "https://graph.facebook.com/v18.0/oauth/access_token",
            params={
                "client_id": st.secrets["FB_CLIENT_ID"],
                "redirect_uri": st.secrets["FB_REDIRECT_URI"], # Ensure consistency
                "client_secret": st.secrets["FB_CLIENT_SECRET"],
                "code": code,
            },
            timeout=10,
        )
        if response.status_code == 200:
            new_token = response.json().get("access_token")
            if new_token:
                st.session_state["fb_token"] = new_token
                st.success("✅ Posts permission granted! You can now create your storybook.")
                # Clear query params
                try:
                    st.query_params.clear()
                except:
                    pass
                st.rerun()
    except Exception as e:
        st.error(f"Failed to update permissions: {e}")

# --- Session defaults ---
if "undo_stack" not in st.session_state:
    st.session_state["undo_stack"] = {}
# --- PDF state (do NOT auto-regenerate on every rerun) ---
st.session_state.setdefault("pdf_bytes", None)     # last built PDF bytes
st.session_state.setdefault("pdf_dirty", True)     # mark needs rebuild

# ── CONSTANTS ────────────────────────────────────────────────
FUNCTION_BASE = st.secrets.get(
    "FUNCTION_BASE",
    os.environ.get("FUNCTION_BASE", "https://test0776.azurewebsites.net/api")
)
if "azurewebsites.net" not in FUNCTION_BASE:
    st.warning("⚠️ FUNCTION_BASE is not pointing to your deployed Function App. Set FUNCTION_BASE in secrets.")

CONNECT_STR   = st.secrets["AZURE_CONNECTION_STRING"]
CONTAINER     = "backup"

blob_service_client = BlobServiceClient.from_connection_string(CONNECT_STR)
container_client = blob_service_client.get_container_client(CONTAINER)

# ── Scrapbook payment helpers ────────────────────────────────
DEBUG_SCRAPBOOK = str(st.secrets.get("DEBUG_SCRAPBOOK", "false")).strip().lower() == "true"

def _scrapbook_is_paid(prefix: str) -> bool:
    """Check if user has paid for the scrapbook PDF download."""
    if DEBUG_SCRAPBOOK:
        return True
    try:
        # Check scrapbook-specific entitlements
        bc = container_client.get_blob_client(f"{prefix}/scrapbook_entitlements.json")
        if bc.exists():
            ent = json.loads(bc.download_blob().readall().decode("utf-8"))
            if bool(ent.get("scrapbook") or ent.get("paid")):
                return True
        # Marker file
        if container_client.get_blob_client(f"{prefix}/.paid.scrapbook").exists():
            return True
    except Exception:
        pass
    return False

def _write_scrapbook_entitlements(prefix: str, session: dict) -> None:
    """Write scrapbook entitlements after successful Stripe payment."""
    ent = {
        "scrapbook": True,
        "paid": True,
        "paid_at": datetime.now().isoformat(),
        "checkout_id": session.get("id"),
        "amount": (session.get("amount_total") or 0) / 100.0,
        "currency": session.get("currency"),
        "fb_id": (session.get("metadata") or {}).get("fb_id"),
        "fb_name": (session.get("metadata") or {}).get("fb_name"),
    }
    bc = container_client.get_blob_client(f"{prefix}/scrapbook_entitlements.json")
    bc.upload_blob(json.dumps(ent, ensure_ascii=False).encode("utf-8"), overwrite=True)
    container_client.get_blob_client(f"{prefix}/.paid.scrapbook").upload_blob(b"", overwrite=True)

# ── Handle Stripe redirect back (session_id in query params) ──
try:
    import stripe as _stripe
    _STRIPE_KEY = st.secrets.get("STRIPE_SCRAPBOOK_SECRET_KEY") or st.secrets.get("STRIPE_SECRET_KEY")
    _qp = st.query_params
    _sid = _qp.get("session_id")
    if isinstance(_sid, list): _sid = _sid[0]

    if _STRIPE_KEY and _sid:
        _stripe.api_key = _STRIPE_KEY
        try:
            _sess = _stripe.checkout.Session.retrieve(_sid)
        except Exception as _e:
            st.error(f"Error verifying payment: {_e}")
            _sess = None

        if _sess and (_sess.get("payment_status") or "").lower() == "paid":
            _md = _sess.get("metadata") or {}
            _prefix = _md.get("blob_folder") or _qp.get("blob_folder") or ""
            if _prefix:
                _write_scrapbook_entitlements(_prefix, _sess)
                st.session_state["scrapbook_paid"] = True
                st.session_state["selected_backup"] = _prefix

                # Build PDF from persisted data and upload to blob
                with st.spinner("Building your scrapbook PDF..."):
                    try:
                        _cls_data = json.loads(container_client.get_blob_client(
                            f"{_prefix}/scrapbook_classification.json"
                        ).download_blob().readall().decode("utf-8"))
                        _chap_data = json.loads(container_client.get_blob_client(
                            f"{_prefix}/scrapbook_chapters.json"
                        ).download_blob().readall().decode("utf-8"))
                        _sum_blob = container_client.get_blob_client(f"{_prefix}/scrapbook_summary.txt")
                        _sum_data = _sum_blob.download_blob().readall().decode("utf-8") if _sum_blob.exists() else ""
                        _user = _md.get("fb_name") or st.session_state.get("fb_name")
                        _pdf = build_pdf_bytes(_cls_data, _chap_data, _prefix, _sum_data, "polaroid", user_name=_user)
                        from azure.storage.blob import ContentSettings
                        container_client.get_blob_client(f"{_prefix}/scrapbook.pdf").upload_blob(
                            _pdf, overwrite=True,
                            content_settings=ContentSettings(content_type="application/pdf"))
                    except Exception as _pdf_err:
                        pass  # Entitlements written; PDF can be rebuilt later

                # Redirect to Projects page
                st.query_params.clear()
                st.switch_page("pages/Projects.py")
            else:
                st.error("Payment verified but couldn't resolve backup folder. Contact support.")
        elif _sess:
            _status = _sess.get("payment_status", "unknown")
            if _status == "unpaid":
                st.warning("Payment was not completed. Please try again.")
            else:
                st.warning(f"Payment status: '{_status}'. Contact support if you were charged.")
except Exception as _e:
    pass  # Stripe not available or no session_id — normal flow

# --- SAS helpers (robust across SDK variants) ---
def _get_account_key() -> str | None:
    try:
        import re
        m = re.search(r'AccountKey=([^;]+)', CONNECT_STR)
        return m.group(1) if m else None
    except Exception:
        return None

def sign_blob_url(blob_path: str) -> str:
    sas_cache = st.session_state.setdefault("_sas_cache", {})
    if blob_path in sas_cache:
        return sas_cache[blob_path]

    try:
        account_name = blob_service_client.account_name
        account_key = _get_account_key()
        sas = generate_blob_sas(
            account_name=account_name,
            container_name=CONTAINER,
            blob_name=blob_path,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=24),
        )
        url = f"https://{account_name}.blob.core.windows.net/{CONTAINER}/{quote(blob_path, safe='/')}?{sas}"
        sas_cache[blob_path] = url
        return url
    except Exception:
        return "https://via.placeholder.com/600x400?text=Image+Unavailable"

_IMAGE_INDEX_CACHE: dict[str, dict[str, str]] = {}

def _build_image_index(folder: str) -> dict[str, str]:
    """
    Build a mapping of image filename stem (post ID) → blob path
    for all images actually stored in Azure Blob Storage.
    This is the ground truth — if a blob exists here, it's displayable.
    Cached in module-level dict (safe inside @st.cache_data).
    """
    if folder in _IMAGE_INDEX_CACHE:
        return _IMAGE_INDEX_CACHE[folder]
    index = {}
    try:
        prefix = f"{folder}/images/"
        blobs = container_client.list_blobs(name_starts_with=prefix)
        for blob in blobs:
            name = blob.name  # e.g., "hash/images/12345.jpg"
            stem = Path(name).stem  # e.g., "12345"
            index[stem] = name
    except Exception:
        pass
    _IMAGE_INDEX_CACHE[folder] = index
    return index

def _resolve_image_url(img_url: str, post_id: str = "", image_index: dict = None) -> str:
    """
    Resolve an image URL to a displayable URL, with blob index fallback.
    Priority:
    1. If it's an Azure blob path/URL → sign and return
    2. If post_id exists in image_index → sign the indexed blob path
    3. Fall back to original URL (may be expired Facebook CDN)
    """
    if not img_url:
        return ""
    s = str(img_url).strip()

    # 1. Try the normal path: Azure blob detection + signing
    bp = _ours_blob_path(s)
    if bp:
        return sign_blob_url(bp)

    # 2. If it's an HTTP URL with SAS, use as-is
    if s.startswith("http") and "sig=" in s:
        return s

    # 3. Try to find the image in the blob index by post ID
    if image_index and post_id:
        clean_id = str(post_id).strip()
        if clean_id in image_index:
            return sign_blob_url(image_index[clean_id])

    # 4. Fall back to the original URL (may be expired)
    return to_display_url(s)

def _to_blob_path_if_ours_https(raw_url: str) -> str | None:
    try:
        u = urlparse(str(raw_url))
        if u.scheme in ("http", "https") and u.netloc.split(".")[0] == blob_service_client.account_name:
            if u.path.startswith(f"/{CONTAINER}/"):
                return u.path[len(f"/{CONTAINER}/"):].lstrip("/")
    except Exception:
        return None
    return None

def to_display_url(u: str) -> str:
    if not u:
        return ""
    s = str(u)
    if s.startswith("http"):
        if "sig=" in s:
            return s
        blob_path = _to_blob_path_if_ours_https(s)
        return sign_blob_url(blob_path) if blob_path else s
    return sign_blob_url(s)

# -- Simple router to make navbar links work --
view = qp_get("view")
if view == "projects":
    st.switch_page("pages/Projects.py")
elif view == "backups":
    st.switch_page("pages/FB_Backup.py")

backup_id = st.session_state.get("selected_backup")
project_id = qp_get("project_id") or st.session_state.get("selected_project")

if backup_id:
    blob_folder = backup_id  
    is_project = False
elif project_id:
    fb_token = st.session_state["fb_token"]
    fb_hash = hashlib.md5(fb_token.encode()).hexdigest()
    blob_folder = f"{fb_hash}/projects/{project_id}"
    is_project = True
else:
    st.error("⚠️ No backup or project selected. Please go to 'My Projects' or 'My Backups'.")
    st.stop()

st.session_state["_allowed_prefixes"] = [
    f"{str(blob_folder).strip('/')}/",
    "app-assets/"
]

_prev = st.session_state.get("_blob_folder")
if _prev != blob_folder:
    st.session_state["_blob_folder"] = blob_folder
    st.session_state.pop("classification", None)
    st.session_state.pop("chapters", None)
    st.session_state["pdf_bytes"] = None
    st.session_state["pdf_dirty"] = True
    st.session_state.pop("_sas_cache", None)

if project_id:
    project_id = unquote(project_id)
    st.session_state["selected_project"] = project_id

try:
    meta_blob = container_client.get_blob_client(f"{blob_folder}/project_meta.json")
    if meta_blob.exists():
        meta = json.loads(meta_blob.download_blob().readall())
        project_name = meta.get("project_name", "Facebook Memories")
    else:
        project_name = "Facebook Memories"
except:
    project_name = "Facebook Memories"

@st.cache_data(show_spinner=False)
def load_all_posts_from_blob(container: str, folder: str) -> list[dict]:
    bsc = BlobServiceClient.from_connection_string(CONNECT_STR)
    cc = bsc.get_container_client(container)
    blobs = list(cc.list_blobs(name_starts_with=f"{folder}/"))

    def _items_from_blob(blob_name: str) -> list[dict]:
        txt = bsc.get_blob_client(container, blob_name).download_blob().readall().decode("utf-8")
        try:
            data = json.loads(txt)
            if isinstance(data, list): return data
            if isinstance(data, dict) and isinstance(data.get("data"), list): return data["data"]
        except json.JSONDecodeError: pass
        return []

    def _key(p: dict) -> str:
        pid = p.get("id") or p.get("post_id") or p.get("status_id")
        if pid: return str(pid)
        base = f"{p.get('message','')}|{p.get('created_time','')}"
        return hashlib.md5(base.encode("utf-8")).hexdigest()

    posts_by_id: dict[str, dict] = {}
    for blob in blobs:
        name = blob.name.lower()
        if not (name.endswith(".json") or name.endswith(".json.json")): continue
        if "posts+cap.json" not in name: continue
        for p in _items_from_blob(blob.name): posts_by_id[_key(p)] = p

    for blob in blobs:
        name = blob.name.lower()
        if not (name.endswith(".json") or name.endswith(".json.json")): continue
        if "posts" not in name or "posts+cap.json" in name: continue
        for p in _items_from_blob(blob.name): posts_by_id.setdefault(_key(p), p)

    return list(posts_by_id.values())

def fetch_posts_from_api(token: str, max_pages: int = 50) -> list[dict]:
    url = f"https://graph.facebook.com/me/posts?fields=id,message,created_time,full_picture,attachments{{media}}&limit=100&access_token={token}"
    all_posts = []
    pages = 0
    while url and pages < max_pages:
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            data = response.json()
            if "error" in data: break
            all_posts.extend(data.get("data", []))
            url = data.get("paging", {}).get("next")
            pages += 1
        except Exception: break
    return all_posts

def save_posts_to_blob(posts: list[dict], blob_folder: str):
    try:
        blob_path = f"{blob_folder}/posts+cap.json"
        data = json.dumps(posts, indent=2, ensure_ascii=False)
        container_client.get_blob_client(blob_path).upload_blob(data, overwrite=True)
    except Exception: pass

def call_function(endpoint:str, payload:dict, timeout:int=90):
    url = f"{FUNCTION_BASE}/{endpoint}"
    try:
        res = requests.post(url, json=payload, timeout=timeout)
        res.raise_for_status()
        return res
    except Exception as e:
        st.error(f"❌ AI Service error: {e}")
        st.stop()

def parse_chapters_strict(raw: str) -> list[str]:
    raw = (raw or "").strip()
    try: data = json.loads(raw)
    except Exception:
        m = re.search(r"\{[\s\S]*\}", raw)
        try: data = json.loads(m.group(0)) if m else None
        except Exception: data = None

    chapters: list[str] = []
    if isinstance(data, dict) and isinstance(data.get("chapters"), list):
        chapters = [str(t).strip() for t in data["chapters"] if isinstance(t, str) and str(t).strip()]
    elif isinstance(data, list):
        chapters = [str(t).strip() for t in data if isinstance(t, str) and str(t).strip()]

    if not chapters: chapters = extract_titles(raw)
    out, seen = [], set()
    for t in chapters:
        t = re.sub(r"\s+", " ", t).strip(' "\'“”')
        if len(t) < 3 or t.lower() in {"none", "null", "undefined"}: continue
        if t not in seen:
            seen.add(t); out.append(t)
    return out[:12]

def _is_displayable_image_ref(u) -> bool:
    if not isinstance(u, str): return False
    s = u.strip()
    if not s or s.lower() in {"none","null","undefined","download failed"}: return False
    if s.isdigit(): return False
    if s.lower().startswith("app-assets/"): return False
    return s.startswith("http") or ("/" in s)

def _scrub_classification(cls: dict) -> dict:
    def _ok_img(u):
        if not isinstance(u, str): return False
        s = u.strip()
        if not s or s.lower() in {"none","null","undefined","download failed"}: return False
        if s.isdigit(): return False
        if s.lower().startswith("app-assets/"): return False
        return s.startswith("http") or ("/" in s)
    out = {}
    for chap, items in (cls or {}).items():
        new_items = []
        for p in (items or []):
            q = dict(p)
            imgs = q.get("images")
            if imgs is None and "image" in q: imgs = [q.get("image")]
            if not isinstance(imgs, list): imgs = [imgs] if imgs is not None else []
            imgs = [u for u in imgs if _ok_img(u)]
            q["images"] = imgs
            q.pop("image", None)
            q["message"] = _text(q.get("message"))
            q["context_caption"] = _text(q.get("context_caption"))
            if imgs or q["message"] or q["context_caption"]: new_items.append(q)
        if new_items: out[chap] = new_items
    return out

def _post_key(p: dict) -> str:
    pid = p.get("id") or p.get("post_id") or p.get("status_id")
    if pid: return str(pid)
    msg = str(p.get("message") or "")
    ct  = str(p.get("created_time") or "")
    img_keys = ",".join(sorted(_canon_for_dedupe(u) for u in (p.get("images") or []) if _is_displayable_image_ref(u)))
    return hashlib.md5(f"{msg}|{ct}|{img_keys}".encode("utf-8")).hexdigest()

def _dedupe_images_in_post(p: dict) -> dict:
    seen, keep = set(), []
    for u in (p.get("images") or []):
        if not _is_displayable_image_ref(u): continue
        k = _image_key(u)
        if not k or k in seen: continue
        seen.add(k)
        keep.append(u)
    q = dict(p); q["images"] = keep
    return q

def _dedupe_classification_global(cls: dict, chapter_order: list[str]) -> dict:
    seen_posts, seen_imgs = set(), set()
    out = {}
    for chap in chapter_order:
        filtered = []
        for p in cls.get(chap, []) or []:
            q = _dedupe_images_in_post(p)
            pk = _post_key(q)
            img_keys = [_image_key(u) for u in q.get("images") or [] if _is_displayable_image_ref(u)]
            if pk in seen_posts or any(k in seen_imgs for k in img_keys): continue
            seen_posts.add(pk)
            for k in img_keys: seen_imgs.add(k)
            filtered.append(q)
        if filtered: out[chap] = filtered
    return out

def _blob_fingerprint(blob_path: str) -> str | None:
    cache = st.session_state.setdefault("_blob_fp_cache", {})
    if blob_path in cache: return cache[blob_path]
    try:
        bc = container_client.get_blob_client(blob_path)
        if not bc.exists(): return None
        props = bc.get_blob_properties()
        etag = getattr(props, "etag", None)
        fp = "etag:" + str(etag).strip('"') if etag else None
        if fp: cache[blob_path] = fp
        return fp
    except: return None

def _image_key(u: str) -> str:
    s = (u or "").strip()
    if not s: return ""
    blob_path = _to_blob_path_if_ours_https(s) or (s if ("/" in s and not s.startswith("http")) else None)
    if blob_path and not blob_path.lower().startswith("app-assets/"):
        fp = _blob_fingerprint(blob_path)
        if fp: return fp
    return "path:" + _canon_for_dedupe(s)

def _coverage(posts_all, classification):
    all_keys, used = set(), set()
    for p in posts_all:
        for u in (p.get("images") or []):
            if _is_displayable_image_ref(u):
                all_keys.add(_image_key(u))
    for plist in classification.values():
        for p in plist:
            for u in p.get("images", []):
                if _is_displayable_image_ref(u):
                    used.add(_image_key(u))
    return len(used), max(1, len(all_keys))

def extract_titles(ai_text:str) -> list[str]:
    def _clean(t:str) -> str:
        t = t.strip()
        t = re.sub(r"^[•\-–\d\.\s]+", "", t)
        t = re.sub(r'^[\"“]+|[\"”]+$', '', t)
        return t.strip()
    titles: list[str] = []
    for raw in ai_text.splitlines():
        raw = raw.strip()
        if not raw: continue
        m = re.match(r"chapter\s*\d+[:\-]?\s*[\"“]?(.+?)[\"”]?$", raw, re.I)
        if m: titles.append(_clean(m.group(1))); continue
        m = re.match(r"(\d+\.|[•\-–])\s+(.+)$", raw)
        if m: titles.append(_clean(m.group(2))); continue
        m = re.match(r'[\"“](.+?)[\"”]$', raw)
        if m: titles.append(_clean(m.group(1)))
    return list(dict.fromkeys([t for t in titles if t]))

def render_chapter_post_images(chap_title, chapter_posts, classification, FUNCTION_BASE):
    st.markdown("<div class='card'><div class='grid-3'>", unsafe_allow_html=True)
    cols = st.columns(3)
    seen_urls: set[str] = set()
    # Build blob image index for reliable image resolution
    image_index = _build_image_index(blob_folder)
    for post_idx, post in enumerate(chapter_posts):
        images = post.get("images", []) or ([post.get("image")] if "image" in post else [])
        images = _prefer_azure([u for u in images if _is_displayable_image_ref(u)])

        # If no displayable images found via URL, try the blob index by post ID
        post_id = str(post.get("id") or post.get("post_id") or "").strip()
        if not images and post_id and post_id in image_index:
            images = [image_index[post_id]]

        # Resolve each URL to prefer actual Azure blob paths over possibly-expired CDN URLs
        resolved = []
        for u in images:
            bp = _ours_blob_path(u)
            if bp:
                resolved.append(bp)
            elif post_id and post_id in image_index:
                resolved.append(image_index[post_id])
            else:
                resolved.append(u)
        images = resolved

        if not images: continue
        caption = _unique_caption(_craft_caption_via_function(post.get("message"), post.get("context_caption")))
        for img_idx, img_url in enumerate(images):
            with cols[post_idx % 3]:
                display_url = to_display_url(img_url)
                if not display_url:
                    continue
                key = _image_key(img_url)
                if key in seen_urls: continue
                seen_urls.add(key)
                cap = _safe_caption(caption)
                st.image(display_url, caption=cap, use_container_width=True)
                button_key = f"replace_{chap_title}_{post_idx}_{img_idx}"
                if st.button("🔄 Replace", key=button_key):
                    with st.spinner("⏳ Finding a better fit..."):
                        prev_img = images[img_idx]
                        try:
                            payload = {
                                "chapter": chap_title,
                                "posts": st.session_state.get("all_posts_raw", []),
                                "exclude_images": [str(prev_img).split("?")[0]],
                                "max_per": 1,
                                "user_prefix": blob_folder,
                            }
                            res = call_function("regenerate_chapter_subset", payload, timeout=60)
                            result = res.json().get(chap_title, [])
                            if result and result[0]["images"]:
                                updated = json.loads(json.dumps(st.session_state["classification"]))
                                target = updated[chap_title][post_idx]
                                target["images"][img_idx] = result[0]["images"][0]
                                st.session_state["classification"] = updated
                                st.session_state["pdf_dirty"] = True
                                st.rerun()
                        except: pass
    st.markdown("</div></div>", unsafe_allow_html=True)

def _register_scrapbook_fonts() -> tuple[str, str, str]:
    try:
        pdfmetrics.registerFont(TTFont("SpecialElite", "fonts/SpecialElite-Regular.ttf"))
        pdfmetrics.registerFont(TTFont("PatrickHand", "fonts/PatrickHand-Regular.ttf"))
        pdfmetrics.registerFont(TTFont("Inter-Bold", "fonts/Inter-Bold.ttf"))
        return "SpecialElite", "Inter-Bold", "PatrickHand"
    except:
        return "Helvetica", "Helvetica-Bold", "Courier"

# ── Storybook colour palette (all RGB 0-1) ────────────────────
_SB_CREAM      = (0.992, 0.973, 0.941)
_SB_IVORY      = (0.976, 0.953, 0.914)
_SB_NAVY       = (0.102, 0.180, 0.290)
_SB_GOLD       = (0.769, 0.573, 0.227)
_SB_RUST       = (0.549, 0.239, 0.149)
_SB_MUTED      = (0.580, 0.560, 0.540)
_SB_TEXT       = (0.160, 0.160, 0.160)
_SB_WHITE      = (1.000, 1.000, 1.000)
_SB_SHADOW     = (0.820, 0.808, 0.790)
# Soft page-tint palette for variety
_SB_SAGE       = (0.930, 0.950, 0.930)   # soft green
_SB_BLUSH      = (0.975, 0.940, 0.940)   # warm pink
_SB_SKY        = (0.930, 0.945, 0.968)   # dusty blue
_SB_LINEN      = (0.965, 0.955, 0.935)   # warm linen
_SB_LAVENDER   = (0.945, 0.935, 0.960)   # soft purple
_PAGE_TINTS    = [_SB_CREAM, _SB_SAGE, _SB_BLUSH, _SB_SKY, _SB_LINEN, _SB_LAVENDER]
_TAPE_COLORS   = [
    (0.94, 0.91, 0.84),   # classic beige
    (0.88, 0.92, 0.88),   # sage green
    (0.93, 0.88, 0.88),   # dusty rose
    (0.88, 0.90, 0.94),   # sky blue
    (0.92, 0.89, 0.94),   # lavender
]

# Inspirational quotes for interlude pages
_MEMORY_QUOTES = [
    ("The best thing about memories is making them.", ""),
    ("Life is not measured by the breaths we take,\nbut by the moments that take our breath away.", ""),
    ("Sometimes you will never know the value\nof a moment until it becomes a memory.", "Dr. Seuss"),
    ("We do not remember days,\nwe remember moments.", "Cesare Pavese"),
    ("In the end, it's not the years in your life that count.\nIt's the life in your years.", "Abraham Lincoln"),
    ("Collect moments, not things.", ""),
    ("The camera is an instrument that teaches\npeople how to see without a camera.", "Dorothea Lange"),
    ("A photograph is a pause button on life.", ""),
]

def _sf(c, rgb): c.setFillColorRGB(*rgb)
def _ss(c, rgb): c.setStrokeColorRGB(*rgb)

def _ornament_corners(c, x, y, w, h, size=18, color=None):
    color = color or _SB_GOLD
    _ss(c, color)
    c.setLineWidth(1.2)
    for (cx, cy), (sx, sy) in zip(
        [(x, y+h), (x+w, y+h), (x, y), (x+w, y)],
        [( 1,-1),  (-1,-1),    ( 1, 1), (-1,  1)]
    ):
        c.line(cx, cy, cx + sx*size, cy)
        c.line(cx, cy, cx, cy + sy*size)

def _divider(c, cx, y, half_w=80, color=None):
    color = color or _SB_GOLD
    _ss(c, color)
    c.setLineWidth(0.8)
    c.line(cx - half_w, y, cx - 10, y)
    c.line(cx + 10, y, cx + half_w, y)
    c.saveState()
    c.translate(cx, y)
    c.rotate(45)
    _sf(c, color)
    c.rect(-3.5, -3.5, 7, 7, fill=True, stroke=False)
    c.restoreState()

def _star_divider(c, cx, y, half_w=90, color=None):
    color = color or _SB_GOLD
    _ss(c, color)
    c.setLineWidth(0.6)
    c.line(cx - half_w, y, cx - 18, y)
    c.line(cx + 18, y, cx + half_w, y)
    _sf(c, color)
    for dx in [-8, 0, 8]:
        c.saveState()
        c.translate(cx + dx, y)
        c.rotate(45)
        sz = 3.0 if dx == 0 else 2.0
        c.rect(-sz, -sz, sz*2, sz*2, fill=True, stroke=False)
        c.restoreState()

def _double_border(c, x, y, w, h, gap=5, color=None):
    color = color or _SB_NAVY
    _ss(c, color)
    c.setLineWidth(1.5)
    c.rect(x, y, w, h, fill=False, stroke=True)
    c.setLineWidth(0.5)
    c.rect(x+gap, y+gap, w-2*gap, h-2*gap, fill=False, stroke=True)

def _corner_flourish(c, x, y, size=30, flip_x=False, flip_y=False, color=None):
    """Draw a simple elegant corner mark with a small leaf-like accent."""
    color = color or _SB_GOLD
    _ss(c, color)
    _sf(c, color)
    sx = -1 if flip_x else 1
    sy = -1 if flip_y else 1
    # L-shaped corner line
    c.setLineWidth(0.6)
    c.line(x, y, x + sx * size, y)
    c.line(x, y, x, y + sy * size)
    # Small diamond accent at corner
    c.saveState()
    c.translate(x, y)
    c.rotate(45)
    c.rect(-2.5, -2.5, 5, 5, fill=True, stroke=False)
    c.restoreState()

def _fetch_img(url: str) -> "ImageReader | None":
    """Fetch image for PDF rendering."""
    try:
        r = requests.get(to_display_url(url), timeout=14)
        r.raise_for_status()
        return ImageReader(BytesIO(r.content))
    except Exception:
        return None

def _draw_tape(c, cx, cy, tw=40, th=14, angle=0, color=None):
    color = color or _TAPE_COLORS[0]
    c.saveState()
    c.translate(cx, cy)
    if angle:
        c.rotate(angle)
    _sf(c, color)
    c.roundRect(-tw/2, -th/2, tw, th, 2, fill=True, stroke=False)
    # Tape edge lines
    darker = tuple(max(0, v - 0.04) for v in color)
    _ss(c, darker)
    c.setLineWidth(0.2)
    c.line(-tw/2 + 2, -th/2 + 2, tw/2 - 2, -th/2 + 2)
    c.line(-tw/2 + 2, th/2 - 2, tw/2 - 2, th/2 - 2)
    c.restoreState()

def _draw_photo_corners(c, cx, cy, dw, dh, color=None):
    """Draw vintage album-style photo corner mounts (simple triangles)."""
    color = color or (0.82, 0.78, 0.68)
    sz = 11
    _sf(c, color)
    # Four corners: draw small rotated squares clipped to triangles
    for ox, oy, rot in [(-dw/2, -dh/2, 0), (dw/2, -dh/2, 90),
                         (-dw/2, dh/2, -90), (dw/2, dh/2, 180)]:
        c.saveState()
        c.translate(cx + ox, cy + oy)
        c.rotate(rot)
        c.rotate(45)
        c.rect(-sz*0.35, -sz*0.35, sz*0.7, sz*0.7, fill=True, stroke=False)
        c.restoreState()

def _framed_photo(c, img_reader, cx, cy, pw, ph,
                  caption="", date_str="", angle=0, style="polaroid",
                  tape_color=None):
    """
    Draw a beautifully framed photo centred on (cx, cy).
    Styles: 'polaroid', 'clean', 'tape', 'vintage', 'magazine'.
    """
    if img_reader:
        iw, ih = img_reader.getSize()
        scale = min(pw / iw, ph / ih)
        dw, dh = iw * scale, ih * scale
    else:
        dw, dh = pw * 0.5, ph * 0.5

    c.saveState()
    c.translate(cx, cy)
    if angle:
        c.rotate(angle)

    if style == "polaroid":
        pad_x, pad_top = 12, 12
        pad_bot = 48 if caption else 20
        fw = dw + 2 * pad_x
        fh = dh + pad_top + pad_bot

        # Layered shadow for depth
        _sf(c, (0.86, 0.85, 0.83))
        c.roundRect(-fw/2 + 5, -fh/2 - 5, fw, fh, 4, fill=True, stroke=False)
        _sf(c, _SB_SHADOW)
        c.roundRect(-fw/2 + 3, -fh/2 - 3, fw, fh, 4, fill=True, stroke=False)

        # White frame
        _sf(c, _SB_WHITE)
        _ss(c, (0.88, 0.86, 0.83))
        c.setLineWidth(0.4)
        c.roundRect(-fw/2, -fh/2, fw, fh, 4, fill=True, stroke=True)

        if img_reader:
            c.drawImage(img_reader, -dw/2, -fh/2 + pad_bot, width=dw, height=dh, mask='auto')
            # Subtle inner shadow line on photo
            _ss(c, (0.75, 0.73, 0.70))
            c.setLineWidth(0.3)
            c.rect(-dw/2, -fh/2 + pad_bot, dw, dh, fill=False, stroke=True)

        if caption:
            _sf(c, _SB_TEXT)
            c.setFont("Courier", 7.5)
            # Italic-style open/close quotes
            lines = wrap(caption.strip(), int(fw / 4.8)) or [""]
            ty = -fh/2 + 6
            for li, line in enumerate(lines[:3]):
                prefix = "\u201c " if li == 0 else ""
                suffix = " \u201d" if li == min(2, len(lines)-1) else ""
                c.drawCentredString(0, ty, f"{prefix}{line}{suffix}")
                ty += 10

        if date_str:
            _sf(c, _SB_RUST)
            c.setFont("Courier", 6.5)
            c.drawRightString(fw/2 - 6, fh/2 - 11, date_str)

    elif style == "clean":
        border = 3
        fw = dw + border * 2
        cap_h = 28 if caption else 6
        fh = dh + border * 2 + cap_h

        # Shadow
        c.setFillColorRGB(0.87, 0.86, 0.84)
        c.roundRect(-fw/2 + 3, -fh/2 - 3, fw, fh, 2, fill=True, stroke=False)

        _sf(c, _SB_WHITE)
        _ss(c, (0.90, 0.88, 0.85))
        c.setLineWidth(0.3)
        c.roundRect(-fw/2, -fh/2, fw, fh, 2, fill=True, stroke=True)

        if img_reader:
            c.drawImage(img_reader, -dw/2, -fh/2 + cap_h, width=dw, height=dh, mask='auto')

        if caption:
            _sf(c, _SB_MUTED)
            c.setFont("Courier", 6.5)
            lines = wrap(caption.strip(), int(fw / 4.4)) or [""]
            ty = -fh/2 + 4
            for line in lines[:2]:
                c.drawCentredString(0, ty, line)
                ty += 9

        if date_str:
            _sf(c, _SB_GOLD)
            c.setFont("Courier", 6)
            c.drawRightString(fw/2 - 4, fh/2 - 9, date_str)

    elif style == "tape":
        if img_reader:
            c.drawImage(img_reader, -dw/2, -dh/2, width=dw, height=dh, mask='auto')
            _ss(c, (0.90, 0.88, 0.85))
            c.setLineWidth(0.3)
            c.rect(-dw/2, -dh/2, dw, dh, fill=False, stroke=True)

        tc = tape_color or _TAPE_COLORS[0]
        _draw_tape(c, -dw/2 + 18, dh/2 - 1, tw=38, th=12, angle=22, color=tc)
        _draw_tape(c, dw/2 - 18, dh/2 - 1, tw=38, th=12, angle=-22, color=tc)

        if caption:
            _sf(c, _SB_TEXT)
            c.setFont("Courier", 6.5)
            lines = wrap(caption.strip(), int(dw / 4.2)) or [""]
            ty = -dh/2 - 13
            for line in lines[:2]:
                c.drawCentredString(0, ty, line)
                ty -= 9

        if date_str:
            _sf(c, _SB_MUTED)
            c.setFont("Courier", 6)
            c.drawRightString(dw/2, dh/2 + 14, date_str)

    elif style == "vintage":
        # Photo with vintage corner mounts (no frame border)
        if img_reader:
            c.drawImage(img_reader, -dw/2, -dh/2, width=dw, height=dh, mask='auto')
        _draw_photo_corners(c, 0, 0, dw, dh)

        if caption:
            _sf(c, _SB_TEXT)
            c.setFont("Courier", 6.5)
            lines = wrap(caption.strip(), int(dw / 4.2)) or [""]
            ty = -dh/2 - 13
            for line in lines[:2]:
                c.drawCentredString(0, ty, line)
                ty -= 9

        if date_str:
            _sf(c, _SB_RUST)
            c.setFont("Courier", 6.5)
            c.drawCentredString(0, dh/2 + 10, date_str)

    elif style == "magazine":
        # Borderless with gold accent line below
        if img_reader:
            c.drawImage(img_reader, -dw/2, -dh/2 + 8, width=dw, height=dh, mask='auto')

        # Gold accent bar under photo
        _sf(c, _SB_GOLD)
        c.rect(-dw/2, -dh/2 + 4, dw, 2, fill=True, stroke=False)

        if caption:
            _sf(c, _SB_NAVY)
            c.setFont("Courier", 7)
            lines = wrap(caption.strip(), int(dw / 4.2)) or [""]
            ty = -dh/2 - 8
            for line in lines[:2]:
                c.drawCentredString(0, ty, line)
                ty -= 9

        if date_str:
            _sf(c, _SB_GOLD)
            c.setFont("Courier", 7)
            c.drawString(-dw/2, -dh/2 - 6, date_str)

    c.restoreState()

def _page_bg(c, W, H, page_num, header=True, footer=True, chap_title="", fonts=None, tint=None):
    """Render a beautiful content page background with header/footer."""
    tf, bf, cf = fonts or ("Helvetica", "Helvetica-Bold", "Courier")
    bg = tint or _PAGE_TINTS[page_num % len(_PAGE_TINTS)]

    # Page background
    _sf(c, bg)
    c.rect(0, 0, W, H, fill=True, stroke=False)

    # Decorative corner flourishes
    _corner_flourish(c, 22, H - 22, size=26, flip_y=True, color=_SB_GOLD)
    _corner_flourish(c, W - 22, H - 22, size=26, flip_x=True, flip_y=True, color=_SB_GOLD)
    _corner_flourish(c, 22, 22, size=26, color=_SB_GOLD)
    _corner_flourish(c, W - 22, 22, size=26, flip_x=True, color=_SB_GOLD)

    # Thin decorative border
    _ss(c, (0.88, 0.86, 0.83))
    c.setLineWidth(0.3)
    c.roundRect(18, 18, W - 36, H - 36, 3, fill=False, stroke=True)

    if header and chap_title:
        # Elegant header
        _sf(c, _SB_NAVY)
        c.setFont(cf, 7)
        c.drawCentredString(W/2, H - 28, chap_title.upper())
        # Thin gold rule
        _sf(c, _SB_GOLD)
        c.rect(W/2 - 50, H - 33, 100, 0.4, fill=True, stroke=False)

    if footer:
        # Decorative footer with diamond
        _sf(c, _SB_MUTED)
        c.setFont(cf, 7)
        c.drawCentredString(W/2, 14, f"-  {page_num}  -")
        # Tiny gold dots flanking page number
        _sf(c, _SB_GOLD)
        c.circle(W/2 - 22, 17, 1.2, fill=True, stroke=False)
        c.circle(W/2 + 22, 17, 1.2, fill=True, stroke=False)

def _page_decorative_border(c, W, H, M=24):
    """Subtle decorative border for content pages (legacy compat)."""
    _ss(c, (0.88, 0.86, 0.83))
    c.setLineWidth(0.3)
    c.rect(M, M, W - 2*M, H - 2*M, fill=False, stroke=True)
    _sf(c, _SB_GOLD)
    for x, y in [(M, M), (W-M, M), (M, H-M), (W-M, H-M)]:
        c.circle(x, y, 2, fill=True, stroke=False)

# ── Individual page renderers ──────────────────────────────────

def _page_cover(c, W, H, user_name: str, summary: str, chapters: list, fonts: tuple):
    tf, bf, cf = fonts
    M = 28

    # Navy background
    _sf(c, _SB_NAVY)
    c.rect(0, 0, W, H, fill=True, stroke=False)

    # Gold bands
    _sf(c, _SB_GOLD)
    c.rect(0, H - 52, W, 52, fill=True, stroke=False)
    c.rect(0, 0, W, 40, fill=True, stroke=False)

    # Cream accent lines
    _sf(c, _SB_CREAM)
    c.rect(0, H - 54, W, 1, fill=True, stroke=False)
    c.rect(0, 40, W, 1, fill=True, stroke=False)

    # Borders
    _double_border(c, M, 44, W - 2*M, H - 100, gap=6, color=_SB_CREAM)
    _ss(c, _SB_GOLD)
    c.setLineWidth(0.5)
    c.rect(M+10, 52, W - 2*M - 20, H - 116, fill=False, stroke=True)
    _ornament_corners(c, M+14, 56, W - 2*M - 28, H - 124, size=24, color=_SB_GOLD)

    # Corner flourishes on navy body
    _corner_flourish(c, M+20, H - 60, size=35, flip_y=True, color=_SB_GOLD)
    _corner_flourish(c, W-M-20, H - 60, size=35, flip_x=True, flip_y=True, color=_SB_GOLD)
    _corner_flourish(c, M+20, 50, size=35, color=_SB_GOLD)
    _corner_flourish(c, W-M-20, 50, size=35, flip_x=True, color=_SB_GOLD)

    # Eyebrow
    _sf(c, _SB_GOLD)
    c.setFont(tf, 9)
    c.drawCentredString(W/2, H - 84, "F A C E B O O K    M E M O R I E S")
    _star_divider(c, W/2, H - 98, half_w=100, color=_SB_GOLD)

    # User name
    _sf(c, _SB_CREAM)
    font_size = 38 if len(user_name) <= 16 else (28 if len(user_name) <= 24 else 22)
    c.setFont(bf, font_size)
    c.drawCentredString(W/2, H/2 + 80, user_name)

    # Thin gold rule
    _sf(c, _SB_GOLD)
    c.rect(W/2 - 70, H/2 + 70, 140, 0.8, fill=True, stroke=False)

    # Subtitle
    c.setFont(tf, 14)
    c.drawCentredString(W/2, H/2 + 48, "A Life in Memories")
    _divider(c, W/2, H/2 + 32, half_w=75, color=_SB_GOLD)

    # Summary
    if summary:
        _sf(c, (0.78, 0.76, 0.73))
        c.setFont(cf, 9)
        lines = wrap(summary.strip()[:380], 56)
        ty = H/2 + 10
        for line in lines[:5]:
            c.drawCentredString(W/2, ty, line)
            ty -= 13

    # Chapter count
    _star_divider(c, W/2, H/2 - 80, half_w=55, color=_SB_GOLD)
    _sf(c, (0.60, 0.58, 0.55))
    c.setFont(cf, 9)
    c.drawCentredString(W/2, H/2 - 98, f"{len(chapters)} Chapters  \u00b7  {datetime.now().year}")

    # Branding
    _sf(c, _SB_NAVY)
    c.setFont(bf, 10)
    c.drawCentredString(W/2, 14, "LiveOn")


def _page_toc(c, W, H, chapters: list, fonts: tuple):
    tf, bf, cf = fonts
    M = 46
    roman = ["I","II","III","IV","V","VI","VII","VIII","IX","X","XI","XII"]

    _sf(c, _SB_CREAM)
    c.rect(0, 0, W, H, fill=True, stroke=False)

    # Navy top band
    _sf(c, _SB_NAVY)
    c.rect(0, H - 66, W, 66, fill=True, stroke=False)
    _sf(c, _SB_GOLD)
    c.rect(0, H - 68, W, 2, fill=True, stroke=False)

    _sf(c, _SB_CREAM)
    c.setFont(bf, 18)
    c.drawCentredString(W/2, H - 46, "Table of Contents")
    _sf(c, _SB_GOLD)
    c.setFont(tf, 8)
    c.drawCentredString(W/2, H - 58, "- your story in chapters -")

    _double_border(c, M - 10, M - 10, W - 2*M + 20, H - 2*M - 50, gap=5, color=_SB_NAVY)
    _ornament_corners(c, M - 2, M - 2, W - 2*M + 4, H - 2*M - 66, size=16, color=_SB_GOLD)

    # Flourishes
    _corner_flourish(c, M, H - 78, size=22, flip_y=True, color=_SB_GOLD)
    _corner_flourish(c, W - M, H - 78, size=22, flip_x=True, flip_y=True, color=_SB_GOLD)

    # Fixed column positions for clean alignment
    col_num   = M + 10            # roman numeral left edge
    col_dot   = M + 38            # dot separator
    col_title = M + 46            # chapter title left edge
    col_end   = W - M - 10        # right edge for page numbers
    leader_end = col_end - 4

    start_y = H - 108
    row_h = 34
    for i, chap in enumerate(chapters):
        ry = start_y - i * row_h
        if ry < M + 10:
            break
        if i % 2 == 0:
            _sf(c, _SB_IVORY)
            c.rect(M, ry - 6, W - 2*M, row_h - 2, fill=True, stroke=False)

        # Roman numeral — right-aligned in its column
        num = roman[i] if i < len(roman) else str(i + 1)
        _sf(c, _SB_GOLD)
        c.setFont(bf, 10)
        c.drawRightString(col_dot - 6, ry + 8, num)

        # Gold dot separator
        c.circle(col_dot, ry + 12, 1.5, fill=True, stroke=False)

        # Chapter title — fixed left position
        _sf(c, _SB_NAVY)
        c.setFont(tf, 11)
        c.drawString(col_title, ry + 8, chap)

        # Dotted leader — starts after actual text width
        title_width = c.stringWidth(chap, tf, 11)
        leader_start = col_title + title_width + 8
        if leader_start < leader_end - 20:
            _ss(c, _SB_MUTED)
            c.setLineWidth(0.4)
            c.setDash([1, 4])
            c.line(leader_start, ry + 12, leader_end, ry + 12)
            c.setDash()

    _sf(c, _SB_MUTED)
    c.setFont(cf, 8)
    c.drawCentredString(W/2, M/2, "- i -")


def _page_chapter_title(c, W, H, title: str, num: int, fonts: tuple):
    tf, bf, cf = fonts
    roman = ["I","II","III","IV","V","VI","VII","VIII","IX","X","XI","XII"]
    num_str = roman[num - 1] if num <= 12 else str(num)

    _sf(c, _SB_IVORY)
    c.rect(0, 0, W, H, fill=True, stroke=False)

    # Spine
    _sf(c, _SB_NAVY)
    c.rect(0, 0, 48, H, fill=True, stroke=False)
    _sf(c, _SB_GOLD)
    c.rect(48, 0, 3, H, fill=True, stroke=False)
    _sf(c, _SB_CREAM)
    c.rect(47, 0, 0.5, H, fill=True, stroke=False)

    c.saveState()
    c.translate(24, H / 2)
    c.rotate(90)
    _sf(c, _SB_GOLD)
    c.setFont(bf, 9)
    c.drawCentredString(0, 0, f"CHAPTER  {num_str}")
    c.restoreState()

    # Ghost numeral
    _sf(c, (0.968, 0.945, 0.906))
    c.setFont(bf, 150)
    c.drawRightString(W - 16, H * 0.04, num_str)

    # Corner flourishes on right page
    cx = 55 + (W - 55) / 2
    _corner_flourish(c, 62, H - 30, size=28, flip_y=True, color=_SB_GOLD)
    _corner_flourish(c, W - 22, H - 30, size=28, flip_x=True, flip_y=True, color=_SB_GOLD)
    _corner_flourish(c, 62, 30, size=28, color=_SB_GOLD)
    _corner_flourish(c, W - 22, 30, size=28, flip_x=True, color=_SB_GOLD)

    # Content
    _sf(c, _SB_GOLD)
    c.setFont(cf, 10)
    c.drawCentredString(cx, H * 0.66, f"Chapter {num_str}")
    _star_divider(c, cx, H * 0.62, half_w=85, color=_SB_GOLD)

    font_size = 28 if len(title) <= 22 else 20
    _sf(c, _SB_NAVY)
    c.setFont(tf, font_size)
    c.drawCentredString(cx, H * 0.54, title)

    _star_divider(c, cx, H * 0.48, half_w=85, color=_SB_GOLD)

    _sf(c, _SB_MUTED)
    c.setFont(cf, 9)
    c.drawCentredString(cx, H * 0.43, "A collection of cherished moments")

    # Gold bottom rule
    _sf(c, _SB_GOLD)
    c.rect(55, 0, W - 55, 4, fill=True, stroke=False)


def _page_quote(c, W, H, quote_text: str, attribution: str, fonts: tuple):
    """Render an inspirational quote interlude page."""
    tf, bf, cf = fonts

    # Soft background
    _sf(c, _SB_IVORY)
    c.rect(0, 0, W, H, fill=True, stroke=False)

    # Decorative border
    _ss(c, _SB_GOLD)
    c.setLineWidth(0.4)
    c.roundRect(36, 36, W - 72, H - 72, 4, fill=False, stroke=True)
    _ornament_corners(c, 42, 42, W - 84, H - 84, size=18, color=_SB_GOLD)

    # Large decorative open-quote mark
    _sf(c, (0.92, 0.90, 0.86))
    c.setFont(bf, 120)
    c.drawCentredString(W/2, H * 0.68, "\u201c")

    # Quote text
    _sf(c, _SB_NAVY)
    c.setFont(tf, 14)
    lines = quote_text.split("\n")
    ty = H * 0.54
    for line in lines:
        c.drawCentredString(W/2, ty, line.strip())
        ty -= 20

    _divider(c, W/2, ty - 8, half_w=60, color=_SB_GOLD)

    # Attribution
    if attribution:
        _sf(c, _SB_MUTED)
        c.setFont(cf, 9)
        c.drawCentredString(W/2, ty - 26, f"- {attribution}")


# ── Content page layout styles ────────────────────────────────

def _layout_hero(c, W, H, chap_title, items, page_num, fonts):
    """Single stunning large photo."""
    tf, bf, cf = fonts
    item = items[0]
    img = _fetch_img(item.get("img", ""))
    cap = item.get("caption", "")
    if cap == "\U0001f4f7": cap = ""
    date_s = _format_date(item.get("date", ""))

    _page_bg(c, W, H, page_num, chap_title=chap_title, fonts=fonts)

    _framed_photo(c, img, W/2, H/2 + 10, W * 0.72, H * 0.64,
                  cap, date_s, angle=0, style="polaroid")


def _layout_duo(c, W, H, chap_title, items, page_num, fonts):
    """Two photos side by side, contrasting styles."""
    tf, bf, cf = fonts
    _page_bg(c, W, H, page_num, chap_title=chap_title, fonts=fonts)

    pw, ph = W * 0.40, H * 0.56
    x1, x2 = W * 0.27, W * 0.73
    cy = H * 0.47

    style_pairs = [("polaroid", "tape"), ("clean", "vintage"), ("vintage", "polaroid")]
    s1, s2 = style_pairs[page_num % len(style_pairs)]
    tc = _TAPE_COLORS[page_num % len(_TAPE_COLORS)]

    for i, item in enumerate(items[:2]):
        img = _fetch_img(item.get("img", ""))
        cap = item.get("caption", "")
        if cap == "\U0001f4f7": cap = ""
        date_s = _format_date(item.get("date", ""))
        _framed_photo(c, img, x1 if i == 0 else x2, cy, pw, ph,
                      cap, date_s, angle=[-2.0, 1.8][i],
                      style=s1 if i == 0 else s2, tape_color=tc)


def _layout_trio(c, W, H, chap_title, items, page_num, fonts):
    """One large featured photo top, two smaller below."""
    tf, bf, cf = fonts
    _page_bg(c, W, H, page_num, chap_title=chap_title, fonts=fonts)
    tc = _TAPE_COLORS[page_num % len(_TAPE_COLORS)]

    configs = [
        (W/2,      H * 0.64, W * 0.54, H * 0.36, 0,    "magazine"),
        (W * 0.28, H * 0.22, W * 0.36, H * 0.28, -1.5, "polaroid"),
        (W * 0.72, H * 0.22, W * 0.36, H * 0.28, 1.5,  "tape"),
    ]
    for i, item in enumerate(items[:3]):
        if i >= len(configs): break
        cx, cy, pw, ph, angle, style = configs[i]
        img = _fetch_img(item.get("img", ""))
        cap = item.get("caption", "")
        if cap == "\U0001f4f7": cap = ""
        date_s = _format_date(item.get("date", ""))
        _framed_photo(c, img, cx, cy, pw, ph, cap, date_s, angle, style,
                      tape_color=tc)


def _layout_grid(c, W, H, chap_title, items, page_num, fonts):
    """2x2 grid with mixed frame styles."""
    tf, bf, cf = fonts
    _page_bg(c, W, H, page_num, chap_title=chap_title, fonts=fonts)
    tc = _TAPE_COLORS[page_num % len(_TAPE_COLORS)]

    pw, ph = W * 0.40, H * 0.35
    x1, x2 = W * 0.27, W * 0.73
    y_top, y_bot = H * 0.67, H * 0.29

    style_sets = [
        ["polaroid", "tape", "vintage", "clean"],
        ["clean", "polaroid", "tape", "vintage"],
        ["vintage", "clean", "polaroid", "tape"],
    ]
    styles = style_sets[page_num % len(style_sets)]
    angles = [-1.0, 1.2, 1.0, -1.2]
    positions = [(x1, y_top), (x2, y_top), (x1, y_bot), (x2, y_bot)]

    for i, item in enumerate(items[:4]):
        cx, cy = positions[i]
        img = _fetch_img(item.get("img", ""))
        cap = item.get("caption", "")
        if cap == "\U0001f4f7": cap = ""
        date_s = _format_date(item.get("date", ""))
        _framed_photo(c, img, cx, cy, pw, ph, cap, date_s, angles[i],
                      styles[i], tape_color=tc)


def _layout_staggered(c, W, H, chap_title, items, page_num, fonts):
    """Asymmetric: one tall left, two stacked right."""
    tf, bf, cf = fonts
    _page_bg(c, W, H, page_num, chap_title=chap_title, fonts=fonts)
    tc = _TAPE_COLORS[page_num % len(_TAPE_COLORS)]

    n = min(len(items), 3)
    if n >= 1:
        img = _fetch_img(items[0].get("img", ""))
        cap = items[0].get("caption", "")
        if cap == "\U0001f4f7": cap = ""
        date_s = _format_date(items[0].get("date", ""))
        _framed_photo(c, img, W * 0.30, H * 0.47, W * 0.42, H * 0.62,
                      cap, date_s, angle=-0.8, style="polaroid")
    if n >= 2:
        img = _fetch_img(items[1].get("img", ""))
        cap = items[1].get("caption", "")
        if cap == "\U0001f4f7": cap = ""
        date_s = _format_date(items[1].get("date", ""))
        _framed_photo(c, img, W * 0.74, H * 0.62, W * 0.36, H * 0.30,
                      cap, date_s, angle=1.5, style="tape", tape_color=tc)
    if n >= 3:
        img = _fetch_img(items[2].get("img", ""))
        cap = items[2].get("caption", "")
        if cap == "\U0001f4f7": cap = ""
        date_s = _format_date(items[2].get("date", ""))
        _framed_photo(c, img, W * 0.72, H * 0.26, W * 0.34, H * 0.28,
                      cap, date_s, angle=-1.0, style="vintage")


def _layout_magazine(c, W, H, chap_title, items, page_num, fonts):
    """Magazine-style: large photo left, caption panel right."""
    tf, bf, cf = fonts
    _page_bg(c, W, H, page_num, chap_title=chap_title, fonts=fonts, tint=_SB_CREAM)

    item = items[0]
    img = _fetch_img(item.get("img", ""))
    cap = item.get("caption", "")
    if cap == "\U0001f4f7": cap = ""
    date_s = _format_date(item.get("date", ""))

    # Large photo taking left 60%
    _framed_photo(c, img, W * 0.33, H * 0.50, W * 0.52, H * 0.68,
                  "", "", angle=0, style="magazine")

    # Right side text panel
    panel_x = W * 0.64
    panel_w = W * 0.30

    if date_s:
        _sf(c, _SB_GOLD)
        c.setFont(cf, 8)
        c.drawString(panel_x, H * 0.68, date_s)
        _sf(c, _SB_GOLD)
        c.rect(panel_x, H * 0.66, 40, 0.5, fill=True, stroke=False)

    if cap:
        _sf(c, _SB_NAVY)
        c.setFont(tf, 11)
        lines = wrap(cap.strip(), int(panel_w / 6.5)) or [""]
        ty = H * 0.62
        for line in lines[:6]:
            c.drawString(panel_x, ty, line)
            ty -= 14

    # Small decorative element
    _divider(c, panel_x + panel_w/2, H * 0.30, half_w=35, color=_SB_GOLD)


def _format_date(raw_d):
    if not raw_d:
        return ""
    try:
        dt = datetime.fromisoformat(raw_d.replace("Z", "+00:00"))
        return dt.strftime("%b %Y")
    except Exception:
        return str(raw_d)[:7]


def _page_photos(c, W, H, chap_title: str, items: list, page_num: int, fonts: tuple):
    """Route to the best layout based on item count and page variety."""
    n = len(items)
    if n == 1:
        # Alternate hero and magazine for single photos
        if page_num % 3 == 0:
            _layout_magazine(c, W, H, chap_title, items, page_num, fonts)
        else:
            _layout_hero(c, W, H, chap_title, items, page_num, fonts)
    elif n == 2:
        if page_num % 2 == 0:
            _layout_duo(c, W, H, chap_title, items, page_num, fonts)
        else:
            _layout_staggered(c, W, H, chap_title, items, page_num, fonts)
    elif n == 3:
        if page_num % 2 == 0:
            _layout_trio(c, W, H, chap_title, items, page_num, fonts)
        else:
            _layout_staggered(c, W, H, chap_title, items, page_num, fonts)
    else:
        _layout_grid(c, W, H, chap_title, items, page_num, fonts)


def _page_back_cover(c, W, H, fonts: tuple):
    tf, bf, cf = fonts
    M = 28

    _sf(c, _SB_NAVY)
    c.rect(0, 0, W, H, fill=True, stroke=False)

    _sf(c, _SB_GOLD)
    c.rect(0, H - 52, W, 52, fill=True, stroke=False)
    c.rect(0, 0, W, 40, fill=True, stroke=False)
    _sf(c, _SB_CREAM)
    c.rect(0, H - 54, W, 1, fill=True, stroke=False)
    c.rect(0, 40, W, 1, fill=True, stroke=False)

    _double_border(c, M, 44, W - 2*M, H - 100, gap=6, color=_SB_CREAM)
    _ss(c, _SB_GOLD)
    c.setLineWidth(0.5)
    c.rect(M+10, 52, W - 2*M - 20, H - 116, fill=False, stroke=True)
    _ornament_corners(c, M+14, 56, W - 2*M - 28, H - 124, size=20, color=_SB_GOLD)

    _corner_flourish(c, M+20, H - 58, size=32, flip_y=True, color=_SB_GOLD)
    _corner_flourish(c, W-M-20, H - 58, size=32, flip_x=True, flip_y=True, color=_SB_GOLD)
    _corner_flourish(c, M+20, 48, size=32, color=_SB_GOLD)
    _corner_flourish(c, W-M-20, 48, size=32, flip_x=True, color=_SB_GOLD)

    _sf(c, _SB_CREAM)
    c.setFont(tf, 22)
    c.drawCentredString(W/2, H/2 + 48, "Thank you")
    c.setFont(tf, 15)
    c.drawCentredString(W/2, H/2 + 24, "for the memories.")
    _star_divider(c, W/2, H/2 + 6, half_w=80, color=_SB_GOLD)

    _sf(c, (0.62, 0.60, 0.57))
    c.setFont(cf, 9)
    c.drawCentredString(W/2, H/2 - 16, "Every photo tells a story.")
    c.drawCentredString(W/2, H/2 - 30, "Every story deserves to be remembered.")

    _divider(c, W/2, H/2 - 52, half_w=50, color=_SB_GOLD)
    _sf(c, (0.55, 0.53, 0.50))
    c.setFont(cf, 8)
    c.drawCentredString(W/2, H/2 - 68, f"Generated {datetime.now().strftime('%B %Y')}")

    _sf(c, _SB_NAVY)
    c.setFont(bf, 10)
    c.drawCentredString(W/2, 14, "LiveOn")


# ── Main PDF assembler ─────────────────────────────────────────

def build_pdf_bytes(classification, chapters, blob_folder, profile_summary, template="polaroid", user_name=None):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    W, H = A4
    fonts = _register_scrapbook_fonts()

    # Use provided name, fall back to blob path segment, then default
    if not user_name:
        try:
            user_name = (blob_folder or "").split("/")[0][:28].strip() or "My Story"
        except Exception:
            user_name = "My Story"

    active = [ch for ch in chapters if classification.get(ch)]

    # Build blob image index for reliable image resolution
    pdf_img_idx = _build_image_index(blob_folder)

    # ── Cover ──────────────────────────────────────────────────
    _page_cover(c, W, H, user_name, profile_summary or "", active, fonts)
    c.showPage()

    # ── Table of Contents ──────────────────────────────────────
    if active:
        _page_toc(c, W, H, active, fonts)
        c.showPage()

    # ── Chapters ───────────────────────────────────────────────
    page_num = 1
    quote_idx = 0
    for chap_idx, chap in enumerate(active):
        posts = classification.get(chap, [])
        if not posts:
            continue

        # Insert a quote interlude page between chapters (not before first)
        if chap_idx > 0 and quote_idx < len(_MEMORY_QUOTES):
            qt, attr = _MEMORY_QUOTES[quote_idx % len(_MEMORY_QUOTES)]
            _page_quote(c, W, H, qt, attr, fonts)
            c.showPage()
            quote_idx += 1

        # Chapter divider page
        _page_chapter_title(c, W, H, chap, chap_idx + 1, fonts)
        c.showPage()

        # Collect displayable images (with blob index fallback)
        items = []
        for p in posts:
            imgs = [u for u in (p.get("images") or []) if _is_displayable_image_ref(u)]
            # Fallback: if no displayable images, try blob index by post ID
            pid = str(p.get("id") or p.get("post_id") or "").strip()
            if not imgs and pid and pid in pdf_img_idx:
                imgs = [pdf_img_idx[pid]]
            # Resolve each URL to prefer Azure blob paths
            resolved_imgs = []
            for u in imgs:
                bp = _ours_blob_path(u)
                if bp:
                    resolved_imgs.append(bp)
                elif pid and pid in pdf_img_idx:
                    resolved_imgs.append(pdf_img_idx[pid])
                else:
                    resolved_imgs.append(u)
            msg  = _cap(p.get("message", ""))
            ctx  = _cap(p.get("context_caption", ""))
            cap  = compose_caption(msg, ctx)
            date = p.get("created_time", "")
            for u in resolved_imgs[:2]:
                items.append({"img": u, "caption": cap, "date": date})

        # Varied layout pattern for visual diversity:
        # Hero(1) → Grid(4) → Trio(3) → Grid(4) → Duo(2) → repeat
        _LAYOUT_PATTERN = [1, 4, 3, 4, 2]
        idx = 0
        pat_pos = 0
        while idx < len(items):
            batch_size = _LAYOUT_PATTERN[pat_pos % len(_LAYOUT_PATTERN)]
            remaining = len(items) - idx
            if remaining <= batch_size + 1:
                batch_size = remaining
            batch = items[idx:idx + batch_size]
            _page_photos(c, W, H, chap, batch, page_num, fonts)
            c.showPage()
            page_num += 1
            idx += batch_size
            pat_pos += 1

    # ── Back cover ─────────────────────────────────────────────
    _page_back_cover(c, W, H, fonts)
    c.showPage()

    c.save()
    val = buffer.getvalue()
    buffer.close()
    return val

@st.cache_data(show_spinner=False)
def _build_pdf_cached(classification, chapters, blob_folder, profile_summary, template, _ck, user_name=None):
    return build_pdf_bytes(classification, chapters, blob_folder, profile_summary, template, user_name=user_name)

def _scrapbook_ck(classification, chapters, blob_folder, template):
    raw = json.dumps([classification, chapters, blob_folder, template], sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()

# ── MAIN UI ───────────────────────────────────────────────────────────────────
st.sidebar.markdown("### ⚙️ Settings")
if st.sidebar.button("🔄 Reload Posts"):
    st.cache_data.clear(); st.rerun()

# ── Guard: if a paid scrapbook PDF already exists, block re-generation ────────
_existing_paid = False
_existing_pdf = False
try:
    _existing_paid = container_client.get_blob_client(f"{blob_folder}/.paid.scrapbook").exists()
    _existing_pdf = container_client.get_blob_client(f"{blob_folder}/scrapbook.pdf").exists()
except Exception:
    pass

if _existing_paid and _existing_pdf:
    st.markdown(f"""
    <div class="mem-header">
      <div class="eyebrow">✦ &nbsp; Your Story &nbsp; ✦</div>
      <h1>Facebook <span class="gold">Memories</span></h1>
    </div>
    """, unsafe_allow_html=True)
    st.info("A scrapbook already exists for this backup. Go to **Projects** to download it, or delete the backup there first to create a new one.")
    col_l, col_c, col_r = st.columns([1.5, 2, 1.5])
    with col_c:
        if st.button("📘 Go to Projects", use_container_width=True, type="primary"):
            st.switch_page("pages/Projects.py")
    st.stop()

if _existing_paid and not _existing_pdf:
    # Paid but PDF not built yet — try to build from persisted data
    try:
        _cls_blob = container_client.get_blob_client(f"{blob_folder}/scrapbook_classification.json")
        if _cls_blob.exists():
            with st.spinner("Building your scrapbook PDF..."):
                _cls = json.loads(_cls_blob.download_blob().readall().decode("utf-8"))
                _chaps = json.loads(container_client.get_blob_client(
                    f"{blob_folder}/scrapbook_chapters.json").download_blob().readall().decode("utf-8"))
                _sum_b = container_client.get_blob_client(f"{blob_folder}/scrapbook_summary.txt")
                _sum = _sum_b.download_blob().readall().decode("utf-8") if _sum_b.exists() else ""
                _name = st.session_state.get("fb_name")
                _pdf = build_pdf_bytes(_cls, _chaps, blob_folder, _sum, "polaroid", user_name=_name)
                from azure.storage.blob import ContentSettings as _CS
                container_client.get_blob_client(f"{blob_folder}/scrapbook.pdf").upload_blob(
                    _pdf, overwrite=True, content_settings=_CS(content_type="application/pdf"))
            st.success("Your scrapbook PDF is ready!")
            col_l, col_c, col_r = st.columns([1.5, 2, 1.5])
            with col_c:
                if st.button("📘 Go to Projects to Download", use_container_width=True, type="primary"):
                    st.switch_page("pages/Projects.py")
            st.stop()
    except Exception:
        pass  # Fall through to normal generation flow

st.caption("Loading your Facebook posts from storage…")
try:
    posts = load_all_posts_from_blob(CONTAINER, blob_folder)
    if not posts and has_posts_permission:
        with st.spinner("📥 Fetching your posts..."):
            posts = fetch_posts_from_api(st.session_state["fb_token"])
            if posts:
                save_posts_to_blob(posts, blob_folder)
                load_all_posts_from_blob.clear()
                st.rerun()
except Exception as e:
    st.error(f"❌ Error: {e}"); st.stop()

if not posts:
    st.warning("⚠️ No posts found. Try refreshing or check permissions.")
    st.stop()

st.session_state["all_posts_raw"] = posts

# ── Page hero ────────────────────────────────────────────────
user_display = st.session_state.get("fb_name", "").split()[0] if st.session_state.get("fb_name") else ""
st.markdown(f"""
<div class="mem-header">
  <div class="eyebrow">✦ &nbsp; Your Story &nbsp; ✦</div>
  <h1>Facebook <span class="gold">Memories</span></h1>
  <p class="sub">{"Hello " + user_display + " — your" if user_display else "Your"} cherished moments, beautifully organised into a personal storybook.</p>
</div>
""", unsafe_allow_html=True)

if "classification" not in st.session_state:
    # Pre-generation landing state
    post_count  = len(posts)
    img_count   = sum(1 for p in posts for u in (p.get("images") or []) if _is_displayable_image_ref(u))
    year_set    = set()
    for p in posts:
        try: year_set.add(datetime.fromisoformat((p.get("created_time") or "").replace("Z","+00:00")).year)
        except: pass
    span = f"{min(year_set)}–{max(year_set)}" if len(year_set) > 1 else (str(list(year_set)[0]) if year_set else "—")

    st.markdown(f"""
    <div class="gen-card">
      <span class="icon">📖</span>
      <h2>Ready to build your Scrapbook?</h2>
      <p>We'll analyse your posts, discover your story's themes, and organise your photos into beautiful chapters — all with AI.</p>
      <div class="stat-row">
        <div class="stat"><div class="val">{post_count}</div><div class="lbl">Posts</div></div>
        <div class="stat"><div class="val">{img_count}</div><div class="lbl">Photos</div></div>
        <div class="stat"><div class="val">{span}</div><div class="lbl">Years</div></div>
      </div>
      <div class="steps">
        <span>🔍 Personality analysis</span>
        <span>📚 Chapter themes</span>
        <span>🖼️ Photo classification</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([1.8, 2, 1.8])
    with col_c:
        if st.button("✨ Generate My Scrapbook", use_container_width=True, type="primary"):
            if not has_posts_permission:
                auth_url = build_posts_auth_url()
                q = chr(34)
                redirect_meta = f"<meta http-equiv={q}refresh{q} content={q}0; url={auth_url}{q}>"
                st.markdown(redirect_meta, unsafe_allow_html=True)
                st.stop()

            with st.spinner("🔍 Evaluating your personality and life themes..."):
                user_name = st.session_state.get("fb_name", "this person")
                user_gender = st.session_state.get("fb_gender", "unspecified").lower()
                if user_gender == "female": p_sub, p_obj, p_pos = "she", "her", "her"
                elif user_gender == "male": p_sub, p_obj, p_pos = "he", "him", "his"
                else: p_sub, p_obj, p_pos = "they", "them", "their"

                surname = re.split(r"[ _]+", (user_name or "").strip())[-1] if user_name else ""
                surname_data = {}
                if surname:
                    try:
                        r = requests.post(f"{FUNCTION_BASE}/surname_insight", json={"surname": surname}, timeout=8)
                        if r.status_code == 200:
                            surname_data = r.json()
                            st.session_state["surname_insight"] = surname_data
                    except: pass

                def _surname_preface(d) -> str:
                    if not isinstance(d, dict) or not d.get("surname"):
                        return ""
                    sn = d.get("surname", "")
                    lines = ["🔎 **Surname insight: " + sn + "**"]
                    om = d.get("origin_meaning", "")
                    ge = d.get("geography_ethnicity", "")
                    ch = d.get("cultural_historical", "")
                    if om: lines.append("- Origin: " + om)
                    if ge: lines.append("- Ties: " + ge)
                    if ch: lines.append("- History: " + ch)
                    return "\n".join(lines)

                surname_preface = _surname_preface(surname_data)
                eval_prompt = f"""First, present the following surname insight block verbatim if provided:
                {surname_preface}

                Then, write a warm, reflective scrapbook personality summary for {user_name} based on their Facebook post history.

                ⚠️ IMPORTANT:
                - The first sentence MUST start with "{user_name}".
                - Use these pronouns naturally: Subject: {p_sub}, Object: {p_obj}, Possessive: {p_pos}.
                - Consider emotional tone, recurring values, life priorities, and mindset.
                - Make it sound personal and meaningful, like it’s written for a legacy scrapbook."""

                res_eval = call_function("ask_about_blob", {
                    "question": eval_prompt,
                    "posts": posts[:300],
                    "filename": f"{blob_folder}/posts.json"
                })
                profile_summary = res_eval.text
                st.session_state["profile_summary"] = profile_summary

            with st.spinner("📚 Generating tailored scrapbook chapters..."):
                res_chapters = call_function("ask_followup_on_answer", {
                    "previous_answer": profile_summary,
                    "question": """Suggest 6–12 practical, post-grounded chapter titles.
                    Avoid abstract themes. Keep titles short (3-5 words).
                    Return JSON only: {"chapters": ["Title 1", "Title 2", ...]}""",
                    "format": "json"
                })
                chapters = parse_chapters_strict(res_chapters.text) or ["Life Highlights", "Family & Friends", "Travel Adventures"]

            with st.spinner("🧩 Organizing your memories across chapters..."):
                res = call_function("embed_classify_posts_into_chapters", {
                    "chapters": chapters,
                    "user_prefix": blob_folder,
                    "posts": posts,
                    "max_per_chapter": 8,
                    "min_per_chapter": 2,
                    "min_match": 0.12,
                    "balance_by_year": True,
                    "max_images_per_post": 2
                })
                cls = _scrub_classification(res.json())
                st.session_state["classification"] = cls
                st.session_state["chapters"] = [c for c in chapters if cls.get(c)]

                # Persist scrapbook data to blob so it survives Stripe redirect
                try:
                    container_client.get_blob_client(f"{blob_folder}/scrapbook_classification.json").upload_blob(
                        json.dumps(cls, ensure_ascii=False).encode("utf-8"), overwrite=True)
                    container_client.get_blob_client(f"{blob_folder}/scrapbook_chapters.json").upload_blob(
                        json.dumps(st.session_state["chapters"], ensure_ascii=False).encode("utf-8"), overwrite=True)
                    container_client.get_blob_client(f"{blob_folder}/scrapbook_summary.txt").upload_blob(
                        (profile_summary or "").encode("utf-8"), overwrite=True)
                except Exception:
                    pass

                st.rerun()

else:
    cls = st.session_state["classification"]
    active_chapters = [c for c in st.session_state.get("chapters", []) if cls.get(c)]
    roman = ["I","II","III","IV","V","VI","VII","VIII","IX","X","XI","XII"]

    # ── Heritage card ─────────────────────────────────────────
    si = st.session_state.get("surname_insight")
    if si and si.get("surname"):
        _si_name    = si.get("surname", "")
        _si_origin  = ("<strong>Origin:</strong> " + si.get("origin_meaning", "") + "<br>") if si.get("origin_meaning") else ""
        _si_ties    = ("<strong>Ties:</strong> " + si.get("geography_ethnicity", "") + "<br>") if si.get("geography_ethnicity") else ""
        _si_history = si.get("cultural_historical", "") or ""
        st.markdown(f"""
        <div class="heritage-card">
          <div class="icon-col">🏛️</div>
          <div>
            <div class="label">Family Heritage</div>
            <div class="name">{_si_name} Family</div>
            <div class="detail">{_si_origin}{_si_ties}{_si_history}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Memory Snapshot ───────────────────────────────────────
    if st.session_state.get("profile_summary"):
        st.markdown("""
        <div class="snapshot-label">
          <span>✦</span><span>Memory Snapshot</span><span>✦</span>
        </div>
        """, unsafe_allow_html=True)
        _profile_text = st.session_state.get("profile_summary", "")
        st.markdown(f"""
        <div class="snapshot-card">
          <p>{_profile_text}</p>
        </div>
        """, unsafe_allow_html=True)

        # ── Coverage meter ─────────────────────────────────────
        used, total = _coverage(posts, cls)
        pct = int((used / total) * 100) if total else 0
        st.markdown(f"""
        <div class="coverage-wrap">
          <div class="icon">🖼️</div>
          <div class="text">
            <div class="title">Scrapbook Coverage</div>
            <div class="coverage-track">
              <div class="coverage-fill" style="width:{pct}%"></div>
            </div>
          </div>
          <div class="coverage-count">{used}<span style="font-size:.75rem;color:#8a99b8;font-weight:400"> / {total}</span></div>
        </div>
        """, unsafe_allow_html=True)

    # ── Chapter TOC pills ─────────────────────────────────────
    if active_chapters:
        pills_html = "".join(
            "<span class=’chap-pill’><span class=’num’>" + (roman[i] if i < 12 else str(i + 1)) + "</span>" + chap + "</span>"
            for i, chap in enumerate(active_chapters)
        )
        st.markdown(f"""
        <div class="toc-section">
          <div class="toc-label"><span>Chapters in this Scrapbook</span></div>
          <div class="chapter-pills">{pills_html}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Chapter sections ──────────────────────────────────────
    for i, chap in enumerate(active_chapters):
        num = roman[i] if i < 12 else str(i + 1)
        st.markdown(f"""
        <div class="chapter-divider">
          <div class="chap-num-badge">{num}</div>
          <div class="chap-title-text">{chap}</div>
          <div class="chap-rule"></div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div class=’photo-grid-wrap’>", unsafe_allow_html=True)
        render_chapter_post_images(chap, cls[chap], cls, FUNCTION_BASE)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Download / Purchase CTA ──────────────────────────────
    paid_for_scrapbook = _scrapbook_is_paid(blob_folder) or st.session_state.get("scrapbook_paid", False)

    if paid_for_scrapbook:
        # User has paid → build PDF and show download button
        chapters_list = st.session_state.get("chapters", list(cls.keys()))
        summary = st.session_state.get("profile_summary", "")
        if st.session_state.get("pdf_dirty", True) or not st.session_state.get("pdf_bytes"):
            with st.spinner("📄 Building your scrapbook PDF…"):
                try:
                    ck = _scrapbook_ck(cls, chapters_list, blob_folder, "polaroid")
                    _fb_display_name = st.session_state.get("fb_name") or None
                    pdf = _build_pdf_cached(cls, chapters_list, blob_folder, summary, "polaroid", ck, user_name=_fb_display_name)
                    st.session_state["pdf_bytes"] = pdf
                    st.session_state["pdf_dirty"] = False
                    # Also persist to blob for download from Projects page
                    try:
                        from azure.storage.blob import ContentSettings as _CS2
                        container_client.get_blob_client(f"{blob_folder}/scrapbook.pdf").upload_blob(
                            pdf, overwrite=True, content_settings=_CS2(content_type="application/pdf"))
                    except Exception:
                        pass
                except Exception as e:
                    st.error(f"PDF generation failed: {e}")

        pdf_data = st.session_state.get("pdf_bytes")
        if pdf_data:
            st.markdown("""
            <div class="dl-bar">
              <div class="dl-icon">📖</div>
              <div class="dl-text">
                <h3>Your Scrapbook is Ready</h3>
                <p>Download the beautifully formatted PDF — cover, chapters, and all your memories.</p>
              </div>
            </div>
            """, unsafe_allow_html=True)
            col_dl_l, col_dl_c, col_dl_r = st.columns([1.5, 2, 1.5])
            with col_dl_c:
                st.download_button(
                    "📥 Download PDF Scrapbook",
                    data=pdf_data,
                    file_name="scrapbook.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
    else:
        # User has NOT paid → show purchase CTA with inline Stripe checkout
        st.markdown("""
        <div class="dl-bar" style="border:2px solid var(--gold, #F6C35D);">
          <div class="dl-icon">📖</div>
          <div class="dl-text">
            <h3>Your Scrapbook is Ready</h3>
            <p>Purchase to download the beautifully formatted PDF — cover, chapters, and all your memories.</p>
          </div>
        </div>
        """, unsafe_allow_html=True)
        col_dl_l, col_dl_c, col_dl_r = st.columns([1.5, 2, 1.5])
        with col_dl_c:
            if st.button("📖 Buy the Scrapbook to Download PDF", use_container_width=True, type="primary"):
                # Persist scrapbook data to blob before redirect (survives Stripe roundtrip)
                try:
                    container_client.get_blob_client(f"{blob_folder}/scrapbook_classification.json").upload_blob(
                        json.dumps(cls, ensure_ascii=False).encode("utf-8"), overwrite=True)
                    container_client.get_blob_client(f"{blob_folder}/scrapbook_chapters.json").upload_blob(
                        json.dumps(st.session_state.get("chapters", list(cls.keys())), ensure_ascii=False).encode("utf-8"), overwrite=True)
                    container_client.get_blob_client(f"{blob_folder}/scrapbook_summary.txt").upload_blob(
                        (st.session_state.get("profile_summary", "") or "").encode("utf-8"), overwrite=True)
                except Exception:
                    pass
                try:
                    import stripe as _stripe_buy
                    _sk = st.secrets.get("STRIPE_SCRAPBOOK_SECRET_KEY") or st.secrets.get("STRIPE_SECRET_KEY")
                    _price = st.secrets.get("STRIPE_SCRAPBOOK_PRICE_ID", "price_1TMECpP1KF2yA8BHSVOrJU8O")
                    _success = st.secrets.get("STRIPE_SCRAPBOOK_SUCCESS_URL", "https://liveonfb.streamlit.app/FbMemories")
                    _cancel = st.secrets.get("STRIPE_SCRAPBOOK_CANCEL_URL", "https://liveonfb.streamlit.app/FbMemories")
                    if not _sk:
                        st.error("Stripe is not configured. Contact support.")
                    else:
                        _stripe_buy.api_key = _sk
                        # Build success URL with blob_folder, cache token, and session_id
                        _token = st.session_state.get("fb_token", "")
                        _cache_hash = hashlib.md5(_token.encode()).hexdigest() if _token else ""
                        _sep = "&" if "?" in _success else "?"
                        _success_full = f"{_success}{_sep}blob_folder={blob_folder}&cache={_cache_hash}&session_id={{CHECKOUT_SESSION_ID}}"
                        _checkout = _stripe_buy.checkout.Session.create(
                            payment_method_types=["card"],
                            line_items=[{"price": _price, "quantity": 1}],
                            mode="payment",
                            success_url=_success_full,
                            cancel_url=_cancel,
                            allow_promotion_codes=True,
                            metadata={
                                "fb_id": st.session_state.get("fb_id", ""),
                                "fb_name": st.session_state.get("fb_name", ""),
                                "blob_folder": blob_folder,
                                "product": "scrapbook",
                            },
                            customer_email=st.session_state.get("fb_email"),
                        )
                        st.link_button("Continue to Secure Checkout", _checkout.url, use_container_width=True)
                        st.caption("You'll be taken to Stripe to complete your payment.")
                except Exception as _e:
                    st.error(f"Error creating checkout: {_e}")
