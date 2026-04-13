import json
from google import genai
from typing import List, Dict
from utils.logger import get_logger

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

        prompt = f"""
Analyze the following {len(articles)} news items. 
Select the TOP {count} most trending, innovative, or high-impact articles. 
Look for major product launches, breakthroughs, or market-shifting news.

News Articles:
{articles_list}

Return ONLY a JSON list of the integers representing the indices of your selected articles. 
Example Output: [0, 4, 12, 19, 21]
"""
        
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

        prompt = f"""
You are a senior LinkedIn content strategist specializing in AI thought leadership.
Transform the following AI news into a high-impact LinkedIn post.

Input news: 
{articles_text}

## Writing Style:
- Sharp, concise, and insightful.
- Professional but conversational.
- Focus on trust, impact, and real-world implications.
- Avoid hype and generic phrases like "revolutionary" or "game-changing".
- Make it feel human, not AI-generated.

## Structure:
1. Strong hook (1-2 lines, thought-provoking).
2. Context (what happened).
3. Insight (why it matters for industry/society).
4. Deeper reflection (leadership, trust, implications).
5. Closing question (to drive engagement).

## Rules:
- Use short paragraphs (1-2 lines each).
- No emoji overload (max 1-2 if needed).
- Keep the length under 150 words.
- Encourage discussion, not conclusions.
- IMPORTANT: Include the source link (URL) of the chosen article at the very bottom.
"""
        try:
            logger.info("AIService: generating social post.")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"AIService: Failed to generate social post - {e}")
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                logger.warning("AIService: Rate limit exceeded. Using MOCK FALLBACK post for testing.")
                return """🚀 The "AI Chat" phase is over. We are entering the era of functional AI Agents.

Recent releases in agentic patterns signal a shift from simple prompting to complex, autonomous orchestration.

This transition isn't just about productivity; it's about redefining how we interact with technology at a fundamental level.

Insight: The real winner in the AI race isn't the one with the biggest model, but the one with the most reliable agentic ecosystem.

Are you moving past the chat interface this year?

Source: https://techcrunch.com/2026/04/08/poke-makes-ai-agents-as-easy-as-sending-a-text/"""
            return ""

    def generate_newsletter_intro(self, articles: List[Dict[str, str]]) -> str:
        """Generates a short intro paragraph for the newsletter."""
        if not articles:
            return "Here are the top trending AI news articles for today!"

        articles_text = "\n".join([f"Article {i+1}: {a.get('title')}" for i, a in enumerate(articles)])

        prompt = f"""
You are an AI news editor writing a newsletter.
Based on the following top {len(articles)} AI news articles, write a short, engaging 2-3 sentence introductory paragraph summarizing the overall trends or highlights of today's AI news.

Articles:
{articles_text}
"""
        try:
            logger.info("AIService: generating newsletter intro.")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"AIService: Failed to generate intro - {e}")
            return "The AI landscape is shifting rapidly today, with a major focus on agentic workflows and cross-industry infrastructure partnerships."
