import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import config
from utils.logger import get_logger
from pipeline.pipeline_orchestrator import main_pipeline
from services.ai_service import AIService
from services.newsletter_generator import HTMLRenderer
from services.slack_notifier import send_slack_notification
from services.visual_service import VisualService
from utils.file_handler import upload_to_imgbb
from api.slack_actions import router as slack_router
from api.subscribers import router as subscribers_router

logger = get_logger(__name__)

app = FastAPI(title="AI LinkedIn Automation")
app.include_router(slack_router)
app.include_router(subscribers_router)

# Mount local media directory to serve uploaded images publicly
os.makedirs(config.MEDIA_DIR, exist_ok=True)
app.mount(f"/{config.MEDIA_DIR}", StaticFiles(directory=config.MEDIA_DIR), name="media")

@app.on_event("startup")
async def startup_event():
    """Warms up API connections on startup."""
    from services.slack_client import slack_client
    logger.info("Warming up Slack connection...")
    try:
        # Just a tiny call to ensure DNS and SSL are cached
        slack_client.post("api.test", {})
    except:
        pass


def run_pipeline() -> None:
    logger.info("Starting AI LinkedIn Automation Pipeline...")

    ai_service = AIService(config.GEMINI_API_KEY)

    # 1. Fetch aggregated news (X Trends + NewsAPI + RSS + caching)
    all_articles = main_pipeline()
    if not all_articles:
        logger.error("No news found. Aborting pipeline.")
        return

    # 2. AI selects the top trending articles
    logger.info("Selecting top articles via AI...")
    top_articles = ai_service.select_top_trending(all_articles, count=10)
    logger.info(f"Selected {len(top_articles)} top articles.")

    # 3. Generate multi-platform posts based on configured channels
    unique_styles = list(set(ch["style"] for ch in config.BUFFER_CHANNELS.values()))
    logger.info(f"Generating posts for styles: {unique_styles}")
    posts_data = ai_service.generate_multi_platform_posts(top_articles, styles=unique_styles)

    # 4. Generate Visual News Card
    image_url = None
    if top_articles:
        logger.info("Generating visual news card...")
        visual_service = VisualService()
        top_headline = top_articles[0].get("title", "AI News Update")
        local_image_path = visual_service.generate_news_card(top_headline, brand_name=config.EMAIL_SENDER_NAME)
        
        if local_image_path:
            # Try to upload to ImgBB for a public URL (Preferred for Buffer)
            image_url = upload_to_imgbb(local_image_path)
            
            if image_url:
                logger.info(f"VisualService: Image successfully hosted on ImgBB: {image_url}")
            else:
                # Fallback to local public URL (Risk of Ngrok interstitial warnings)
                filename = os.path.basename(local_image_path)
                image_url = f"{config.BASE_PUBLIC_URL}/{config.MEDIA_DIR}/{filename}"
                logger.warning(f"VisualService: ImgBB upload failed. Falling back to local Ngrok URL: {image_url}")

    # 5. Generate newsletter content
    logger.info("Generating newsletter intro via AI...")
    intro_text = ai_service.generate_newsletter_intro(top_articles)

    # 5. Render newsletter HTML (generic copy — used for Slack upload + debug artifact)
    generic_html = HTMLRenderer.render_newsletter(intro_text, top_articles)
    with open("output_newsletter.html", "w", encoding="utf-8") as f:
        f.write(generic_html)
    logger.info("Newsletter saved to 'output_newsletter.html'.")

    if posts_data:
        image_urls = [image_url] if image_url else []
        logger.info(f"Final image URLs for Slack: {image_urls}")
        send_slack_notification(posts_data, image_urls=image_urls, newsletter_html=generic_html)
        logger.info("Multi-platform posts + visuals sent to Slack for approval.")
    else:
        logger.warning("Post generation failed — skipping Slack notification.")

    # 6. Email newsletter to subscribers
    _dispatch_newsletter(intro_text, top_articles)

    logger.info("Pipeline complete.")
    
    # Optional Local Cleanup (Ignored by Git)
    try:
        from utils.cleanup import cleanup_news_cache
        cleanup_news_cache()
    except (ImportError, ModuleNotFoundError):
        # This is expected if the file is ignored/missing in other environments
        pass


def _dispatch_newsletter(intro_text: str, articles: list) -> None:
    """Renders a personalised copy per subscriber and sends via the configured email driver."""
    from services.subscriber_store import get_all_active
    from services.email_service import EmailService

    subscribers = get_all_active()
    if not subscribers:
        logger.info("No active subscribers — skipping email dispatch.")
        return

    logger.info(f"Dispatching newsletter to {len(subscribers)} subscriber(s)...")

    # Build per-recipient payloads with personalised greeting + unsubscribe URL
    recipients = []
    for sub in subscribers:
        unsubscribe_url = f"{config.BASE_PUBLIC_URL}/unsubscribe?token={sub['unsubscribe_token']}"
        recipients.append({
            "email": sub["email"],
            "name": sub.get("name", ""),
            "unsubscribe_token": sub["unsubscribe_token"],
            "html_body": HTMLRenderer.render_newsletter(
                intro_text, articles,
                subscriber_name=sub.get("name", ""),
                unsubscribe_url=unsubscribe_url,
            ),
            "plain_body": HTMLRenderer.render_plaintext_newsletter(
                intro_text, articles,
                subscriber_name=sub.get("name", ""),
                unsubscribe_url=unsubscribe_url,
            ),
        })

    try:
        email_service = EmailService()
    except (ValueError, ImportError) as exc:
        logger.warning(f"Email dispatch skipped — driver not configured: {exc}")
        return

    result = email_service.send_newsletter(
        recipients=recipients,
        subject="🔥 Your AI News Digest",
        html_template="",   # per-recipient bodies are pre-rendered above
        plain_template="",
    )
    logger.info(f"Email dispatch — sent: {result['sent']}, failed: {result['failed']}")
    if result["errors"]:
        logger.warning(f"Failed recipients: {result['errors']}")


if __name__ == "__main__":
    run_pipeline()