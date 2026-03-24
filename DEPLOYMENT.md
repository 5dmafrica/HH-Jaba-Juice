# HH Jaba Staff Portal — Deployment Guide

> A step-by-step guide for deploying the HH Jaba Staff Portal outside the Emergent platform.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Database Setup (MongoDB Atlas)](#1-database-setup-mongodb-atlas)
4. [Authentication Setup (Google OAuth)](#2-authentication-setup-google-oauth)
5. [Backend Deployment](#3-backend-deployment)
6. [Frontend Deployment (Cloudflare Pages)](#4-frontend-deployment-cloudflare-pages)
7. [Environment Variables Reference](#environment-variables-reference)
8. [Post-Deployment Checklist](#post-deployment-checklist)
9. [MongoDB Collections Reference](#mongodb-collections-reference)
10. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
┌─────────────────────┐      ┌──────────────────────┐      ┌──────────────────┐
│   Cloudflare Pages  │      │  Backend Server       │      │  MongoDB Atlas   │
│   (React Frontend)  │─────>│  (FastAPI + Python)   │─────>│  (Cloud DB)      │
│   Port: 443 (HTTPS) │      │  Railway / Render /   │      │  Free M0 Tier    │
│                     │      │  Fly.io / VPS         │      │                  │
└─────────────────────┘      └──────────────────────┘      └──────────────────┘
```

| Component | Technology | Recommended Host |
|-----------|-----------|-----------------|
| Frontend | React 19 + Tailwind CSS + shadcn/ui | Cloudflare Pages |
| Backend | FastAPI (Python 3.11+) | Railway, Render, or Fly.io |
| Database | MongoDB | MongoDB Atlas (free tier) |
| Auth | Google OAuth 2.0 | Google Cloud Console |
| Email | Resend API | resend.com |

---

## Prerequisites

- Node.js 18+ and Yarn 1.22+
- Python 3.11+
- Git
- A Cloudflare account (free)
- A MongoDB Atlas account (free)
- A Google Cloud Console account (for OAuth)
- A Resend account for email (optional, free tier available)

---

## 1. Database Setup (MongoDB Atlas)

1. Go to [MongoDB Atlas](https://www.mongodb.com/atlas) and create a free account
2. Create a new **Shared Cluster** (M0 Free Tier)
3. Choose your preferred cloud provider and region
4. Under **Database Access**, create a database user:
   - Username: `hhjaba_admin` (or your choice)
   - Password: Generate a strong password and **save it**
5. Under **Network Access**, add your backend server's IP address
   - For initial testing, you can allow `0.0.0.0/0` (all IPs), then restrict later
6. Click **Connect** > **Drivers** > Copy the connection string:
   ```
   mongodb+srv://hhjaba_admin:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
7. Replace `<password>` with your actual password

The application will auto-create these collections on first run:
- `users`, `products`, `orders`, `credit_invoices`, `manual_invoices`
- `payment_submissions`, `dispute_messages`, `feedback`
- `notifications`, `user_sessions`, `stock_entries`

Default products (5 drink flavors) are seeded automatically on startup.

---

## 2. Authentication Setup (Google OAuth)

> **IMPORTANT:** The current codebase uses Emergent-managed Google Auth (`auth.emergentagent.com`). For production deployment, you **must** replace this with your own Google OAuth setup.

### What Needs to Change

Two files reference Emergent Auth and need modification:

#### A. Backend: `backend/server.py`

The session exchange endpoint (around line 420) calls Emergent's auth API:

```python
# CURRENT (Emergent Auth) — MUST REPLACE
auth_response = await client.get(
    "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
    headers={"X-Session-ID": session_id}
)
```

**Replace with** your own Google OAuth token verification. Here's a recommended approach:

```python
# PRODUCTION (Google OAuth directly)
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

@api_router.post("/auth/google")
async def google_auth(request: Request, response: Response):
    body = await request.json()
    token = body.get("credential")  # Google ID token from frontend
    
    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            YOUR_GOOGLE_CLIENT_ID
        )
        email = idinfo["email"]
        name = idinfo.get("name", "")
        picture = idinfo.get("picture", "")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google token")
    
    # ... rest of user creation/session logic stays the same
```

#### B. Frontend: `frontend/src/context/AuthContext.js`

The login function (line 51) redirects to Emergent Auth:

```javascript
// CURRENT (Emergent Auth) — MUST REPLACE
const login = () => {
    const redirectUrl = window.location.origin + '/dashboard';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
};
```

**Replace with** Google Sign-In. Install `@react-oauth/google` and use:

```javascript
// PRODUCTION (Google OAuth)
import { GoogleOAuthProvider, GoogleLogin } from '@react-oauth/google';

// In your login component:
<GoogleLogin
    onSuccess={(credentialResponse) => {
        // Send credentialResponse.credential to your backend /api/auth/google
    }}
    onError={() => console.log('Login Failed')}
/>
```

#### C. Frontend: `frontend/src/pages/AuthCallback.js`

This file handles the Emergent Auth callback. Replace it with your Google OAuth callback logic or remove it entirely if using the Google Sign-In button approach (which doesn't need a callback page).

### Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Navigate to **APIs & Services** > **Credentials**
4. Click **Create Credentials** > **OAuth 2.0 Client IDs**
5. Set application type to **Web application**
6. Add authorized JavaScript origins:
   - `https://your-app.pages.dev` (your Cloudflare Pages URL)
   - `http://localhost:3000` (for local development)
7. Add authorized redirect URIs:
   - `https://your-app.pages.dev/dashboard`
   - `http://localhost:3000/dashboard`
8. Copy the **Client ID** and **Client Secret**

### Email Domain Restriction

The app restricts login to `@5dm.africa` emails. This is enforced in `backend/server.py` (line 441):

```python
if not email.endswith("@5dm.africa"):
    raise HTTPException(status_code=403, detail="Only @5dm.africa email addresses are allowed")
```

Modify this if your email domain changes.

---

## 3. Backend Deployment

### Option A: Railway (Recommended — Easiest)

1. Go to [Railway](https://railway.app/) and sign up
2. Click **New Project** > **Deploy from GitHub Repo**
3. Select your repository
4. Set the **Root Directory** to `backend`
5. Railway auto-detects Python. Set the **Start Command**:
   ```
   uvicorn server:app --host 0.0.0.0 --port $PORT
   ```
6. Add environment variables (see [Environment Variables](#environment-variables-reference))
7. Deploy — Railway will provide a URL like `https://your-app.up.railway.app`

### Option B: Render

1. Go to [Render](https://render.com/) and create a **Web Service**
2. Connect your GitHub repo
3. Set:
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn server:app --host 0.0.0.0 --port $PORT`
4. Add environment variables
5. Deploy

### Option C: Fly.io

1. Install the Fly CLI: `curl -L https://fly.io/install.sh | sh`
2. Create a `backend/fly.toml`:
   ```toml
   app = "hhjaba-api"

   [build]
     builder = "paketobuildpacks/builder:base"

   [env]
     PORT = "8080"

   [http_service]
     internal_port = 8080
     force_https = true

   [[services.ports]]
     port = 443
     handlers = ["tls", "http"]
   ```
3. Create a `backend/Procfile`:
   ```
   web: uvicorn server:app --host 0.0.0.0 --port 8080
   ```
4. Deploy: `fly launch` then `fly deploy`

### Dependencies Cleanup (Optional)

The `requirements.txt` includes packages from the development environment that aren't needed in production. Here's a minimal list of what the app actually uses:

```
fastapi==0.110.1
uvicorn==0.25.0
motor==3.3.1
pymongo==4.5.0
pydantic==2.12.5
python-dotenv==1.2.1
httpx==0.28.1
resend==2.26.0
python-jose==3.5.0
passlib==1.7.4
bcrypt==4.1.3
python-multipart==0.0.22
email-validator==2.3.0
```

You can create a `backend/requirements-prod.txt` with just these if you want faster deploys.

---

## 4. Frontend Deployment (Cloudflare Pages)

### Step 1: Update the Backend URL

Before deploying, update the frontend to point to your production backend.

Create `frontend/.env.production`:
```
REACT_APP_BACKEND_URL=https://your-backend-url.up.railway.app
```

> Replace with your actual backend URL from Step 3.

### Step 2: Deploy to Cloudflare Pages

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com/) > **Pages**
2. Click **Create a project** > **Connect to Git**
3. Select your GitHub repository
4. Configure the build:
   - **Framework preset:** Create React App
   - **Root directory:** `frontend`
   - **Build command:** `yarn build`
   - **Build output directory:** `frontend/build`
5. Add environment variable:
   - `REACT_APP_BACKEND_URL` = `https://your-backend-url.up.railway.app`
6. Click **Save and Deploy**

Cloudflare will provide a URL like `https://your-app.pages.dev`.

### Step 3: Update CORS on Backend

After getting your Cloudflare Pages URL, update the backend's CORS settings.

In `backend/.env`, set:
```
CORS_ORIGINS=https://your-app.pages.dev
```

The backend currently accepts all origins (`CORS_ORIGINS="*"`). For production, restrict this to your Cloudflare Pages domain.

### Custom Domain (Optional)

In Cloudflare Pages settings, you can add a custom domain (e.g., `jaba.5dm.africa`) under **Custom domains**.

---

## Environment Variables Reference

### Backend (`backend/.env`)

| Variable | Description | Example |
|----------|-------------|---------|
| `MONGO_URL` | MongoDB Atlas connection string | `mongodb+srv://user:pass@cluster0.xxx.mongodb.net/hhjaba?retryWrites=true&w=majority` |
| `DB_NAME` | MongoDB database name | `hhjaba_production` |
| `CORS_ORIGINS` | Allowed frontend origins (comma-separated) | `https://your-app.pages.dev` |
| `RESEND_API_KEY` | Resend API key for emails | `re_xxxxxxxxxx` |
| `SENDER_EMAIL` | From email for notifications | `noreply@5dm.africa` |

### Frontend (`frontend/.env`)

| Variable | Description | Example |
|----------|-------------|---------|
| `REACT_APP_BACKEND_URL` | Backend API base URL | `https://your-backend.up.railway.app` |

---

## Post-Deployment Checklist

- [ ] MongoDB Atlas cluster is running and accessible from backend server IP
- [ ] Backend is deployed and responding at `/api/health`
- [ ] Frontend is deployed on Cloudflare Pages
- [ ] `REACT_APP_BACKEND_URL` points to the correct backend URL
- [ ] `CORS_ORIGINS` on backend includes the Cloudflare Pages URL
- [ ] Google OAuth is configured with the correct production URLs
- [ ] Auth flow replaced from Emergent Auth to Google OAuth (see Section 2)
- [ ] Email domain restriction (`@5dm.africa`) is correct in `server.py`
- [ ] Default products seeded (happens automatically on first startup)
- [ ] Test login with a `@5dm.africa` Google account
- [ ] Test placing an order as a User
- [ ] Test fulfilling an order as Admin (`yongo@5dm.africa`)
- [ ] Test Super Admin features (`mavin@5dm.africa`)

---

## MongoDB Collections Reference

| Collection | Purpose |
|-----------|---------|
| `users` | User accounts with roles, credit balance, phone |
| `products` | 5 drink flavors with stock and pricing |
| `orders` | All orders with status tracking |
| `credit_invoices` | Credit purchase invoices |
| `manual_invoices` | Cash/manual invoices |
| `payment_submissions` | Proof of Payment (POP) submissions |
| `dispute_messages` | Payment dispute chat messages |
| `feedback` | Customer feedback messages |
| `notifications` | In-app notifications |
| `user_sessions` | Active login sessions |
| `stock_entries` | Stock update history |

---

## Troubleshooting

### Backend won't start
- Ensure Python 3.11+ is installed
- Run `pip install -r requirements.txt` 
- Check that `MONGO_URL` is correct and the IP is whitelisted in Atlas

### Frontend shows blank page
- Check browser console for errors
- Verify `REACT_APP_BACKEND_URL` is set correctly (no trailing slash)
- Ensure the backend CORS allows the frontend origin

### Authentication not working
- This is the **most likely issue** — you MUST replace Emergent Auth with your own Google OAuth
- Check that Google OAuth Client ID is correct
- Verify authorized origins and redirect URIs in Google Cloud Console

### Orders/data not appearing
- Check MongoDB Atlas connection — ensure the database name matches `DB_NAME`
- Check backend logs for MongoDB connection errors
- Verify the backend seeded default products (check `products` collection)

### CORS errors
- Update `CORS_ORIGINS` in backend `.env` to include your exact frontend URL
- Ensure no trailing slash in the URL
- Restart the backend after changing `.env`

---

## Role Configuration

These are hardcoded in `backend/server.py` (lines 30-31):

```python
ADMIN_EMAILS = ['mavin@5dm.africa', 'yongo@5dm.africa']
SUPER_ADMIN_EMAIL = 'mavin@5dm.africa'
```

To add/change admins, modify these lists and redeploy the backend.

---

## Support

For questions about the codebase, refer to:
- `memory/PRD.md` — Product requirements and feature list
- `backend/server.py` — All API endpoints (monolithic, ~2300 lines)
- `frontend/src/pages/AdminDashboard.js` — Admin panel UI (~2200 lines)
- `frontend/src/pages/Dashboard.js` — User dashboard
- `frontend/src/context/AuthContext.js` — Authentication state management
