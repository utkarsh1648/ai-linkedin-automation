from config import config
from utils.logger import get_logger
from services.slack_client import slack_client
from services.slack_blocks import build_post_message

logger = get_logger(__name__)


def send_slack_notification(message: str) -> dict:
    """Posts an AI-generated LinkedIn post to the approval Slack channel."""
    blocks = build_post_message(
        text=message,
        image_urls=[],
        header="*AI Generated LinkedIn Post*",
    )
    payload = {
        "channel": config.SLACK_CHANNEL_ID,
        "text": "AI Generated LinkedIn Post",
        "blocks": blocks,
    }

    data = slack_client.post("chat.postMessage", payload)

    if not data.get("ok"):
        logger.error(f"Slack API Error: {data}")
        return {"error": data}

    return {"channel": data["channel"], "ts": data["ts"]}