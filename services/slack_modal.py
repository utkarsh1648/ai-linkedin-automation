import json
import requests
from config import config
from utils.logger import get_logger
from typing import List

logger = get_logger(__name__)

def get_edit_view(post_text: str, channel_id: str, ts: str, current_image_urls: List[str] = None):
    """Constructs the Slack Modal view JSON with multi-image support (up to 3)."""
    current_image_urls = current_image_urls or []
    
    # Ensure it's a list even if a single string was passed during migration
    if isinstance(current_image_urls, str):
        current_image_urls = [current_image_urls] if current_image_urls else []

    image_element = {
        "type": "plain_text_input",
        "action_id": "image_input",
        "placeholder": {
            "type": "plain_text",
            "text": "Paste a public image URL here (Priority)..."
        }
    }
    if current_image_urls and current_image_urls[0]:
        image_element["initial_value"] = current_image_urls[0]

    blocks = [
        {
            "type": "input",
            "block_id": "post_block",
            "element": {
                "type": "plain_text_input",
                "multiline": True,
                "initial_value": post_text,
                "action_id": "post_input"
            },
            "label": {
                "type": "plain_text",
                "text": "Edit your post"
            }
        },
        {
            "type": "input",
            "block_id": "image_block",
            "optional": True,
            "element": image_element,
            "label": {
                "type": "plain_text",
                "text": "Option A: Manual Image URL"
            }
        },
        {
            "type": "input",
            "block_id": "file_block",
            "optional": True,
            "element": {
                "type": "file_input",
                "action_id": "file_input",
                "filetypes": ["png", "jpg", "jpeg"],
                "max_files": 3 # REDUCED TO 3 AS REQUESTED
            },
            "label": {
                "type": "plain_text",
                "text": "Option B: Upload from System (Max 3) - TAKES PRIORITY"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": ":warning: *Note:* Please use only one option at a time. If you upload files, the manual URL field will be ignored."
            }
        }
    ]

    # Add the live preview block if images exist
    if current_image_urls:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Current Previews:*"}
        })
        for idx, url in enumerate(current_image_urls[:3]):
            if url:
                blocks.append({
                    "type": "image",
                    "image_url": url,
                    "alt_text": f"Image Preview {idx+1}"
                })

    return {
        "type": "modal",
        "callback_id": "edit_post_modal",
        "private_metadata": json.dumps({
            "channel_id": channel_id, 
            "ts": ts,
            "current_image_urls": current_image_urls
        }),
        "title": {
            "type": "plain_text",
            "text": "Edit LinkedIn Post"
        },
        "submit": {
            "type": "plain_text",
            "text": "Submit"
        },
        "blocks": blocks
    }

def open_edit_modal(trigger_id: str, post_text: str, channel_id: str, ts: str, initial_image_urls: List[str] = None, response_url: str = None):
    url = "https://slack.com/api/views.open"
    headers = {
        "Authorization": f"Bearer {config.SLACK_BOT_TOKEN}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    logger.info(f"Opening modal with token ending in ...{config.SLACK_BOT_TOKEN[-4:]}")

    view = get_edit_view(post_text, channel_id, ts, initial_image_urls)
    payload = {
        "trigger_id": trigger_id,
        "view": view
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        res_data = res.json()
        logger.info(f"Modal Open Response: {res_data}")
        if not res_data.get("ok"):
            error_code = res_data.get("error")
            logger.error(f"Slack API Error opening modal: {error_code} - {res_data.get('response_metadata')}")
            
            # Surface cold start issues or timeouts to the user
            if error_code == "expired_trigger_id" and response_url:
                try:
                    requests.post(response_url, json={
                        "response_type": "ephemeral",
                        "replace_original": False,
                        "text": "⏳ *The server was cold-starting!* Your action timed out. Please click the *Edit* button again."
                    }, timeout=5)
                except Exception as ping_ex:
                    logger.error(f"Failed to send ephemeral error message: {ping_ex}")

    except Exception as e:
        logger.error(f"Failed to open slack edit modal: {e}")

def update_edit_modal(view_id: str, post_text: str, channel_id: str, ts: str, image_urls: List[str]):
    url = "https://slack.com/api/views.update"
    headers = {
        "Authorization": f"Bearer {config.SLACK_BOT_TOKEN}",
        "Content-Type": "application/json; charset=utf-8"
    }

    view = get_edit_view(post_text, channel_id, ts, image_urls)
    payload = {
        "view_id": view_id,
        "view": view
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        res_data = res.json()
        logger.info(f"Modal Update Response: {res_data}")
        if not res_data.get("ok"):
            logger.error(f"Slack API Error updating modal: {res_data.get('error')} - {res_data.get('response_metadata')}")
    except Exception as e:
        logger.error(f"Failed to update slack edit modal: {e}")