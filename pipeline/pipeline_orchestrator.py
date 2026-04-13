import os
import json
import logging
from typing import List, Dict
from dotenv import load_dotenv

# Setup logger (configuration should be handled by the entry point script)
logger = logging.getLogger(__name__)

# Import modular components
from pipeline.x_trends import fetch_x_trends, filter_ai_trends
from pipeline.news_fetcher_wrapper import fetch_newsapi, fetch_rss
from pipeline.news_processor import clean_news, enrich_with_trends, rank_news

def load_pipeline_config(config_path: str = "pipeline_config.json") -> dict:
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        return {}

def handle_caching(articles: List[Dict], cache_file: str) -> List[Dict]:
    """Prevent redundant reporting by caching seen article URLs."""
    seen_urls = set()
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
            
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(list(seen_urls), f)
    except Exception as e:
        logger.error(f"Error writing cache at {cache_file}: {e}")
        
    return new_articles

def main_pipeline():
    """
    Main orchestrator for the AI News Pipeline.
    1. Fetch X Trends
    2. Filter AI Trends
    3. Fetch NewsAPI & RSS
    4. Clean & Enrich News
    5. Cache & Rank & Return
    """
    load_dotenv()
    
    config = load_pipeline_config()
    gnews_cfg = config.get("gnews", {})
    x_cfg = config.get("x_trends", {})
    rss_cfg = config.get("rss", {}) # Assume rss feeds are in config or hardcoded
    cache_file = config.get("cache", {}).get("file_path", "news_cache.json")
    
    API_KEY_X = os.getenv("X_API_KEY", "")
    API_KEY_NEWS = os.getenv("NEWS_API_KEY", "")
    ENABLE_X_API = os.getenv("ENABLE_X_API", "true").lower() == "true"
    
    if not API_KEY_NEWS:
        logger.error("NEWS_API_KEY is missing. Pipeline aborted.")
        return []

    logger.info("--- Starting Enhanced AI News Pipeline ---")

    # 1. Fetch & Filter X Trends
    top_ai_trends = []
    if ENABLE_X_API:
        raw_trends = fetch_x_trends(API_KEY_X, x_cfg.get("woeid", 1))
        top_ai_trends = filter_ai_trends(
            raw_trends, 
            keywords=x_cfg.get("ai_keywords", ["ai", "gpt"])
        )
        
        if top_ai_trends:
            logger.info(f"Top AI Trends identified: {[t['trend_name'] for t in top_ai_trends]}")
    else:
        logger.info("X Trends integration is disabled via feature flag.")

    # 2. Fetch News (Aggregated)
    # Fetch from NewsAPI
    news_queries = gnews_cfg.get("queries", ["AI", "Generative AI", "LLM"])
    raw_articles = fetch_newsapi(API_KEY_NEWS, queries=news_queries)
    
    # Fetch from RSS (if URLs provided in config or elsewhere)
    # Using config.py fallback if config_loader is empty for RSS
    from config import config as app_config
    rss_urls = app_config.RSS_FEEDS
    rss_articles = fetch_rss(rss_urls)
    
    combined_raw = raw_articles + rss_articles
    
    # 3. Clean Data
    cleaned_articles = clean_news(combined_raw)
    
    # 4. Enrich with Trends
    enriched_articles = enrich_with_trends(cleaned_articles, top_ai_trends)
    
    # 5. Cache Avoidance
    fresh_articles = handle_caching(enriched_articles, cache_file)
    
    # 6. Rank by Trend Context
    final_articles = rank_news(fresh_articles)
    
    logger.info(f"--- Pipeline Finished: {len(final_articles)} fresh articles ready ---")
    return final_articles

if __name__ == "__main__":
    # Setup logging for standalone execution
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    results = main_pipeline()
    print(json.dumps(results, indent=2))
