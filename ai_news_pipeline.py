import os
import json
import logging
from typing import List, Dict, Optional
import requests

# Setup logging for debugging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config(config_path: str = "pipeline_config.json") -> dict:
    """Loads configuration options from a JSON/YAML file."""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        return {}

def fetch_x_trends(api_key: str, woeid: int) -> List[Dict]:
    """1. Fetches trending topics from X (Twitter) API."""
    if not api_key:
        logger.warning("No X_API_KEY provided. Skipping X trends integration.")
        return []

    url = f"https://api.twitter.com/2/trends/by/woeid/{woeid}"
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        logger.info(f"Requesting X Trends for WOEID: {woeid}...")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Twitter API often returns [{ "trends": [...] }] structure
        if isinstance(data, list) and len(data) > 0 and 'trends' in data[0]:
            return data[0]['trends']
        return data if isinstance(data, list) else []
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching X trends API calls: {e}")
        return []

def filter_ai_trends(trends_data: List[Dict], keywords: List[str], top_k: int = 2) -> List[Dict]:
    """2. Filters trends to only include AI-related ones by keywords and ranks by volume."""
    filtered = []
    
    for trend in trends_data:
        # Compatibility with different trend object fields (v1.1 vs v2 structure)
        name = trend.get("trend_name", trend.get("name", ""))
        tweet_count = trend.get("tweet_count", trend.get("tweet_volume"))
        
        if tweet_count is None:
            tweet_count = 0  # Default to zero if volume not available
            
        name_lower = name.lower()
        if any(kw in name_lower for kw in keywords):
            filtered.append({
                "trend_name": name,
                "tweet_count": int(tweet_count)
            })
            
    # Sort descending by tweet_count and take Top K
    filtered.sort(key=lambda x: x["tweet_count"], reverse=True)
    return filtered[:top_k]

def build_combined_query(base_query: str, top_trends: List[Dict]) -> str:
    """3. Intelligently combines X trends to avoid redundant API queries to GNews."""
    if not top_trends:
        return base_query
    
    trend_queries = []
    for t in top_trends:
        # Convert trend like "#GPT5" to "GPT5 AI news"
        clean_trend = t["trend_name"].replace("#", "")
        # Enclose in quotes to match exactly
        trend_queries.append(f'"{clean_trend} AI news"')
        
    trends_joined = " OR ".join(trend_queries)
    return f"({base_query}) OR ({trends_joined})"

def fetch_gnews(api_key: str, query: str, max_articles: int = 20) -> List[Dict]:
    """4. Fetch articles from GNews using single optimized query."""
    if not api_key:
        logger.warning("No GNEWS_API_KEY provided.")
        return []

    url = "https://gnews.io/api/v4/search"
    params = {
        "q": query,
        "apikey": api_key,
        "max": max_articles,
        "lang": "en",
        "sortby": "publishedAt"
    }

    try:
        logger.info(f"Running optimized GNews Query: {query}")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        articles = data.get("articles", [])
        
        # Map to structured news object
        return [{
            "title": a.get("title", ""),
            "content": a.get("content", ""),
            "description": a.get("description", ""),
            "source": a.get("source", {}).get("name", "Unknown"),
            "url": a.get("url", ""),
            "published_at": a.get("publishedAt", "")
        } for a in articles]
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching from GNews: {e}")
        return []

def deduplicate_news(articles: List[Dict]) -> List[Dict]:
    """5. Deduplicates by Title and removes low-quality/empty content."""
    seen_titles = set()
    cleaned = []
    
    for a in articles:
        # Data Cleaning Rule
        content = a.get("content", "")
        desc = a.get("description", "")
        
        if not content.strip() or len(desc.strip()) < 50:
            continue
            
        title = a.get("title", "").strip().lower()
        if title and title not in seen_titles:
            seen_titles.add(title)
            # Remove "description" internal temp field if we want to stick to exact Output Format but keep it for contextual reasons
            cleaned.append(a)
            
    return cleaned

