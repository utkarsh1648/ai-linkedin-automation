import json
from google import genai
from typing import List, Dict
from utils.logger import get_logger
from prompts import (
    SELECT_TOP_TRENDING_PROMPT,
    GENERATE_SOCIAL_POST_PROMPT,
    GENERATE_NEWSLETTER_INTRO_PROMPT
)
logger = get_logger(__name__)

class AIService:
    """Encapsulates all generative AI operations using the Gemini model."""
    def __init__(self, api_key: str):
        if not api_key:
            logger.warning("Empty GEMINI_API_KEY provided.")
        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-flash-latest" 

    def select_top_trending(self, articles: List[Dict[str, str]], count: int = 10) -> List[Dict[str, str]]:
        """Analyzes a large pool of articles to select the most trending ones."""
        if not articles:
            return []

        articles_list = "\n".join([f"[{i}] {a.get('title', 'Unknown')}" for i, a in enumerate(articles)])

        prompt = SELECT_TOP_TRENDING_PROMPT.format(
            article_count=len(articles),
            count=count,
            articles_list=articles_list
        )
        
        try:
            logger.info("AIService: Sending `select_top_trending` request to Gemini.")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={'response_mime_type': 'application/json'}
            )
            
            selected_indices = json.loads(response.text)
            
            filtered_articles = [articles[idx] for idx in selected_indices if 0 <= idx < len(articles)]
            return filtered_articles[:count] if filtered_articles else articles[:count]

        except Exception as e:
            logger.error(f"AIService: Error in select_top_trending - {e}")
            return articles[:count]

    def generate_social_post(self, articles: List[Dict[str, str]]) -> str:
        """Generates a LinkedIn post based on the top stories."""
        if not articles:
            return ""

        articles_text = "\n".join([f"Article {i+1}: {a.get('title')} - {a.get('description')} ({a.get('url')})" for i, a in enumerate(articles)])

        prompt = GENERATE_SOCIAL_POST_PROMPT.format(
            articles_text=articles_text
        )
        try:
            logger.info("AIService: generating social post.")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"AIService: Failed to generate social post - {e}")
            return ""

    def generate_newsletter_intro(self, articles: List[Dict[str, str]]) -> str:
        """Generates a short intro paragraph for the newsletter."""
        if not articles:
            return "Here are the top trending AI news articles for today!"

        articles_text = "\n".join([f"Article {i+1}: {a.get('title')}" for i, a in enumerate(articles)])

        prompt = GENERATE_NEWSLETTER_INTRO_PROMPT.format(
            article_count=len(articles),
            articles_text=articles_text
        )
        try:
            logger.info("AIService: generating newsletter intro.")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"AIService: Failed to generate intro - {e}")
            return ""
