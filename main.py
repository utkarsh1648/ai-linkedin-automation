import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from config import config
from utils.logger import get_logger
from pipeline.pipeline_orchestrator import main_pipeline
from services.ai_service import AIService
from services.newsletter_generator import HTMLRenderer
from services.slack_notifier import send_slack_notification
from services.buffer_poster import post_to_linkedin
from api.slack_actions import router as slack_router

logger = get_logger(__name__)

app = FastAPI()
app.include_router(slack_router)

# Mount local media directory to serve files publicly for Buffer/LinkedIn
os.makedirs(config.MEDIA_DIR, exist_ok=True)
app.mount(f"/{config.MEDIA_DIR}", StaticFiles(directory=config.MEDIA_DIR), name="media")

def run_pipeline() -> None:
    logger.info("Starting AI LinkedIn Automation Pipeline...")

    # 1. Dependency Injection setup
    ai_service = AIService(config.GEMINI_API_KEY)
    
    # 2. Fetch Aggregated News using the enhanced pipeline (X Trends + NewsAPI + RSS + Caching)
    all_articles = main_pipeline()
    
    if not all_articles:
        logger.error("No news found. Aborting pipeline.")
        return

    # 3. Filter using AI
    logger.info("Deciding top trending using AI...")
    top_articles = ai_service.select_top_trending(all_articles, count=10)
    logger.info(f"Selected {len(top_articles)} top trending articles.")

    # 4. Generate Content
    logger.info("Generating LinkedIn post using Gemini...")
    post = ai_service.generate_social_post(top_articles)
    
    if post:
        logger.info(f"Generated Post:\n{post}")
        # 5. Send to Slack for Approval
        response = send_slack_notification(post)
        logger.info("Post sent to Slack for approval.")
    else:
        logger.warning("LinkedIn post generation failed. Skipping Slack notification.")

    # 6. Generate Newsletter
    logger.info("Generating HTML Newsletter intro...")
    intro_text = ai_service.generate_newsletter_intro(top_articles)
    
    logger.info("Rendering final HTML Newsletter...")
    newsletter_html = HTMLRenderer.render_newsletter(intro_text, top_articles)
    
    with open("output_newsletter.html", "w", encoding="utf-8") as f:
        f.write(newsletter_html)
        
    logger.info("Newsletter saved to 'output_newsletter.html'. Pipeline complete!")


if __name__ == "__main__":
    run_pipeline()