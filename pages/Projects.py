# ======================
# FILE: FbeMyProjects.py
# ======================

import streamlit as st
import os
import json
from datetime import datetime
from pandas import DataFrame
from azure.storage.blob import BlobServiceClient
import base64
import requests
st.set_page_config(
    page_title="My Projects | Facebook Scrapbook",
    layout="wide",
    page_icon="📚",
    initial_sidebar_state="collapsed"
)


def restore_session():
    """Restore session from cache if available"""
    fb_token = st.session_state.get("fb_token")
    cache_file = f"backup_cache_{fb_token}.json" if fb_token else "backup_cache.json"
    if not all(key in st.session_state for key in ["fb_id", "fb_name", "fb_token"]):
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r") as f:
                    cached = json.load(f)
                    st.session_state.update({
                        "fb_token": cached.get("fb_token"),
                        "fb_id": cached.get("latest_backup", {}).get("user_id"), 
                        #"fb_name": cached.get("fb_name"),  # Default to "User" if none
                        "fb_name": cached.get("latest_backup", {}).get("name"),
                        "latest_backup": cached.get("latest_backup"),
                        "new_backup_done": cached.get("new_backup_done")
                    })
            except Exception as e:
                st.error(f"Session restore error: {str(e)}")

restore_session()

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

# ✅ Ensure all session variables are present
missing_keys = [k for k in ["fb_id", "fb_name", "fb_token"] if k not in st.session_state]
if missing_keys:
    st.warning(f"⚠️ Missing session keys: {missing_keys}")
    st.stop()

# ─── Facebook Session Variables ───────────────────────
fb_id = st.session_state["fb_id"]
fb_name = st.session_state["fb_name"]
fb_token = st.session_state["fb_token"]
query_params = st.query_params
order_status = (query_params.get("order") or [None])[0]

if "order" in query_params and query_params["order"][0] == "success":
    st.markdown(
        """
        <div style='background-color:#d4edda;padding:15px;border-radius:8px;
        border:1px solid #c3e6cb;color:#000;'>
        🎉 Your order was successful! Thank you.
        </div>
        """,
        unsafe_allow_html=True
    )
elif "order" in query_params and query_params["order"][0] == "cancel":
    st.warning("❌ Your order was cancelled.")
if "edit_duration" in query_params:
    st.session_state["editing_backup_folder"] = query_params["edit_duration"][0]
    st.switch_page("pages/FbFullProfile.py")
# if "generate_memories" in query_params:
#     st.session_state["selected_backup"] = query_params["generate_memories"][0]
#     st.switch_page("pages/FbMemories.py")

# Custom CSS with modern design
st.markdown("""
<style>
            
    :root {
        --primary: #4361ee;
        --secondary: #3f37c9;
        --accent: #4895ef;
        --light: #f8f9fa;
        --dark: #212529;
        --success: #4cc9f0;
        --warning: #f72585;
    }
    
    html, body, .stApp {
        background: #f5f7fb;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: var(--dark);
        line-height: 1.6;
    }
    
    .stButton>button {
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .stButton>button.primary {
        background: var(--primary);
        color: white;
    }
    div[data-testid="stTabs"] button {
    color: var(--dark) !important;
    }
    .stButton>button.primary:hover {
        background: var(--secondary);
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
        .download-actions {
        display: flex;
        gap: 10px;
        align-items: center;
        flex-wrap: wrap;
        margin-top: 8px;
    }
    .stDownloadButton {
        display: inline-block !important;
        vertical-align: middle;
    }
    .stDownloadButton button {
        width: auto !important;
        min-width: 140px;
        text-align: center;
        background: var(--primary);
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stDownloadButton button:hover {
        background: var(--secondary);
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    .stButton>button {
    background: var(--primary);
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
    transition: all 0.3s ease;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
.stButton>button:hover {
    background: var(--secondary);
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}
        .card {
        background: white;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        border: 1px solid #e9ecef;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.1);
    }
    
    h1, h2, h3 {
        color: var(--dark);
        font-weight: 700;
    }
    
    .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 32px;
        padding-bottom: 16px;
        border-bottom: 1px solid #e9ecef;
    }
    
    .user-badge {
        display: flex;
        align-items: center;
        gap: 12px;
        background: white;
        padding: 10px 16px;
        border-radius: 50px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    .avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: var(--accent);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
    }
    
    .section-title {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: 40px 0 16px 0;
    }
    
    .empty-state {
        text-align: center;
        padding: 40px 20px;
        background: #f8f9fa;
        border-radius: 12px;
        margin: 20px 0;
    }
    
    .empty-state-icon {
        font-size: 48px;
        margin-bottom: 16px;
        color: #adb5bd;
    }
</style>
""", unsafe_allow_html=True)

# ─── Session State Restoration ──────────────────


