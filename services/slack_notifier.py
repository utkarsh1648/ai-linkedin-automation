import json
import requests
from config import config
from utils.logger import get_logger

logger = get_logger(__name__)

def send_slack_notification(message: str) -> dict:
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {config.SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "channel": config.SLACK_CHANNEL_ID,
        "text": "AI Generated LinkedIn Post",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*AI Generated LinkedIn Post*\n\n{message}"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Approve"},
                        "style": "primary",
                        "value": json.dumps({"text": message, "image_urls": []}),
                        "action_id": "approve_post"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Reject"},
                        "style": "danger",
                        "value": json.dumps({"text": message, "image_urls": []}),
                        "action_id": "reject_post"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Edit"},
                        "value": json.dumps({"text": message, "image_urls": []}),
                        "action_id": "edit_post"
                    }
                ]
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        data = response.json()

        if not data.get("ok"):
            logger.error(f"Slack API Error: {data}")
            return {"error": data}

        return {
            "channel": data["channel"],
            "ts": data["ts"]
        }
    except Exception as e:
        logger.error(f"Failed to send slack notification: {e}")
        return {"error": str(e)}