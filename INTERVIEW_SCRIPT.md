# LiveOn - Interview Script

## Project Overview (30 seconds)

"LiveOn is a secure web application I built that helps users back up their Facebook posts, photos, and memories to cloud storage. Think of it as a digital preservation service - users can safely archive their social media data and later download it as organized ZIP files. It includes integrated payment processing for premium downloads."

---

## Technical Architecture (45-60 seconds)

**"I built this using a full-stack architecture:"**

**Frontend:**
- Next.js 14 with TypeScript and Tailwind CSS for the marketing and login experience
- Modern React components with responsive design
- Navy and gold branding consistent across the app

**Backend:**
- Python with Streamlit as the web framework
- Facebook OAuth 2.0 for secure authentication
- Azure Functions (serverless) to fetch data from Facebook Graph API
- Azure Blob Storage for cloud storage of all backup data
- Stripe integration for payment processing

**"The flow works like this:"**
1. User authenticates with Facebook OAuth
2. The app fetches their posts and media via Azure Functions calling the Facebook Graph API
3. Data is organized and stored in Azure Blob Storage with a clear folder structure
4. Users can browse their memories through an interactive viewer
5. For premium downloads, Stripe handles secure payment processing
6. After payment, users download their entire backup as a ZIP file

---

## Key Technical Challenges & Solutions (60 seconds)

**"I tackled several interesting challenges:"**

**Security:**
- Implemented HMAC-signed state tokens with expiration to prevent CSRF attacks during OAuth
- Used time-limited tokens to ensure secure authentication flows
- Stored all secrets securely, never committing credentials to version control

**Data Organization:**
- Designed a hierarchical storage structure in Azure Blob Storage (user ID → backup timestamp → organized files)
- Created an entitlements system to track which users have paid access to which backups
- Built a session restoration mechanism using cache hashing so users don't lose progress

**Payment Integration:**
- Integrated Stripe Checkout Sessions with custom metadata
- Ensured payment verification and entitlement tracking work seamlessly
- Handled edge cases like payment verification failures and session restoration

**API Integration:**
- Worked with Facebook Graph API to fetch posts, photos, and user data
- Implemented rate limiting and error handling for API calls
- Used Azure Functions for serverless API endpoints to keep costs low

---

## What I Learned / Why This Matters (30 seconds)

**"This project taught me a lot about:"**
- Building secure authentication flows with OAuth 2.0
- Integrating multiple third-party services (Facebook, Azure, Stripe) into one cohesive application
- Serverless architecture and cloud storage best practices
- Handling user data securely and responsibly
- Creating a smooth user experience across authentication, data fetching, payment, and download flows

**"It's relevant because:"**
- It demonstrates full-stack development skills
- Shows ability to work with cloud platforms (Azure)
- Proves I can integrate payment processing securely
- Highlights security-conscious development practices

---

## Quick Demo Points (if showing the app)

- "Here's the landing page - clean, professional UI"
- "Users authenticate with Facebook - notice the secure OAuth flow"
- "After authentication, they see their backup projects dashboard"
- "The memory viewer lets them browse through archived posts and photos"
- "For downloads, we have Stripe checkout integration"
- "Finally, they can download everything as an organized ZIP file"

---

## Technologies Mentioned (Quick Reference)

- **Frontend**: Next.js 14, React, TypeScript, Tailwind CSS
- **Backend**: Python, Streamlit
- **Cloud**: Azure Functions, Azure Blob Storage
- **APIs**: Facebook Graph API
- **Payments**: Stripe
- **Security**: OAuth 2.0, HMAC signatures
- **Other**: Pandas, Pillow (image processing)

---

## Closing Statement (15 seconds)

**"This project demonstrates my ability to build end-to-end applications that integrate multiple services, handle user data securely, and provide a smooth user experience. It's a complete solution from authentication through payment processing to data delivery."**



