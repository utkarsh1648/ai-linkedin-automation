import requests
import logging
from typing import List, Dict
from utils.logger import get_logger

logger = get_logger(__name__)

def fetch_x_trends(api_key: str, woeid: int = 1) -> List[Dict]:
    """
    Fetches trending topics from X (Twitter) API v2.
    Endpoint: /2/trends/by/woeid/{woeid}
    """
    if not api_key:
        logger.error("X_API_KEY is missing. Cannot fetch trends.")
        return []

    url = f"https://api.twitter.com/2/trends/by/woeid/{woeid}"
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        logger.info(f"Fetching X trends for WOEID: {woeid}")
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 402:
            logger.warning("X Trends API returned 402 (Payment Required). This usually means your X API tier does not support this endpoint. Skipping trends.")
            return []
            
        response.raise_for_status()
        data = response.json()
        
        # Structure expected: list of trend objects or nested in a 'data' field
        # The prompt specifies fields: trend_name, tweet_count
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and 'data' in data:
            return data['data']
        return []
    except Exception as e:
        logger.error(f"Error fetching X trends: {e}")
        return []

def filter_ai_trends(trends_data: List[Dict], keywords: List[str] = None) -> List[Dict]:
    """
    Filters trends to keep only AI-relevant ones and ranks them by tweet_count.
    """
    if keywords is None:
        keywords = ["ai", "gpt", "llm", "agents", "openai", "genai"]
    
    filtered_trends = []
    for trend in trends_data:
        # Extract fields as specified in requirements
        name = trend.get("trend_name", trend.get("name", ""))
        count = trend.get("tweet_count", trend.get("tweet_volume", 0))
        
        if not name:
            continue
            
        name_lower = name.lower()
        if any(kw in name_lower for kw in keywords):
            filtered_trends.append({
                "trend_name": name,
                "tweet_count": count if count is not None else 0
            })
    
    # Sort by tweet_count descending
    filtered_trends.sort(key=lambda x: x["tweet_count"], reverse=True)
    
    # Keep top 2-3 as requested
    return filtered_trends[:3]
