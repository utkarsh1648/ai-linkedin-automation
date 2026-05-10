# 🤖 Multi-Platform AI Social Bot

An automated news discovery and broadcasting engine that transforms the latest AI developments into high-engagement content for LinkedIn, Twitter, and Instagram.

---

## ✨ Key Features

*   **🔍 AI News Discovery**: Aggregates the latest AI news from NewsAPI and curated RSS feeds.
*   **🧠 Dynamic Content Engine**: Uses **Google Gemini AI** to generate platform-optimized posts for any number of channels (LinkedIn, X/Twitter, Instagram, etc.).
*   **🎨 Branded Visual Engine**: Automatically generates **1080x1080 News Cards** using Pillow, featuring headlines, branding, and dynamic layouts.
*   **✨ Smart Image Handling**: Upload any image ratio! The bot automatically "squares" images for Instagram while preserving originals for LinkedIn and X.
*   **🕹️ Slack Command Center**: A unified approval workflow in Slack:
    *   **Dynamic Channel Selection**: Choose where to post based on your active Buffer configuration.
    *   **Live Previews**: See all text and image versions before they go live.
    *   **Interactive Editing**: Edit the content or upload custom images directly from Slack.
*   **☁️ Cloud-Ready Architecture**: Pluggable storage drivers (JSON/PostgreSQL) designed for seamless deployment on **Render**, Heroku, or AWS.

---

## 🛠️ Tech Stack

*   **Language**: Python 3.10+
*   **AI Engine**: Google Gemini Pro
*   **Broadcaster**: Buffer (GraphQL API)
*   **Visuals**: Pillow (PIL)
*   **Interface**: Slack Block Kit & FastAPI
*   **Database**: PostgreSQL / JSON

---

## 🚦 Workflow

1.  **Fetch**: Pipeline discovers the top AI news stories of the day.
2.  **Generate**: Gemini creates 3 style-specific post drafts and an image concept.
3.  **Render**: Visual Engine builds a branded news card image.
4.  **Review**: Slack sends a unified preview with approval checkboxes.
5.  **Edit/Approve**: User refines content via Slack modal and hits "Approve."
6.  **Broadcast**: Bot pushes the content to all selected Buffer channels simultaneously.

---

## 🛠️ Getting Started

For detailed instructions on API keys, Slack configuration, and deployment, please refer to the:

👉 **[SETUP_GUIDE.md](./SETUP_GUIDE.md)**

---

## 🚀 Render Deployment (Free Tier)

This bot is optimized to run on Render's **Free Tier** without requiring a paid Persistent Disk. To ensure stability:

1.  **Storage**: Use the **Postgres** driver (`STORAGE_DRIVER=postgres`) with a Render Free PostgreSQL instance.
2.  **Images**: Set `IMGBB_API_KEY` to ensure all images are hosted in the cloud.
3.  **Newsletter**: Use the **Resend** driver for reliable email delivery.

---

## 📜 Automation
The pipeline can be triggered manually or scheduled using **GitHub Actions** or a standard CRON job to ensure a consistent social media presence.