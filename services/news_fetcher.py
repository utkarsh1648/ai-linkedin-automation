import requests
import xml.etree.ElementTree as ET
import re
from typing import List, Dict, Set
from utils.logger import get_logger

logger = get_logger(__name__)

class BaseFetcher:
    """Abstract base definition for a generic News Fetcher."""
    def fetch(self) -> List[Dict[str, str]]:
        raise NotImplementedError("Subclasses must implement the fetch method.")

class NewsApiFetcher(BaseFetcher):
    """Fetches trending tech news from the NewsAPI service."""
    
    BASE_URL = "https://newsapi.org/v2/everything"

    def __init__(self, api_key: str, queries: List[str]):
        self.api_key = api_key
        self.queries = queries

    def fetch(self) -> List[Dict[str, str]]:
        if not self.api_key:
            logger.error("Missing NEWS_API_KEY")
            return []

        articles = []
        for query in self.queries:
            url = f"{self.BASE_URL}?q={query}&sortBy=publishedAt&language=en&apiKey={self.api_key}"
            try:
                logger.info(f"NewsAPI: Fetching articles for query '{query}'")
                res = requests.get(url, timeout=10)
                if res.status_code == 200:
                    data = res.json().get("articles", [])
                    articles.extend(data[:25])
                else:
                    logger.warning(f"NewsAPI: Non-200 response ({res.status_code}) for query '{query}'")
            except Exception as e:
                logger.error(f"NewsAPI: Error fetching query '{query}': {e}")
        
        return articles

class RSSFetcher(BaseFetcher):
    """Fetches tech news from standard RSS feeds."""
    
    def __init__(self, feed_urls: List[str]):
        self.feed_urls = feed_urls
        
    def fetch(self) -> List[Dict[str, str]]:
        articles = []
        for url in self.feed_urls:
            logger.info(f"RSSFetcher: Fetching from '{url}'")
            try:
                response = requests.get(url, timeout=10)
                if response.status_code != 200:
                    logger.warning(f"RSSFetcher: Failed logic {url} - Status Code {response.status_code}")
                    continue
                
                root = ET.fromstring(response.content)
                for item in root.findall(".//item"):
                    title = item.find("title").text if item.find("title") is not None else ""
                    link = item.find("link").text if item.find("link") is not None else ""
                    description = item.find("description").text if item.find("description") is not None else ""
                    
                    if description:
                        description = re.sub('<[^<]+?>', '', description)[:200]
                    
                    articles.append({
                        "title": title,
                        "description": description,
                        "url": link,
                        "urlToImage": ""
                    })
            except Exception as e:
                logger.error(f"RSSFetcher: Exception parsing {url}: {e}")
        
        return articles

class NewsAggregator:
    """Coordinates various fetchers to produce a unified, deduplicated list of news articles."""
    def __init__(self, fetchers: List[BaseFetcher]):
        self.fetchers = fetchers
        
    def fetch_all(self, limit: int = 50) -> List[Dict[str, str]]:
        all_raw_articles = []
        for fetcher in self.fetchers:
            all_raw_articles.extend(fetcher.fetch())
            
        return self._deduplicate(all_raw_articles, limit)

    def _deduplicate(self, raw_articles: List[Dict[str, str]], limit: int) -> List[Dict[str, str]]:
        processed = []
        seen_urls: Set[str] = set()
        
        for article in raw_articles:
            url = article.get("url", "")
            if url and url not in seen_urls:
                processed.append({
                    "title": article.get("title", ""),
                    "description": article.get("description", ""),
                    "url": url,
                    "urlToImage": article.get("urlToImage", "")
                })
                seen_urls.add(url)
                
                if len(processed) >= limit:
                    break
                    
        logger.info(f"Aggregator: Final deduped article count: {len(processed)}")
        return processed