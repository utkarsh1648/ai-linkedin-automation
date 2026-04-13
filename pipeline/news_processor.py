import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

def clean_news(articles: List[Dict]) -> List[Dict]:
    """
    Cleans news articles:
    - Removes empty content
    - Removes very short content (<50 chars)
    - Deduplicates by title
    """
    seen_titles = set()
    cleaned = []
    
    for art in articles:
        title = art.get("title", "").strip()
        content = art.get("content", "").strip()
        
        if not title or not content:
            continue
            
        if len(content) < 50:
            continue
            
        title_lower = title.lower()
        if title_lower not in seen_titles:
            seen_titles.add(title_lower)
            cleaned.append(art)
            
    logger.info(f"Cleaned news: {len(articles)} -> {len(cleaned)} articles")
    return cleaned

def enrich_with_trends(articles: List[Dict], top_trends: List[Dict]) -> List[Dict]:
    """
    Enriches articles with trend context.
    Matches trends with news articles using keyword matching.
    Adds field: "trend_context": ["trend1", "trend2"]
    """
    if not top_trends:
        for art in articles:
            art["trend_context"] = []
        return articles

    for art in articles:
        matched_trends = []
        # Combine title and content for better matching
        search_text = f"{art.get('title', '')} {art.get('content', '')}".lower()
        
        for trend in top_trends:
            trend_name = trend.get("trend_name", "").lower()
            # Remove '#' if present for easier matching
            clean_trend = trend_name.replace("#", "")
            
            if clean_trend in search_text:
                matched_trends.append(trend.get("trend_name"))
        
        art["trend_context"] = matched_trends
        
    return articles

def rank_news(articles: List[Dict]) -> List[Dict]:
    """
    Ranks news articles by the number of matched trends.
    Prioritizes articles that match more trends.
    """
    # Sort descending by the length of trend_context list
    ranked = sorted(
        articles, 
        key=lambda x: len(x.get("trend_context", [])), 
        reverse=True
    )
    return ranked
