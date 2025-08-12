# ======================
# FILE: FbeMyProjects.py
# ======================
import streamlit as st
import os
import json
from datetime import datetime
from pandas import DataFrame
from azure.storage.blob import BlobServiceClient
import requests  # ✅ Needed for Facebook Graph API calls
import hashlib  # ✅ Added for hashing fb_token for safe filenames
from pathlib import Path
DEBUG = str(st.secrets.get("DEBUG", "false")).strip().lower() == "true"
st.set_page_config(
    page_title="My Projects | Facebook Scrapbook",
    layout="wide",
    page_icon="📚",
    initial_sidebar_state="collapsed"
)
# 🔥 Hash token for safe cache filename
def safe_token_hash(token):
    return hashlib.md5(token.encode()).hexdigest()
def restore_session():
    """Restore session from per-user cache if available"""
    fb_token = st.session_state.get("fb_token")
    if fb_token:
        CACHE_DIR = Path("cache")
        cache_file = CACHE_DIR / f"backup_cache_{hashlib.md5(fb_token.encode()).hexdigest()}.json"

        # Try to find any cache file
        for f in Path(".").glob("cache/backup_cache_*.json"):
            try:
                with open(f, "r") as file:
                    cached = json.load(file)
                    if "fb_token" in cached:
                        st.session_state.update({
                            "fb_token": cached.get("fb_token"),
                            "fb_id": cached.get("latest_backup", {}).get("user_id"),
                            "fb_name": cached.get("latest_backup", {}).get("Name"),
                            "latest_backup": cached.get("latest_backup"),
                            "new_backup_done": cached.get("new_backup_done"),
                            "new_project_added": cached.get("new_project_added")
                        })
                        break
            except Exception as e:
                st.error(f"Error restoring from {f}: {e}")

            

restore_session()

if DEBUG:
    st.warning(f"🧠 Session loaded: fb_id={st.session_state.get('fb_id')}")
    st.warning(f"🧠 latest_backup={st.session_state.get('latest_backup')}")
    st.warning(f"🧠 new_backup_done={st.session_state.get('new_backup_done')}")

if st.session_state.pop("force_reload", False):  # 👈 ADD THIS
    st.rerun()  # ✅ For Streamlit >=1.30, use st.rerun
# 🛡 Ensure required session keys exist
for key in ["fb_token", "fb_id", "fb_name"]:
    if key not in st.session_state:
        st.session_state[key] = None



@st.cache_resource
def get_blob_service_client():
    AZ_CONN = st.secrets.get("AZURE_CONNECTION_STRING") or os.getenv("AZURE_CONNECTION_STRING")
    if AZ_CONN:
        return BlobServiceClient.from_connection_string(AZ_CONN)
    return None
if get_blob_service_client() is None:
    st.error("Missing AZURE_CONNECTION_STRING in Secrets. Set it in Streamlit Cloud → Settings → Secrets.")
    st.stop()

# Set up Azure container client
blob_service_client = get_blob_service_client()
container_client = blob_service_client.get_container_client("backup")

# Prepare paths early for reloads
user_folder = f"{st.session_state['fb_id']}/projects"
projects_blob_path = f"{user_folder}/projects_{st.session_state['fb_id']}.json"



# 🔥 Force reload all backups and projects after redirect
if st.session_state.get("redirect_to_projects", False) or st.session_state.get("new_project_added", False):
    st.session_state["redirect_to_projects"] = False  # reset flag
    st.session_state["new_project_added"] = False     # reset flag
    blob_client = container_client.get_blob_client(projects_blob_path)
    try:
        if blob_client.exists():
            all_projects = json.loads(blob_client.download_blob().readall().decode("utf-8"))
            projects.clear()  # clear old list
            for proj in all_projects:
                backup_folder = proj.get("backup_folder", "")
                summary_blob = container_client.get_blob_client(f"{backup_folder}/summary.json")
                proj["status"] = "Ready" if summary_blob.exists() else "⚠️ Backup Missing"
                if not any(p["id"] == proj["id"] for p in projects):
                    projects.append(proj)

    except Exception as e:
        if DEBUG: st.warning(f"⚠️ Could not refresh projects: {e}")



# ✅ Refresh Facebook user details from API
if "fb_token" in st.session_state:
    try:
        profile = requests.get(
            f"https://graph.facebook.com/me?fields=id,name,email&access_token={st.session_state['fb_token']}"
        ).json()
        st.session_state["fb_id"] = str(profile.get("id")).strip()
        st.session_state["fb_name"] = profile.get("name")
    except Exception as e:
        st.error(f"Failed to refresh Facebook user info: {e}")
        st.stop()
