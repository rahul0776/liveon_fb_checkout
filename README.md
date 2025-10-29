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
- [Project Structure](#project-structure)
- [Technologies Used](#technologies-used)
- [Security](#security)
- [Acknowledgments](#acknowledgments)

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

- Python 3.9 or higher
- Azure account with:
  - Azure Functions (for API)
  - Azure Blob Storage container named `backup`
- Facebook Developer account with an app configured for OAuth
- Stripe account (test or live keys)

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


## 🙏 Acknowledgments

- Facebook Graph API documentation
- Azure SDK for Python
- Streamlit community
- Stripe API documentation

---

**Made with ❤️ by MinedCo | LiveOn**

*Preserving your digital memories, one backup at a time.*

