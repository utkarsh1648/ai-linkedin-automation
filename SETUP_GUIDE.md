# 🚀 Multi-Platform AI Social Bot - Setup Guide

Welcome! This guide will help you configure and deploy your unified AI broadcasting tool. This bot handles news discovery, multi-platform content generation (LinkedIn, Twitter, Instagram), branded visual cards, and Slack-based approval workflows.

---

## 🛠️ API & Service Setup

### 1. Google Gemini AI (The Brain)
*   **Purpose**: Generates high-quality posts in three distinct styles.
*   **Action**: Get your API key from [Google AI Studio](https://aistudio.google.com/).
*   **Env Variable**: `GEMINI_API_KEY`

### 2. Buffer (The Broadcaster)
*   **Purpose**: Handles posting to LinkedIn, Twitter, and Instagram.
*   **Action**: 
    1. Create a Buffer account and connect your channels.
    2. Go to the [Buffer Developers](https://buffer.com/developers) portal.
    3. Create an "App" and get your **Access Token**.
    4. Note down your **Channel IDs** (visible in your Buffer dashboard URL).
*   **Env Variables**: `BUFFER_TOKEN`, `BUFFER_CHANNELS` 
*   **Channel Format**: `id:style:Name:Icon` (Multiple channels separated by `;`)
    *   **Styles**: `linkedin`, `twitter`, `instagram` (or any custom style for AI generation).
    *   **Example**: `69b4...:linkedin:LinkedIn:💼;69ff...:instagram:Instagram:📸`

### 3. Slack App (The Control Center)
*   **Purpose**: Approval workflow, multi-platform previews, and editing.
*   **Action**:
    1. Create an app at [api.slack.com](https://api.slack.com/apps).
    2. **Interactivity & Shortcuts**: Enable this and set the Request URL to `https://your-ngrok-url.ngrok-free.dev/slack/actions`.
    3. **OAuth & Permissions**: Add `chat:write`, `files:write`, and `remote_files:write` scopes.
    4. Install the app to your workspace.
*   **Env Variables**: `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`

### 4. ImgBB (Image Hosting)
*   **Purpose**: Hosts AI-generated news cards for Slack previews.
*   **Action**: Sign up at [ImgBB](https://imgbb.com/) and get an API key from the [API Documentation](https://api.imgbb.com/).
*   **Env Variable**: `IMGBB_API_KEY`

### 5. Resend (Email Newsletter)
*   **Purpose**: Sends the "AI News Digest" to your subscribers.
*   **Action**: 
    1. Create an account at [Resend](https://resend.com).
    2. Get your **API Key**.
    3. Verify your domain (optional but recommended).
*   **Env Variables**: `EMAIL_DRIVER` ("resend" or "smtp"), `RESEND_API_KEY`, `EMAIL_SENDER` (your verified email).

---

## ⚙️ Configuration (.env)

Create a `.env` file in the root directory with the following structure:

```env
# AI & Core
GEMINI_API_KEY="your_key"
NEWS_API_KEY="your_key"

# Slack
SLACK_BOT_TOKEN="xoxb-your-token"
SLACK_CHANNEL_ID="C0XXXXXXX"

# Buffer (Multi-Channel Configuration)
BUFFER_TOKEN="your_buffer_token"
# Format: CHANNEL_ID:STYLE:NAME:ICON
BUFFER_CHANNELS="id1:linkedin:LinkedIn:💼;id2:twitter:X:🐦;id3:instagram:Instagram:📸"

# Visual Engine
IMGBB_API_KEY="your_imgbb_key"
BASE_PUBLIC_URL="https://your-ngrok-url.ngrok-free.dev"

# Storage Driver (Local vs Render)
# Use 'json' for local dev, 'postgres' for Render
STORAGE_DRIVER="json"
DATABASE_URL="postgresql://..." 

# Email (Resend)
EMAIL_DRIVER="resend"
RESEND_API_KEY="re_..."
EMAIL_SENDER="you@yourdomain.com"
EMAIL_SENDER_NAME="AI News Digest"
```

---

## 🚀 Deployment Options

### Option A: Local Development
1.  Install dependencies: `pip install -r requirements.txt`
2.  Start ngrok: `ngrok http 8000`
3.  Start the API server: `uvicorn main:app --reload --port 8000`
4.  Run the pipeline: `python main.py`

### Option B: Hosting on Render (Production)
1.  **Connect Repo**: Point Render to your GitHub repository.
2.  **Add Database**: Provision a "Render PostgreSQL" instance.
3.  **Env Variables**: Copy your `.env` values to Render's environment dashboard. 
    *   Set `STORAGE_DRIVER=postgres`.
    *   Render will automatically provide the `DATABASE_URL`.
4.  **Persistent Disk**: For better file handling, add a "Disk" in Render and mount it to `/media`.

---

## 🎯 Usage Workflow
1.  Run `python main.py`.
2.  Wait for the **Slack Notification**.
3.  Check the **Checkboxes** for the platforms you want to post to.
4.  (Optional) Click **Edit** to refine the LinkedIn version or upload a custom image.
5.  Click **Approve** to broadcast live! 🚀