missing_keys = [k for k in ["fb_id", "fb_name", "fb_token"] if k not in st.session_state]
if missing_keys:
    st.warning(f"⚠️ Missing session keys: {missing_keys}")
    st.stop()
# ─── Tab Handling ───────────────────────────────────
# Get query parameters and set default tab
query_params = st.query_params
if st.session_state.pop("redirect_to_projects", False):
    default_tab = "projects"
elif st.session_state.pop("redirect_to_backups", False):
    default_tab = "backups"
else:
    default_tab = query_params.get("tab", "backups")


# ─── Facebook Session Variables ───────────────────────

query_params = st.query_params
if "edit_duration" in query_params:
    folder_name = query_params["edit_duration"][0]
    if DEBUG: st.info(f"Editing folder passed from dashboard: {folder_name}")
    if folder_name and folder_name != "f":  # ✅ Prevent invalid folder names
        st.session_state["editing_backup_folder"] = folder_name
        st.switch_page("pages/FbFullProfile.py")
    else:
        st.error("❌ Invalid folder passed. Please select a valid backup.")
if "generate_memories" in query_params:
    st.session_state["selected_backup"] = query_params["generate_memories"][0]
    st.switch_page("pages/FbMemories.py")
# Custom CSS with modern design
st.markdown("""
<style>
:root{
  --navy-900:#0F253D;     /* deep background */
  --navy-800:#143150;
  --navy-700:#1E3A5F;
  --navy-500:#2F5A83;
  --gold:#F6C35D;         /* brand accent */
  --text:#F3F6FA;         /* off-white text */
  --muted:#B9C6D6;        /* secondary text */
  --card:#112A45;         /* card bg */
  --line:rgba(255,255,255,.14);
}

/* App background + base typography */
html, body, .stApp{
  background: linear-gradient(180deg, var(--navy-900) 0%, var(--navy-800) 55%, var(--navy-700) 100%);
  color: var(--text);
  font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

/* Headings */
h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3{
  color: var(--text) !important;
  letter-spacing:.25px;
}

/* Primary buttons (Streamlit buttons) */
.stButton>button,
.stDownloadButton button{
  background: var(--gold) !important;
  color: var(--navy-900) !important;
  border: none !important;
  border-radius: 10px !important;
  padding: 10px 16px !important;
  font-weight: 800 !important;
  box-shadow: 0 4px 14px rgba(246,195,93,.22) !important;
  transition: transform .15s ease, filter .15s ease, box-shadow .15s ease !important;
}
.stButton>button:hover,
.stDownloadButton button:hover{
  transform: translateY(-1px);
  filter: brightness(.95);
  box-shadow: 0 6px 18px rgba(246,195,93,.28) !important;
}

/* Tabs */
div[data-testid="stTabs"]{
  border-bottom: 1px solid var(--line);
  margin-bottom: 12px;
}
div[data-testid="stTabs"] button{
  color: var(--muted) !important;
  background: transparent !important;
  border: 0 !important;
  padding-bottom: 10px !important;
}
div[data-testid="stTabs"] button[aria-selected="true"]{
  color: var(--text) !important;
  border-bottom: 3px solid var(--gold) !important;
}

/* Cards */
.card{
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 12px;
  box-shadow: 0 10px 24px rgba(0,0,0,.18);
  padding: 24px;
  margin-bottom: 24px;
  transition: transform .2s ease, box-shadow .2s ease;
}
.card:hover{ transform: translateY(-2px); }

/* Page header (title + user badge) */
.header{
  display:flex; justify-content:space-between; align-items:center;
  margin-bottom:32px; padding-bottom:16px; border-bottom:1px solid var(--line);
}
.header p{ color: var(--muted) !important; }

.user-badge{
  display:flex; align-items:center; gap:12px;
  background: rgba(255,255,255,.06);
  padding:10px 16px; border-radius: 50px;
  box-shadow: 0 2px 8px rgba(0,0,0,.12);
}
.avatar{
  width:40px; height:40px; border-radius:50%;
  background: var(--gold);
  display:flex; align-items:center; justify-content:center;
  color: var(--navy-900); font-weight: 900;
}

/* “Empty state” sections */
.empty-state{
  text-align:center; padding: 40px 20px;
  background: rgba(255,255,255,.06);
  border-radius: 12px;
  border: 1px dashed var(--line);
  color: var(--muted);
}
.empty-state-icon{ font-size:48px; margin-bottom:16px; color: var(--gold); }

/* Captions, small text */
p, span, label, .stCaption, .stMarkdown, .st-emotion-cache-1n76uvr{
  color: var(--muted) !important;
}

/* Download buttons inside the list */
.stDownloadButton{ display:inline-block !important; vertical-align:middle; }

/* Alert styling to match theme */
div[data-testid="stAlert"]{
  border-left:4px solid var(--gold) !important;
  background: rgba(255,255,255,.06) !important;
  color: var(--text) !important;
}
div[data-testid="stAlert"] *{ color: var(--text) !important; }

/* Small tweaks for columns list rows */
.css-ocqkz7, .css-1dp5vir{ background: transparent !important; }
</style>
""", unsafe_allow_html=True)