# ─── Authentication Check ──────────────────────
if not all(key in st.session_state for key in ["fb_id", "fb_name", "fb_token"]):
    st.warning("Please login to access your projects")
    if st.button("Go to Login", key="go_to_login"):
        st.switch_page("pages/Login Page.py")
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
            {fb_name[0].upper() if fb_name else "U"}
        </div>
        <div>
            <div style="font-weight: 600;">{fb_name}</div>
            <div style="font-size: 0.8em; color: #6c757d;">Account active</div>
        </div>
        <button onclick="window.location.href='/Projects.py'" style="
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
@st.cache_resource
def get_blob_service_client():
    AZ_CONN = st.secrets.get("AZURE_CONNECTION_STRING") or os.getenv("AZURE_CONNECTION_STRING")
    if AZ_CONN:
        return BlobServiceClient.from_connection_string(AZ_CONN)
    return None

blob_service_client = get_blob_service_client()
backups = []

if blob_service_client:
    try:
        container_client = blob_service_client.get_container_client("backup")
        blobs = list(container_client.list_blobs())
        
        # Process backups with progress indicator
        with st.spinner("Loading your backups..."):
            folders = set(b.name.split("/")[0] for b in blobs if b.name and "summary.json" in b.name)
            for folder in sorted(folders, reverse=True):
                if not folder:
                    continue
                try:
                    blob_path = f"{folder}/summary.json"
                    summary_blob = container_client.download_blob(blob_path)
                    summary = json.loads(summary_blob.readall().decode("utf-8"))

                    # If fb_id is set, filter by it
                    if fb_id and summary.get("user_id") != fb_id:
                        continue

                    created_date = datetime.fromisoformat(summary.get("timestamp", "2000-01-01"))

                    backups.append({
                        "id": folder,
                        "name": summary.get("user") or folder.replace("_", " "),
                        "date": created_date.strftime("%b %d, %Y"),
                        "posts": summary.get("posts", 0),
                        "status": "Completed",
                        "raw_date": created_date
                    })

                except Exception as e:
                    st.error(f"Error loading backup {folder}: {str(e)}")

        # Sort by date
        backups.sort(key=lambda x: x["raw_date"], reverse=True)
        
    except Exception as e:
        st.error(f"Azure connection error: {str(e)}")

# ─── Projects Management ───────────────────────
projects_file = f"projects_{fb_id}.json"
projects = []

if os.path.exists(projects_file):
    try:
        with open(projects_file, "r") as f:
            projects = json.load(f)
    except Exception as e:
        st.error(f"Error loading projects: {str(e)}")

# Handle new backup if redirected
if st.session_state.pop("new_backup_done", False):
    latest = st.session_state.pop("latest_backup", None)
    if latest and latest.get("user_id") == st.session_state["fb_id"]:
        normalized = {
            "id": latest.get("id"),
            "name": latest.get("name") or latest.get("Name", "Unnamed Backup"),
            "date": latest.get("date") or latest.get("Created On", "Unknown"),
            "posts": latest.get("posts") or latest.get("# Posts", 0),
            "status": latest.get("status", "Completed"),
            "raw_date": datetime.now()
        }
        backups.insert(0, normalized)


# Handle new project if redirected
if st.session_state.pop("new_project_added", False):
    latest_project = st.session_state.pop("latest_project", None)
    if latest_project:
        projects.append(latest_project)
        try:
            with open(projects_file, "w") as f:
                json.dump(projects, f)
        except Exception as e:
            st.error(f"Error saving project: {str(e)}")

# ─── Main Content ──────────────────────────────
tab1, tab2, tab3 = st.tabs(["📦 My Backups", "📚 My Projects", "📦 Orders"])

with tab1:
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
                subcols = st.columns(3)

                # Download JSON button
                with subcols[0]:
                    posts_blob_path = f"{backup['id']}/posts+cap.json"
                    try:
                        blob_client = container_client.get_blob_client(posts_blob_path)
                        blob_client.get_blob_properties()
                        blob_data = blob_client.download_blob().readall()
                        st.download_button(
                            label="📥 Download JSON",
                            data=blob_data,
                            file_name=f"{backup['id']}.json",
                            mime="application/json"
                        )
                    except Exception:
                        st.caption("No posts file")

                # Edit Duration button as markdown styled link
                with subcols[1]:
                    st.markdown(
                        f"""
                        <a href="?edit_duration={backup['id']}" class="stButton primary" 
                        style="text-decoration: none; color: white; padding: 8px 16px; 
                        border-radius: 6px; background: var(--primary); display: inline-block;">
                        ✂️ Edit Duration</a>
                        """,
                        unsafe_allow_html=True
                    )

                # Generate Memories streamlit button
                with subcols[2]:
                    if st.button("📘 Generate Memories", key=f"mem_{backup['id']}"):
                        st.session_state["selected_backup"] = backup["id"]
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
        for project in projects:
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
                if st.button("Continue", key=f"continue_{project.get('id')}"):
                    st.session_state.selected_project = project.get('id')
                    st.switch_page("pages/FbProjectEditor.py")
            
            st.divider()
        st.markdown("</div>", unsafe_allow_html=True)
    else:
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