import json
from typing import List, Dict

from config import config
from utils.logger import get_logger
from pipeline.x_trends import fetch_x_trends, filter_ai_trends
from pipeline.news_processor import clean_news, enrich_with_trends, rank_news
from services.news_fetcher import NewsApiFetcher, RSSFetcher, NewsAggregator

logger = get_logger(__name__)


def _load_pipeline_config(config_path: str = "pipeline_config.json") -> dict:
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load pipeline config from '{config_path}': {e}")
        return {}


def _handle_caching(articles: List[Dict], cache_file: str) -> List[Dict]:
    """Filters out previously seen articles (by URL) and writes the updated cache."""
    seen_urls: set = set()

    try:
        import os
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                seen_urls = set(json.load(f))
    except Exception as e:
        logger.error(f"Error reading cache '{cache_file}': {e}")

    new_articles = [a for a in articles if a.get("url") and a["url"] not in seen_urls]
    seen_urls.update(a["url"] for a in new_articles)

    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(list(seen_urls), f)
    except Exception as e:
        logger.error(f"Error writing cache '{cache_file}': {e}")

    return new_articles


def main_pipeline() -> List[Dict]:
    """
    Orchestrates the AI news pipeline:
      1. Fetch & filter X trends
      2. Fetch NewsAPI + RSS articles via NewsAggregator
      3. Clean, enrich with trend context, cache, rank
    """
    if not config.NEWS_API_KEY:
        logger.error("NEWS_API_KEY is missing — pipeline aborted")
        return []

    pipeline_cfg = _load_pipeline_config()
    gnews_cfg = pipeline_cfg.get("gnews", {})
    x_cfg = pipeline_cfg.get("x_trends", {})
    cache_file = pipeline_cfg.get("cache", {}).get("file_path", "news_cache.json")

    logger.info("--- Starting Enhanced AI News Pipeline ---")

    # Step 1: X Trends (optional, controlled by feature flag)
    top_ai_trends: List[Dict] = []
    if config.ENABLE_X_API:
        raw_trends = fetch_x_trends(config.X_API_KEY, x_cfg.get("woeid", 1))
        top_ai_trends = filter_ai_trends(raw_trends, keywords=x_cfg.get("ai_keywords", ["ai", "gpt"]))
        if top_ai_trends:
            logger.info(f"Top AI trends: {[t['trend_name'] for t in top_ai_trends]}")
    else:
        logger.info("X Trends disabled via ENABLE_X_API flag")

    # Step 2: Aggregate news from NewsAPI and RSS
    queries = gnews_cfg.get("queries", config.NEWS_API_QUERIES)
    combined_query = " OR ".join(queries)
    aggregator = NewsAggregator([
        NewsApiFetcher(api_key=config.NEWS_API_KEY, queries=[combined_query]),
        RSSFetcher(feed_urls=config.RSS_FEEDS),
    ])
    raw_articles = aggregator.fetch_all()

    # Step 3: Process — clean → enrich → cache → rank
    cleaned = clean_news(raw_articles)
    enriched = enrich_with_trends(cleaned, top_ai_trends)
    fresh = _handle_caching(enriched, cache_file)
    final = rank_news(fresh)

    logger.info(f"--- Pipeline finished: {len(final)} fresh articles ready ---")
    return final


if __name__ == "__main__":
    import json as _json
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    results = main_pipeline()
    print(_json.dumps(results, indent=2))