# ─── Authentication Check ──────────────────────
if not all(key in st.session_state for key in ["fb_id", "fb_name", "fb_token"]):
    st.warning("Please log in to access your projects.")
    if st.button("🔑 Go to Login"):
        st.switch_page("LiveOn.py")
    st.stop()
# Get user info from session with fallback
fb_id = st.session_state["fb_id"]
fb_name = st.session_state.get("fb_name")  # Default to "User" if none
fb_token = st.session_state["fb_token"]
# ─── Header with User Info ─────────────────────
st.markdown(f"""
<div class="header">
    <div>
        <h1 style="margin: 0;">My Projects</h1>
        <p style="color: #6c757d; margin: 4px 0 0 0;">Manage your Facebook backups and projects</p>
    </div>
    <div class="user-badge">
        <div class="avatar">
            {(fb_name or 'User')[0].upper()}
        </div>
        <div>
            <div style="font-weight: 600;">{fb_name}</div>
            <div style="font-size: 0.8em; color: #6c757d;">Account active</div>
        </div>
        <button onclick="window.location.href='/FacebookLogin'" style="
            background: none;
            border: none;
            color: #6c757d;
            cursor: pointer;
            padding: 8px;
            border-radius: 8px;
        ">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                <polyline points="16 17 21 12 16 7"></polyline>
                <line x1="21" y1="12" x2="9" y2="12"></line>
            </svg>
        </button>
    </div>
</div>
""", unsafe_allow_html=True)
# ─── Azure Storage Setup ───────────────────────


backups = []
# In the Azure Storage Setup section
if blob_service_client:
    try:
        container_client = blob_service_client.get_container_client("backup")
        blobs = list(container_client.list_blobs(name_starts_with=f"{st.session_state['fb_id']}/"))
        
        # Process backups with progress indicator
        # 🆕 Process user-specific backups
        with st.spinner("🔄 Loading your backups…"):
            user_id = str(st.session_state["fb_id"]).strip()
            for blob in blobs:
                if blob.name.endswith("summary.json"):
                    parts = blob.name.split("/")
                    if len(parts) >= 2:
                        folder_fb_id = parts[0].strip()
                        folder_name = parts[1].strip()
                        # ✅ Skip any folders inside /projects/
                        if folder_fb_id == user_id and not folder_name.startswith("projects/"):
                            try:
                                summary_blob = container_client.get_blob_client(blob.name)
                                summary = json.loads(summary_blob.download_blob().readall().decode("utf-8"))
                                posts_blob_path = f"{folder_fb_id}/{folder_name}/posts+cap.json"
                                posts_blob = container_client.get_blob_client(posts_blob_path)
                                if posts_blob.exists():
                                    created_date = datetime.fromisoformat(summary.get("timestamp", "2000-01-01"))
                                    backups.append({
                                        "id": f"{folder_fb_id}/{folder_name}",
                                        "name": summary.get("user") or folder_name.replace("_", " "),
                                        "date": created_date.strftime("%b %d, %Y"),
                                        "posts": summary.get("posts", 0),
                                        "status": "Completed",
                                        "raw_date": created_date
                                    })
                            except Exception as e:
                                if DEBUG: st.warning(f"⚠️ Error reading backup in {blob.name}: {e}")
            
            # Process each folder
            for backup in backups:
                try:
                    summary_blob = container_client.get_blob_client(f"{backup['id']}/summary.json")
                    posts_blob = container_client.get_blob_client(f"{backup['id']}/posts+cap.json")
                    if summary_blob.exists():
                        summary = json.loads(summary_blob.download_blob().readall().decode("utf-8"))
                        # Strict user ID matching
                        backup_user_id = str(summary.get("user_id", "")).strip()
                        current_user_id = str(st.session_state["fb_id"]).strip()
                        if backup_user_id == current_user_id and posts_blob.exists():
                            created_date = datetime.fromisoformat(summary.get("timestamp", "2000-01-01"))
                            # Add to backups if not already present
                            folder_normalized = backup['id'].lower().strip()
                            if not any(b["id"].lower().strip() == folder_normalized for b in backups):
                                backups.append({
                                    "id": backup['id'],
                                    "name": summary.get("user") or backup['id'].replace("_", " "),
                                    "date": created_date.strftime("%b %d, %Y"),
                                    "posts": summary.get("posts", 0),
                                    "status": "Completed",
                                    "raw_date": created_date
                                })
                except Exception as e:
                    if DEBUG: st.warning(f"⚠️ Error processing backup {backup['id']}: {str(e)}")
                    continue

        # Sort backups by date (newest first)
        backups.sort(key=lambda x: x["raw_date"], reverse=True)
    except Exception as e:
        st.error(f"Azure connection error: {e}")


