import os
from dotenv import load_dotenv


class Config:
    def __init__(self):
        load_dotenv(override=True)
        self.NEWS_API_KEY = os.getenv("NEWS_API_KEY", "").strip().strip('"')
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip().strip('"')
        self.SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "").strip().strip('"')
        self.SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID", "").strip().strip('"')
        self.BUFFER_TOKEN = os.getenv("BUFFER_TOKEN", "").strip().strip('"')
        self.CHANNEL_ID = os.getenv("CHANNEL_ID", "").strip().strip('"')
        self.BUFFER_CHANNELS_RAW = os.getenv("BUFFER_CHANNELS", "").strip().strip('"')
        self.BUFFER_CHANNELS = self._parse_channels()

        self.BASE_PUBLIC_URL = os.getenv("BASE_PUBLIC_URL", "https://acronymous-losingly-arianna.ngrok-free.dev").strip().strip('"')
        self.IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", "").strip().strip('"')
        self.MEDIA_DIR = "media"

        # Storage & Database
        self.DATABASE_URL = os.getenv("DATABASE_URL", "").strip().strip('"')
        # Drivers: 'json' or 'postgres'
        self.STORAGE_DRIVER = os.getenv("STORAGE_DRIVER", "json").strip().lower()

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

        # Storage & Database
        # STORAGE_DRIVER: "json" (default) or "postgres"
        self.STORAGE_DRIVER = os.getenv("STORAGE_DRIVER", "json").strip().lower()
        self.DATABASE_URL = os.getenv("DATABASE_URL", "").strip().strip('"')

        # JSON driver — path to the subscribers JSON file
        self.SUBSCRIBERS_JSON_PATH = os.getenv("SUBSCRIBERS_JSON_PATH", "subscribers.json").strip()
        # SQLite driver (optional)
        self.SUBSCRIBERS_DB_PATH = os.getenv("SUBSCRIBERS_DB_PATH", "subscribers.db").strip()

        self.NEWS_API_QUERIES = [
            "Artificial Intelligence OR AI",
            "Salesforce OR Agentforce",
        ]

        self.RSS_FEEDS = [
            "https://techcrunch.com/category/artificial-intelligence/feed/",
            "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
        ]

    def _parse_channels(self) -> dict:
        """
        Parses BUFFER_CHANNELS env var.
        Format: "id1:style1:Name1;id2:style2:Name2"
        Returns a dict: { "id1": {"style": "style1", "name": "Name1"}, ... }
        """
        channels = {}
        if self.BUFFER_CHANNELS_RAW:
            pairs = self.BUFFER_CHANNELS_RAW.split(";")
            for pair in pairs:
                if ":" in pair:
                    # Use maxsplit=3 to only split the ID, Style, and Name. 
                    # Everything after the 3rd colon is the Icon.
                    parts = pair.split(":", 3)
                    cid = parts[0].strip()
                    style = parts[1].strip().lower() if len(parts) > 1 else "professional"
                    name = parts[2].strip() if len(parts) > 2 else f"{style.capitalize()} Channel"
                    icon = parts[3].strip() if len(parts) > 3 else None
                    
                    channels[cid] = {"style": style, "name": name, "icon": icon}
        
        if not channels and self.CHANNEL_ID:
            channels[self.CHANNEL_ID] = {"style": "linkedin", "name": "LinkedIn"}
            
        return channels


config = Config()
