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

        self.NEWS_API_QUERIES = [
            "Artificial Intelligence OR AI",
            "Salesforce OR Agentforce",
        ]

        self.RSS_FEEDS = [
            "https://techcrunch.com/category/artificial-intelligence/feed/",
            "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
        ]


config = Config()