# ─── Projects Management ───────────────────────
projects = []
user_folder = f"{fb_id}/projects"
projects_blob_path = f"{user_folder}/projects_{fb_id}.json"
# 🔥 Always fetch projects fresh from Azure
try:
    blob_client = container_client.get_blob_client(projects_blob_path)
    projects = []  # Start fresh
    if blob_client.exists():
        all_projects = json.loads(blob_client.download_blob().readall().decode("utf-8"))
        for proj in all_projects:
            backup_folder = proj.get("backup_folder", "")
            summary_blob = container_client.get_blob_client(f"{backup_folder}/summary.json")
            # ✅ Add project even if backup folder is missing
            if summary_blob.exists():
                proj["status"] = "Ready"
            else:
                proj["status"] = "⚠️ Backup Missing"
            # ✅ Avoid duplicates using project id
            if not any(p["id"] == proj["id"] for p in projects):
                projects.append(proj)
    else:
        if DEBUG: st.info("No projects metadata found in Azure.")
except Exception as e:
    st.error(f"❌ Error loading projects from Azure: {e}")



# Handle new backup if redirected
if st.session_state.pop("new_backup_done", False):
    latest = st.session_state.pop("latest_backup", None)
    if DEBUG: st.info(f"✅ Attempting to add new backup: {latest}")
    if latest and str(latest.get("user_id")).strip() == str(st.session_state["fb_id"]).strip():
        folder = latest.get("Folder").rstrip("/").lower()
        if blob_service_client:
            summary_blob = container_client.get_blob_client(f"{folder}/summary.json")
            posts_blob = container_client.get_blob_client(f"{folder}/posts+cap.json")
            if summary_blob.exists() and posts_blob.exists():
                # Skip if already exists
                if not any(b["id"].rstrip("/").lower() == folder for b in backups):
                    backups.insert(
                        0,
                        {
                            "id": folder,
                            "name": latest.get("Name", "Unnamed Backup"),
                            "date": latest.get("Created On", "Unknown"),
                            "posts": latest.get("# Posts", 0),
                            "status": "Completed",
                            "raw_date": datetime.now()
                        }
                    )
                    if DEBUG: st.info(f"✅ Added session backup: {folder}")
            else:
                if DEBUG: st.info(f"🚫 Skipped session backup (missing files): {folder}")
# ─── Handle new project creation ────────────────────────
# 🚀 Always load latest projects from Azure
try:
    blob_client = container_client.get_blob_client(projects_blob_path)
    projects.clear()
    if blob_client.exists():
        all_projects = json.loads(blob_client.download_blob().readall().decode("utf-8"))
        for proj in all_projects:
            backup_folder = proj.get("backup_folder", "")
            summary_blob = container_client.get_blob_client(f"{backup_folder}/summary.json")
            if summary_blob.exists():
                proj["status"] = "Ready"
            else:
                proj["status"] = "⚠️ Backup Missing"
            # Avoid duplicates
            if not any(p["id"] == proj["id"] for p in projects):
                projects.append(proj)
except Exception as e:
    st.error(f"❌ Error loading projects: {e}")

            
