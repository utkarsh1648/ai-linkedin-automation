import os
from dotenv import load_dotenv

class Config:
    def __init__(self):
        load_dotenv()
        self.NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
        self.SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
        self.SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID", "")
        self.BUFFER_TOKEN = os.getenv("BUFFER_TOKEN", "")
        self.CHANNEL_ID = os.getenv("CHANNEL_ID", "")
        self.BASE_PUBLIC_URL = os.getenv("BASE_PUBLIC_URL", "http://localhost:8000")
        self.MEDIA_DIR = "media"
        
        self.NEWS_API_QUERIES = [
            "Artificial Intelligence OR AI",
            "Salesforce OR Agentforce"
        ]
        
        self.RSS_FEEDS = [
            "https://techcrunch.com/category/artificial-intelligence/feed/",
            "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml"
        ]

config = Config()
