import requests
import xml.etree.ElementTree as ET
import re
from typing import List, Dict, Set
from utils.logger import get_logger

logger = get_logger(__name__)

# Shared article schema keys: title, description, content, source, url, published_at, urlToImage


class BaseFetcher:
    """Interface for a news source fetcher. Subclasses must implement fetch()."""

    def fetch(self) -> List[Dict[str, str]]:
        raise NotImplementedError


class NewsApiFetcher(BaseFetcher):
    """Fetches AI news from the NewsAPI /v2/everything endpoint."""

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
                logger.info(f"NewsAPI: fetching query '{query}'")
                res = requests.get(url, timeout=10)
                if res.status_code == 200:
                    for raw in res.json().get("articles", [])[:25]:
                        articles.append(self._normalize(raw))
                else:
                    logger.warning(f"NewsAPI: status {res.status_code} for query '{query}'")
            except Exception as e:
                logger.error(f"NewsAPI: error for query '{query}': {e}")

        return articles

    @staticmethod
    def _normalize(raw: dict) -> Dict[str, str]:
        source = raw.get("source", {})
        return {
            "title": raw.get("title", ""),
            "description": raw.get("description", ""),
            "content": raw.get("content", raw.get("description", "")),
            "source": source.get("name", "Unknown") if isinstance(source, dict) else str(source),
            "url": raw.get("url", ""),
            "published_at": raw.get("publishedAt", ""),
            "urlToImage": raw.get("urlToImage", ""),
        }


class RSSFetcher(BaseFetcher):
    """Fetches news from standard RSS feeds."""

    def __init__(self, feed_urls: List[str]):
        self.feed_urls = feed_urls

    def fetch(self) -> List[Dict[str, str]]:
        articles = []
        for url in self.feed_urls:
            logger.info(f"RSSFetcher: fetching '{url}'")
            try:
                response = requests.get(url, timeout=10)
                if response.status_code != 200:
                    logger.warning(f"RSSFetcher: status {response.status_code} for '{url}'")
                    continue

                root = ET.fromstring(response.content)
                for item in root.findall(".//item"):
                    title = item.find("title")
                    link = item.find("link")
                    desc = item.find("description")

                    description = desc.text if desc is not None else ""
                    if description:
                        description = re.sub("<[^<]+?>", "", description)[:200]

                    articles.append({
                        "title": title.text if title is not None else "",
                        "description": description,
                        "content": description,
                        "source": "RSS Feed",
                        "url": link.text if link is not None else "",
                        "published_at": "",
                        "urlToImage": "",
                    })
            except Exception as e:
                logger.error(f"RSSFetcher: error parsing '{url}': {e}")

        return articles


class NewsAggregator:
    """Coordinates fetchers and returns a deduplicated, normalized article list."""

    def __init__(self, fetchers: List[BaseFetcher]):
        self.fetchers = fetchers

    def fetch_all(self, limit: int = 50) -> List[Dict[str, str]]:
        raw: List[Dict[str, str]] = []
        for fetcher in self.fetchers:
            raw.extend(fetcher.fetch())
        return self._deduplicate(raw, limit)

    def _deduplicate(self, raw_articles: List[Dict[str, str]], limit: int) -> List[Dict[str, str]]:
        seen_urls: Set[str] = set()
        processed = []

        for article in raw_articles:
            url = article.get("url", "")
            if url and url not in seen_urls:
                processed.append(article)
                seen_urls.add(url)
                if len(processed) >= limit:
                    break

        logger.info(f"Aggregator: {len(processed)} unique articles after deduplication")
        return processed