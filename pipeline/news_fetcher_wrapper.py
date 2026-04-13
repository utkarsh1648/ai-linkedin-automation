import logging
from typing import List, Dict
from services.news_fetcher import NewsApiFetcher, RSSFetcher

logger = logging.getLogger(__name__)

def fetch_newsapi(api_key: str, queries: List[str] = None) -> List[Dict]:
    """
    Wrapper for existing NewsApiFetcher.
    Ensures single call efficiency by aggregating queries if needed, 
    but requirements state SINGLE NewsAPI call.
    """
    if queries is None:
        # Default AI broad queries
        queries = ["Artificial Intelligence", "Generative AI", "LLM"]

    # To ensure ONE call, we either pick the primary query or join them logic-wise if the API supports it
    # GNews/NewsAPI 'everything' endpoint supports OR queries.
    # However, the existing NewsApiFetcher.fetch loops through queries.
    # To keep it to ONE call, we'll pass a single combined query.
    
    combined_query = " OR ".join(queries)
    fetcher = NewsApiFetcher(api_key=api_key, queries=[combined_query])
    
    logger.info(f"Fetching news from NewsAPI with query: {combined_query}")
    raw_articles = fetcher.fetch()
    
    # Standardize output format
    # Requirement: title, content, source, url, published_at
    formatted = []
    for art in raw_articles:
        formatted.append({
            "title": art.get("title", ""),
            "content": art.get("content", art.get("description", "")),
            "description": art.get("description", art.get("content", "")[:200]), # Added for AI service compatibility
            "source": art.get("source", {}).get("name", "Unknown") if isinstance(art.get("source"), dict) else art.get("source", "Unknown"),
            "url": art.get("url", ""),
            "published_at": art.get("publishedAt", "")
        })
        
    return formatted[:25]

def fetch_rss(feed_urls: List[str]) -> List[Dict]:
    """
    Wrapper for existing RSSFetcher.
    """
    if not feed_urls:
        return []
        
    fetcher = RSSFetcher(feed_urls=feed_urls)
    logger.info(f"Fetching news from {len(feed_urls)} RSS feeds")
    raw_articles = fetcher.fetch()
    
    formatted = []
    for art in raw_articles:
        formatted.append({
            "title": art.get("title", ""),
            "content": art.get("description", ""),
            "description": art.get("description", "")[:200],
            "source": "RSS Feed",
            "url": art.get("url", ""),
            "published_at": "" # RSS fetcher might not parse date currently
        })
    return formatted
