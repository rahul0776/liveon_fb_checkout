# LiveOn Facebook Backup

A secure, user-friendly web application for backing up Facebook posts, photos, and memories to Azure Blob Storage with integrated payment processing via Stripe.

![LiveOn Fb](media/banner.png)

## 🌟 Features

- **Facebook OAuth Integration**: Secure authentication with Facebook's OAuth 2.0
- **Automated Backup**: Fetch and archive posts, photos, and profile data from Facebook
- **Azure Blob Storage**: Reliable cloud storage for all backup data
- **Stripe Payment Integration**: Secure payment processing for premium downloads
- **Interactive Memory Viewer**: Browse and search through your backed-up posts and photos
- **Bulk Download**: Download entire backups as ZIP files
- **Beautiful UI**: Navy and gold-themed interface with responsive design

## 📋 Table of Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running Locally](#running-locally)
- [Deployment](#deployment)
- [Project Structure](#project-structure)
- [Environment Variables](#environment-variables)
- [Usage](#usage)
- [Technologies Used](#technologies-used)
- [Contributing](#contributing)
- [License](#license)

## 🏗️ Architecture

**Stack:**
- **Frontend**: Streamlit (Python web framework)
- **Backend API**: Azure Functions (serverless)
- **Storage**: Azure Blob Storage
- **Payments**: Stripe
- **Authentication**: Facebook OAuth 2.0

**Flow:**
1. User authenticates with Facebook OAuth
2. App fetches posts and media from Facebook Graph API via Azure Functions
3. Data is stored in Azure Blob Storage with organized folder structure
4. Users can view memories, create new backups, and purchase downloads
5. Stripe handles payment processing for premium downloads

## ✅ Prerequisites

Before you begin, ensure you have:

- Python 3.9 or higher
- Azure account with:
  - Azure Functions (for API)
  - Azure Blob Storage container named `backup`
- Facebook Developer account with an app configured for OAuth
- Stripe account (test or live keys)
- Git

## 📦 Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/liveon_checkout.git
cd liveon_checkout
```

### 2. Create virtual environment

```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## ⚙️ Configuration

### 1. Set up Facebook App

1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Create a new app or use an existing one
3. Add "Facebook Login" product
4. Configure OAuth redirect URIs:
   - Development: `http://localhost:8501`
   - Production: `https://yourdomain.com`
5. Note your App ID and App Secret

### 2. Set up Azure

**Azure Blob Storage:**
1. Create a storage account
2. Create a container named `backup`
3. Copy the connection string

**Azure Functions:**
1. Deploy your backend API to Azure Functions
2. Note the function app URL

### 3. Set up Stripe

1. Go to [Stripe Dashboard](https://dashboard.stripe.com/)
2. Get your API keys (test or live)
3. Configure webhook endpoints if needed

### 4. Create Secrets File

Create `.streamlit/secrets.toml` (for local development):

```toml
# Facebook OAuth
FB_CLIENT_ID = "your_facebook_app_id"
FB_CLIENT_SECRET = "your_facebook_app_secret"
FB_REDIRECT_URI = "http://localhost:8501"

# Security
STATE_SECRET = "your_secure_random_string_min_32_chars"

# Azure
AZURE_CONNECTION_STRING = "your_azure_storage_connection_string"

# Stripe
STRIPE_SECRET_KEY = "sk_test_..."
STRIPE_PUBLIC_KEY = "pk_test_..."

# Optional
DEBUG = "true"
SHOW_MEMORIES_BUTTON = "true"
```

**For production (Streamlit Cloud):**
Add these in Settings → Secrets

**Security Note**: NEVER commit secrets.toml to Git. It's already in .gitignore.

## 🚀 Running Locally

```bash
streamlit run LiveOn.py
```

The app will open in your browser at `http://localhost:8501`

## 🌐 Deployment

### Streamlit Cloud (Recommended)

1. Push your code to GitHub
2. Go to [Streamlit Cloud](https://streamlit.io/cloud)
3. Connect your GitHub repository
4. Configure secrets in the dashboard
5. Deploy!

### Other Platforms

See our [deployment guide](full-website-deployment.plan.md) for:
- Azure App Service
- Vercel (with Next.js migration)
- Railway
- Render

## 📁 Project Structure

```
liveon_checkout/
├── LiveOn.py                 # Main entry point (home/login page)
├── pages/
│   ├── Projects.py           # Backup projects dashboard
│   ├── FbMemories.py         # Memory viewer
│   ├── FB_Backup.py          # Backup creation page
│   ├── success.py            # Payment success page
│   └── utils/
│       └── theme.py          # Shared theme utilities
├── media/                    # Images and branding assets
│   ├── logo.png
│   ├── banner.png
│   └── ...
├── requirements.txt          # Python dependencies
├── constraints.txt           # Version constraints
└── .streamlit/
    └── secrets.toml          # Local secrets (not in Git)
```

## 🔐 Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `FB_CLIENT_ID` | Facebook App ID | `123456789012345` |
| `FB_CLIENT_SECRET` | Facebook App Secret | `abcdef123456...` |
| `FB_REDIRECT_URI` | OAuth redirect URL | `https://yourapp.com` |
| `STATE_SECRET` | HMAC signing key (min 32 chars) | Random secure string |
| `AZURE_CONNECTION_STRING` | Azure Storage connection | `DefaultEndpointsProtocol=https;...` |
| `STRIPE_SECRET_KEY` | Stripe secret key | `sk_live_...` or `sk_test_...` |
| `STRIPE_PUBLIC_KEY` | Stripe publishable key | `pk_live_...` or `pk_test_...` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug messages | `false` |
| `SHOW_MEMORIES_BUTTON` | Show memories navigation | `true` |

## 💡 Usage

### For End Users

1. **Sign In**: Click "Link Facebook Account" and authorize the app
2. **Create Backup**: Navigate to Projects and click "Create New Backup"
3. **View Memories**: Browse your posts, photos, and timeline
4. **Download**: Purchase and download your backup as a ZIP file

### For Developers

**Adding New Pages:**
```python
# pages/NewPage.py
import streamlit as st

st.set_page_config(page_title="New Page", page_icon="🆕")
st.title("New Feature")
```

**Accessing Session Data:**
```python
if "fb_token" in st.session_state:
    token = st.session_state["fb_token"]
    # Use token for API calls
```

**Calling Azure Functions:**
```python
import requests

response = requests.post(
    f"{azure_function_url}/create-backup",
    json={"token": fb_token}
)
```

## 🛠️ Technologies Used

- **[Streamlit](https://streamlit.io/)** - Web framework
- **[Azure Blob Storage](https://azure.microsoft.com/en-us/services/storage/blobs/)** - Cloud storage
- **[Azure Functions](https://azure.microsoft.com/en-us/services/functions/)** - Serverless backend
- **[Stripe](https://stripe.com/)** - Payment processing
- **[Facebook Graph API](https://developers.facebook.com/docs/graph-api/)** - Data fetching
- **[Pillow](https://python-pillow.org/)** - Image processing
- **[Pandas](https://pandas.pydata.org/)** - Data manipulation

## 🔒 Security

- OAuth 2.0 for authentication
- HMAC-signed state tokens with expiration
- httpOnly cookies recommended for production
- Secrets stored securely (never committed to Git)
- Azure Blob Storage with private access
- Stripe PCI-compliant payment processing

## 🧪 Testing

```bash
# Run with debug mode
# Set DEBUG = "true" in secrets.toml

streamlit run LiveOn.py
```

## 📝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 🐛 Known Issues

- Large backups (>1000 posts) may take several minutes
- Facebook API rate limits apply
- Vercel cannot host Streamlit apps directly (see Next.js migration plan)

## 📊 Roadmap

- [ ] Incremental backups (only fetch new posts)
- [ ] Schedule automatic backups
- [ ] Export to multiple formats (PDF, CSV)
- [ ] Instagram integration
- [ ] Multi-user support with database
- [ ] Mobile app

## 💰 Cost Estimation

- **Streamlit Cloud**: Free tier available
- **Azure Functions**: ~$5-20/month (consumption plan)
- **Azure Blob Storage**: ~$5-10/month
- **Stripe**: 2.9% + 30¢ per transaction
- **Total**: ~$10-30/month + transaction fees

## 📞 Support

For issues, questions, or feature requests:
- Open an issue on GitHub
- Contact: [your-email@example.com]

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Facebook Graph API documentation
- Azure SDK for Python
- Streamlit community
- Stripe API documentation

---

**Made with ❤️ by MinedCo | LiveOn**

*Preserving your digital memories, one backup at a time.*

