# FILE: utils/theme.py

# FILE: utils/theme.py
def inject_global_styles():
    import streamlit as st
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    :root{
      /* === Brand tokens === */
      --brand-color: #4B72E0;          /* primary */
      --brand-color-600: #3654b6;      /* hover */
      --accent: #0EA5E9;               /* accent / links */
      --success: #16a34a;
      --warning: #f59e0b;
      --danger:  #dc2626;

      /* === Surface & text === */
      --bg: #f7f8fb;                   /* app background */
      --card: #ffffff;                 /* cards */
      --card-border: #e9edf3;
      --shadow: 0 6px 24px rgba(16,24,40,.06);
      --text: #101828;                 /* primary text */
      --muted: #475467;                /* secondary text */

      /* === Radii & spacing === */
      --radius: 12px;
      --radius-lg: 16px;
      --pad: 16px;

      /* === Font === */
      --font-family: 'Inter', -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
    }

    html, body, .stApp {
      background: var(--bg);
      font-family: var(--font-family);
      color: var(--text);
      line-height: 1.6;
    }

    .stButton>button{
      background: var(--brand-color);
      color:#fff;
      padding:12px 18px;
      border:none;
      border-radius: var(--radius);
      font-weight:600;
      box-shadow: var(--shadow);
      transition: transform .15s ease, background .2s ease, box-shadow .2s ease;
    }
    .stButton>button:hover{
      background: var(--brand-color-600);
      transform: translateY(-1px);
    }

    /* Cards */
    .card {
      background: white;
      padding: 24px;
      border-radius: 12px;
      margin-bottom: 24px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.05);
      border: 1px solid var(--card-border);
    }

    /* Titles */
    .section-title {
      font-size: 1.4rem;
      font-weight: 700;
      margin-top: 30px;
      margin-bottom: 10px;
    }
    .page-header {
      text-align: center;
      font-size: 2.2rem;
      font-weight: 800;
      margin-bottom: 1rem;
    }

    /* Info boxes */
    .info-box { background: #e7f1ff; border-left: 4px solid var(--brand-color); padding: 14px 20px; margin: 20px 0; font-size: 0.95rem; border-radius: 8px; }
    .success-box { background: #e6ffec; border-left: 4px solid #28a745; }
    .warning-box { background: #fff5e6; border-left: 4px solid #ffc107; }
    .error-box   { background: #ffe6e6; border-left: 4px solid #dc3545; }

    

    /* Cards grid */
    .grid-3{ display:grid; grid-template-columns: repeat(3,1fr); gap:16px; }
    @media (max-width: 1100px){ .grid-3{ grid-template-columns: repeat(2,1fr);} }
    @media (max-width: 700px){ .grid-3{ grid-template-columns: 1fr; } }

    /* Badge + muted */
    .badge{ display:inline-flex; align-items:center; gap:6px; padding:6px 10px; border-radius:999px; font-weight:600; font-size:.85rem; background:#eef2ff; color: var(--brand-color); }
    .muted{ color: var(--muted); }
    </style>
    """, unsafe_allow_html=True)