# ─── Main Content ──────────────────────────────
# Update the tabs creation:
tab1, tab2, tab3 = st.tabs(["📦 My Backups", "📚 My Projects", "📦 Orders"])
active_tab = default_tab  # This will control which tab opens by default
# Later in the code where you create tabs:
with tab1 if active_tab == "backups" else tab2 if active_tab == "projects" else tab3:
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("＋ New Backup", type="primary", use_container_width=True):
            st.switch_page("pages/FbFullProfile.py")
    
    if backups:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        
        # Enhanced backup table
        for backup in backups:
            cols = st.columns([3, 1, 1, 1, 3])
            with cols[0]:
                st.markdown(f"**{backup['name']}**")
                st.caption(f"ID: {backup['id']}")
            with cols[1]:
                st.markdown(f"**{backup['posts']}**")
                st.caption("Posts")
            with cols[2]:
                st.markdown(f"**{backup['date']}**")
                st.caption("Created")
            with cols[3]:
                st.caption("Actions")
            with cols[4]:
                posts_blob_path = f"{backup['id']}/posts+cap.json"
                try:
                    if blob_service_client:
                        blob_client = container_client.get_blob_client(posts_blob_path)
                        blob_client.get_blob_properties()  # Check existence
                        blob_data = blob_client.download_blob().readall()
                        st.download_button(
                            label="📥 Download JSON",
                            data=blob_data,
                            file_name=f"{backup['id']}.json",
                            mime="application/json",
                            use_container_width=True
                        )
                except Exception:
                    st.caption("No posts file available to download.")
                # Use Streamlit buttons instead of HTML links
                edit_col, memories_col = st.columns([1, 1])
                with edit_col:
                    if st.button("✂️ Edit Duration", key=f"edit_{backup['id']}", type="primary"):
                        st.session_state["editing_backup_folder"] = backup['id']
                        st.switch_page("pages/FbFullProfile.py")
                with memories_col:
                    if st.button("📘 Generate Memories", key=f"memories_{backup['id']}", type="primary"):
                        st.session_state["selected_backup"] = backup['id']
                        st.switch_page("pages/FbMemories.py")
            st.divider()
        
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">📂</div>
            <h3>No backups yet</h3>
            <p>Create your first backup to get started</p>
            <button class="stButton primary" onclick="window.location.href='/FbFullProfile'">Create Backup</button>
        </div>
        """, unsafe_allow_html=True)
with tab2:
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("＋ New Project", type="primary", use_container_width=True):
            st.switch_page("pages/FbMemories.py")
    
    if projects:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        for i, project in enumerate(projects):  # Add enumerate to get index
            cols = st.columns([3, 1, 1, 1])
            with cols[0]:
                st.markdown(f"**{project.get('name', 'Unnamed Project')}**")
                st.caption(project.get('description', 'No description'))
            with cols[1]:
                st.markdown(f"**{project.get('status', 'Draft')}**")
                st.caption("Status")
            with cols[2]:
                st.markdown(f"**{project.get('created', 'Unknown')}**")
                st.caption("Created")
            with cols[3]:
                edit_col, memories_col = st.columns([1, 1])
                with edit_col:
                    if st.button("📝 Edit Project", key=f"edit_project_{project.get('id')}_{i}"):
                        st.session_state.selected_project = project.get('id')
                        st.switch_page("pages/FbProjectEditor.py")
                with memories_col:
                    if st.button("📘 Generate Memories", key=f"memories_project_{project.get('id')}_{i}"):
                        st.session_state["selected_project"] = project.get("id")
                        st.switch_page("pages/FbMemories.py")
            st.divider()
        st.markdown("</div>", unsafe_allow_html=True)
    if isinstance(projects, list) and len(projects) == 0:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">📝</div>
            <h3>No projects yet</h3>
            <p>Start a new project from one of your backups</p>
        </div>
        """, unsafe_allow_html=True)

with tab3:
    orders = st.session_state.get("orders", [
        {"id": "56781", "product": "Hardcover Scrapbook", "status": "In Printing", "date": "2023-11-15"},
        {"id": "56724", "product": "PDF Scrapbook", "status": "Delivered", "date": "2023-10-28"},
    ])
    
    if orders:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        for order in orders:
            status_color = {
                "Delivered": "green",
                "In Printing": "orange",
                "Processing": "blue"
            }.get(order['status'], "gray")
            
            cols = st.columns([1, 2, 1, 1, 1])
            with cols[0]:
                st.markdown(f"**#{order['id']}**")
            with cols[1]:
                st.markdown(f"**{order['product']}**")
            with cols[2]:
                st.markdown(f"**{order['date']}**")
            with cols[3]:
                st.markdown(f"<span style='color: {status_color}; font-weight: bold;'>{order['status']}</span>", 
                          unsafe_allow_html=True)
            with cols[4]:
                if st.button("Track", key=f"track_{order['id']}"):
                    st.session_state.selected_order = order['id']
                    st.switch_page("pages/OrderTracker.py")
            
            st.divider()
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">📦</div>
            <h3>No orders yet</h3>
            <p>Your order history will appear here</p>
        </div>
        """, unsafe_allow_html=True)
