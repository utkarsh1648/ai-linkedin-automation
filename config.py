import os
from dotenv import load_dotenv


class Config:
    def __init__(self):
        load_dotenv(override=True)
        
        def get_env(key, default=""):
            val = os.getenv(key, "").strip().strip('"')
            return val if val else default

        self.NEWS_API_KEY = get_env("NEWS_API_KEY")
        self.GEMINI_API_KEY = get_env("GEMINI_API_KEY")
        self.SLACK_BOT_TOKEN = get_env("SLACK_BOT_TOKEN")
        self.SLACK_CHANNEL_ID = get_env("SLACK_CHANNEL_ID")
        self.BUFFER_TOKEN = get_env("BUFFER_TOKEN")
        self.CHANNEL_ID = get_env("CHANNEL_ID")
        self.BUFFER_CHANNELS_RAW = get_env("BUFFER_CHANNELS")
        self.BUFFER_CHANNELS = self._parse_channels()

        self.BASE_PUBLIC_URL = get_env("BASE_PUBLIC_URL", "https://acronymous-losingly-arianna.ngrok-free.dev")
        self.IMGBB_API_KEY = get_env("IMGBB_API_KEY")
        self.MEDIA_DIR = "media"

        # Storage & Database
        self.DATABASE_URL = get_env("DATABASE_URL")
        # Drivers: 'json' or 'postgres'
        self.STORAGE_DRIVER = get_env("STORAGE_DRIVER", "json").lower()

        # X (Twitter) Trends integration
        self.X_API_KEY = get_env("X_API_KEY")
        self.ENABLE_X_API = get_env("ENABLE_X_API", "true").lower() == "true"

        # Email newsletter service
        # EMAIL_DRIVER: "resend" (default) or "smtp"
        self.EMAIL_DRIVER = get_env("EMAIL_DRIVER", "resend").lower()
        self.EMAIL_SENDER = get_env("EMAIL_SENDER")
        self.EMAIL_SENDER_NAME = get_env("EMAIL_SENDER_NAME", "AI News Digest")

        # Resend driver (https://resend.com) — set RESEND_API_KEY
        self.RESEND_API_KEY = get_env("RESEND_API_KEY")

        # SMTP driver (e.g. Gmail) — set SMTP_HOST / PORT / USER / PASSWORD
        self.SMTP_HOST = get_env("SMTP_HOST", "smtp.gmail.com")
        self.SMTP_PORT = int(get_env("SMTP_PORT", "587"))
        self.SMTP_USER = get_env("SMTP_USER")
        self.SMTP_PASSWORD = get_env("SMTP_PASSWORD")

        # JSON driver — path to the subscribers JSON file
        self.SUBSCRIBERS_JSON_PATH = get_env("SUBSCRIBERS_JSON_PATH", "subscribers.json")
        # SQLite driver (optional)
        self.SUBSCRIBERS_DB_PATH = get_env("SUBSCRIBERS_DB_PATH", "subscribers.db")

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
            
        from utils.logger import get_logger
        logger = get_logger("config")
        logger.info(f"Config: Parsed {len(channels)} Buffer channels.")
        return channels


config = Config()
