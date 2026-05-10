import os
from dotenv import load_dotenv


class Config:
    def __init__(self):
        load_dotenv(override=True)
        self.NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
        self.SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "").strip()
        self.SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID", "").strip()
        self.BUFFER_TOKEN = os.getenv("BUFFER_TOKEN", "").strip()
        self.CHANNEL_ID = os.getenv("CHANNEL_ID", "").strip()
        self.BASE_PUBLIC_URL = os.getenv("BASE_PUBLIC_URL", "http://localhost:8000").strip()
        self.IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", "").strip()
        self.MEDIA_DIR = "media"

        # X (Twitter) Trends integration
        self.X_API_KEY = os.getenv("X_API_KEY", "").strip()
        self.ENABLE_X_API = os.getenv("ENABLE_X_API", "true").lower() == "true"

        # Email newsletter service
        # EMAIL_DRIVER: "resend" (default) or "smtp"
        self.EMAIL_DRIVER = os.getenv("EMAIL_DRIVER", "resend").lower().strip()
        self.EMAIL_SENDER = os.getenv("EMAIL_SENDER", "").strip()
        self.EMAIL_SENDER_NAME = os.getenv("EMAIL_SENDER_NAME", "AI News Digest").strip()

        # Resend driver (https://resend.com) — set RESEND_API_KEY
        self.RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()

        # SMTP driver (e.g. Gmail) — set SMTP_HOST / PORT / USER / PASSWORD
        self.SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
        self.SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
        self.SMTP_USER = os.getenv("SMTP_USER", "").strip()
        self.SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()

        # Subscriber store — pluggable driver
        # SUBSCRIBER_DRIVER: "json" (default, zero-dep) | "sqlite" | "postgres"
        self.SUBSCRIBER_DRIVER = os.getenv("SUBSCRIBER_DRIVER", "json").lower().strip()

        # JSON driver — path to the subscribers JSON file (same pattern as news_cache.json)
        self.SUBSCRIBERS_JSON_PATH = os.getenv("SUBSCRIBERS_JSON_PATH", "subscribers.json").strip()

        # SQLite driver (optional) — path to the .db file
        self.SUBSCRIBERS_DB_PATH = os.getenv("SUBSCRIBERS_DB_PATH", "subscribers.db").strip()

        # PostgreSQL driver (optional) — standard libpq connection string
        # e.g. postgresql://user:password@host:5432/dbname
        self.DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

        self.NEWS_API_QUERIES = [
            "Artificial Intelligence OR AI",
            "Salesforce OR Agentforce",
        ]

        self.RSS_FEEDS = [
            "https://techcrunch.com/category/artificial-intelligence/feed/",
            "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
        ]


config = Config()
