import datetime
from typing import Dict, List, Optional

from config import config
from utils.logger import get_logger
from services.slack_client import slack_client
from services.slack_blocks import build_multi_platform_message
from services.pending_posts import pending_post_service

logger = get_logger(__name__)


def send_slack_notification(posts_data: Dict[str, str], image_urls: Optional[List[str]] = None, newsletter_html: str = None) -> dict:
    """
    Posts AI-generated content for multiple platforms to the approval Slack channel.
    """
    # Store the post data locally to avoid Slack character limits
    post_id = pending_post_service.save_post(posts_data, image_urls or [])

    # Use the new multi-platform blocks
    blocks = build_multi_platform_message(
        posts_data=posts_data,
        channels=config.BUFFER_CHANNELS,
        post_id=post_id,
        image_urls=image_urls or [],
    )
    
    payload = {
        "channel": config.SLACK_CHANNEL_ID,
        "text": "🔥 New AI News Content - Approval Required",
        "blocks": blocks,
    }

    data = slack_client.post("chat.postMessage", payload)

    if not data.get("ok"):
        logger.error(f"Slack API Error: {data}")
        return {"error": data}

    result = {"channel": data["channel"], "ts": data["ts"]}

    # Upload the newsletter HTML as a file attachment when provided
    if newsletter_html:
        date_str = datetime.date.today().strftime("%Y-%m-%d")
        filename = f"newsletter_{date_str}.html"
        upload_res = slack_client.upload_file(
            channel_id=config.SLACK_CHANNEL_ID,
            content=newsletter_html,
            filename=filename,
            title=f"📰 Newsletter Preview — {date_str}",
            initial_comment="📎 *Newsletter for this post* — download and open in your browser to preview.",
        )
        if not upload_res.get("ok"):
            logger.warning(f"Newsletter file upload failed: {upload_res}")
        else:
            logger.info(f"Newsletter uploaded to Slack: {filename}")
        result["newsletter_upload"] = upload_res

    return result