def cache_handler(articles: List[Dict], cache_file: str) -> List[Dict]:
    """6. Prevent redundant reporting by caching seen article URLs."""
    seen_urls = set()
    
    # Read Cache
    try:
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                seen_urls = set(json.load(f))
    except Exception as e:
        logger.error(f"Error reading cache at {cache_file}: {e}")
        
    new_articles = []
    for a in articles:
        url = a.get("url")
        if url and url not in seen_urls:
            new_articles.append(a)
            seen_urls.add(url)
            
    # Write Cache
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(list(seen_urls), f)
    except Exception as e:
        logger.error(f"Error writing to cache at {cache_file}: {e}")
        
    return new_articles

def enrich_trend_context(articles: List[Dict], trends: List[Dict]) -> List[Dict]:
    """Validates if any of the fetched articles explicitly match our AI trends."""
    if not trends:
        return articles
        
    for a in articles:
        text_corpus = f"{a.get('title', '')} {a.get('description', '')} {a.get('content', '')}".lower()
        matched = []
        for t in trends:
            clean_trend = t["trend_name"].replace("#", "").lower()
            if clean_trend in text_corpus:
                matched.append(t["trend_name"])
                
        if matched:
            a["trend_context"] = f"Related to X Trend: {', '.join(matched)}"
            
    # Clean up output representation
    for a in articles:
        if "description" in a:
            del a["description"]
            
    return articles

def main_pipeline() -> List[Dict]:
    """
    7. Orchestrator Pipeline
    Fetches latest AI news + X trends, cleanly merged & cached.
    """
    logger.info("=== Starting AI News Data Pipeline ===")
    
    config = load_config()
    gnews_cfg = config.get("gnews", {})
    x_cfg = config.get("x_trends", {})
    cache_file = config.get("cache", {}).get("file_path", "news_cache.json")
    
    API_KEY_GNEWS = os.environ.get("GNEWS_API_KEY", "")
    API_KEY_X = os.environ.get("X_API_KEY", "")
    
    # Phase 1: Trend Identification
    raw_trends = fetch_x_trends(API_KEY_X, x_cfg.get("woeid", 1))
    ai_trends = filter_ai_trends(
        trends_data=raw_trends,
        keywords=x_cfg.get("ai_keywords", ["ai", "gpt"]),
        top_k=x_cfg.get("top_k_trends", 2)
    )
    
    if ai_trends:
        logger.info(f"Top actionable AI trends identified: {ai_trends}")
    else:
        logger.info("No actionable AI trends identified at the moment.")
        
    # Phase 2: Fetch and Combine Content
    base_query = gnews_cfg.get("query", "AI")
    combined_query = build_combined_query(base_query, ai_trends)
    
    logger.info("Fetching articles using unified GNews query...")
    raw_articles = fetch_gnews(
        api_key=API_KEY_GNEWS,
        query=combined_query,
        max_articles=gnews_cfg.get("max_articles", 20)
    )
    
    # Phase 3: Sanitize and Structure Data
    clean_unique_arts = deduplicate_news(raw_articles)
    enriched_arts = enrich_trend_context(clean_unique_arts, ai_trends)
    
    # Phase 4: Cache Avoidance Strategy
    logger.info(f"Comparing {len(enriched_arts)} unique structured articles against caching limits...")
    final_fresh_articles = cache_handler(enriched_arts, cache_file)
    
    logger.info(f"=== Pipeline Complete: Yielded {len(final_fresh_articles)} new stories ===")
    return final_fresh_articles

if __name__ == "__main__":
    # --- Example Usage --- #
    # Set fake credentials internally for local testing print demo:
    # os.environ["GNEWS_API_KEY"] = "your_test_key_here"
    # os.environ["X_API_KEY"] = "your_twitter_bearer_token"
    
    results = main_pipeline()
    
    print(f"\n--- Output Dump: {len(results)} new articles ---")
    for idx, article in enumerate(results, 1):
        print(f"{idx}. {article['title']}")
        if "trend_context" in article:
            print(f"   🔥 {article['trend_context']}")
        print(f"   🔗 {article['url']}")
        print()
