import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import config
from utils.logger import get_logger
from pipeline.pipeline_orchestrator import main_pipeline
from services.ai_service import AIService
from services.newsletter_generator import HTMLRenderer
from services.slack_notifier import send_slack_notification
from api.slack_actions import router as slack_router
from api.subscribers import router as subscribers_router

logger = get_logger(__name__)

app = FastAPI(title="AI LinkedIn Automation")
app.include_router(slack_router)
app.include_router(subscribers_router)

# Mount local media directory to serve uploaded images publicly
os.makedirs(config.MEDIA_DIR, exist_ok=True)
app.mount(f"/{config.MEDIA_DIR}", StaticFiles(directory=config.MEDIA_DIR), name="media")


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

    # 3. Generate LinkedIn post and send to Slack for approval
    post = ai_service.generate_social_post(top_articles)
    if post:
        send_slack_notification(post)
        logger.info("Post sent to Slack for approval.")
    else:
        logger.warning("LinkedIn post generation failed — skipping Slack notification.")

    # 4. Generate newsletter content
    logger.info("Generating newsletter intro via AI...")
    intro_text = ai_service.generate_newsletter_intro(top_articles)

    # 5. Save a local copy (useful for debugging / GitHub Actions artefact)
    generic_html = HTMLRenderer.render_newsletter(intro_text, top_articles)
    with open("output_newsletter.html", "w", encoding="utf-8") as f:
        f.write(generic_html)
    logger.info("Newsletter saved to 'output_newsletter.html'.")

    # 6. Email newsletter to subscribers
    _dispatch_newsletter(intro_text, top_articles)

    logger.info("Pipeline complete.")


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

    email_service = EmailService()
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