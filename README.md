# AI LinkedIn Automation

This project automatically generates and posts LinkedIn content about the latest Artificial Intelligence developments.

## Features

• Fetches latest AI news  
• Generates LinkedIn posts using Google Gemini  
• Publishes posts using Buffer API  
• Runs automatically using GitHub Actions  

## Tech Stack

Python  
Google Gemini API  
Buffer GraphQL API  
GitHub Actions  

## Workflow

Latest AI News  
↓  
Gemini generates LinkedIn content  
↓  
Python sends post to Buffer  
↓  
Buffer publishes on LinkedIn  
↓  
GitHub Actions runs weekly

## Automation

Posts are automatically generated and published every week.

## Configuration

All configuration is done via a `.env` file in the project root.  
Copy the example below, fill in your values, and the pipeline will pick them up automatically.

```env
# ── Core APIs ─────────────────────────────────────────────────────────────
NEWS_API_KEY=          # NewsAPI.org key — fetches latest AI articles
GEMINI_API_KEY=        # Google Gemini API key — generates LinkedIn posts
BUFFER_TOKEN=          # Buffer API token — schedules/publishes LinkedIn posts
CHANNEL_ID=            # Buffer channel ID for your LinkedIn profile

# ── Slack Integration ─────────────────────────────────────────────────────
SLACK_BOT_TOKEN=       # xoxb-... token for your Slack bot
SLACK_CHANNEL_ID=      # Channel ID where pipeline notifications are sent

# ── X (Twitter) Trends ────────────────────────────────────────────────────
X_API_KEY=             # Bearer token for Twitter/X API v2
ENABLE_X_API=true      # Set to false to disable trend fetching from X

# ── Image Storage ─────────────────────────────────────────────────────────
IMGBB_API_KEY=         # ImgBB API key — used to host generated images publicly
BASE_PUBLIC_URL=       # Public URL of your local/remote server (e.g. https://yourserver.com)

# ── Email Newsletter ──────────────────────────────────────────────────────
EMAIL_DRIVER=smtp           # "smtp" or "resend"
EMAIL_SENDER=               # From address shown to subscribers
EMAIL_SENDER_NAME=AI News   # Display name for the sender

# SMTP driver (e.g. Gmail)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=               # Gmail address used to send emails
SMTP_PASSWORD=           # Gmail App Password (not your login password)

# Resend driver (https://resend.com) — alternative to SMTP
RESEND_API_KEY=

# ── Subscriber Store ──────────────────────────────────────────────────────
SUBSCRIBER_DRIVER=json            # "json" | "sqlite" | "postgres"
SUBSCRIBERS_JSON_PATH=subscribers.json   # Used when SUBSCRIBER_DRIVER=json
SUBSCRIBERS_DB_PATH=subscribers.db       # Used when SUBSCRIBER_DRIVER=sqlite
DATABASE_URL=                            # Used when SUBSCRIBER_DRIVER=postgres
                                         # e.g. postgresql://user:pass@host:5432/dbname
```

---

## Backend Server

The project includes a lightweight FastAPI server (`api/`) that exposes webhook endpoints for Slack interactions (e.g. approving/rejecting posts, managing subscribers).

### Starting the server locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the API server
uvicorn api.main:app --reload --port 8000
```

Set `BASE_PUBLIC_URL` in your `.env` to make it reachable by Slack:

```env
BASE_PUBLIC_URL=https://your-ngrok-or-server-url.com
```

> **Tip:** For local development, use [ngrok](https://ngrok.com) to expose your local server:  
> `ngrok http 8000` — then paste the generated URL into `BASE_PUBLIC_URL`.

### Available endpoints

| Endpoint | Description |
|---|---|
| `POST /slack/actions` | Handles Slack interactive button callbacks (approve/reject posts) |
| `GET /subscribers` | Lists all newsletter subscribers |
| `POST /subscribers` | Adds a new subscriber |
| `DELETE /subscribers/{email}` | Removes a subscriber |

---

## Image Storage

Generated images (e.g. AI-illustrated post visuals) are uploaded to **ImgBB** to obtain a public URL that Buffer can attach to the LinkedIn post.

### Setup

1. Sign up at [imgbb.com](https://imgbb.com) and generate a free API key.
2. Add it to your `.env`:

```env
IMGBB_API_KEY=your_imgbb_api_key_here
```

### How it works

```
Image generated locally (media/)
    ↓
Uploaded to ImgBB via API
    ↓
Public URL returned
    ↓
Attached to LinkedIn post via Buffer
```

Images are also saved locally under the `media/` directory as a backup.

---

## Customizing Prompts

All AI prompts are stored as plain-text files inside the `prompts/` directory.  
You can edit them directly — **no Python knowledge required**.

```
prompts/
  select_top_trending.txt       # Selects the most relevant articles from the news pool
  generate_social_post.txt      # Generates the LinkedIn post content
  generate_newsletter_intro.txt # Writes the intro paragraph for the email newsletter
```

### How to edit a prompt

1. Open the relevant `.txt` file in any text editor.
2. Modify the wording, tone, structure, or rules as needed.
3. Save the file and re-run the pipeline — changes take effect immediately.

### Dynamic placeholders

The following placeholders are replaced automatically at runtime — **do not remove them**:

| Placeholder | Description |
|---|---|
| `{article_count}` | Total number of articles being analyzed |
| `{count}` | Number of top articles to select |
| `{articles_list}` | Numbered list of article headlines/summaries |
| `{articles_text}` | Full text of the selected articles |

> **Tip:** You can change the writing style, tone, length constraints, or output format of any prompt freely — just keep the `{placeholders}` intact.

## Future Improvements

• Summarize multiple AI news articles  
• AI-generated carousel posts  
• Engagement analytics