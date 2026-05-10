import json
from typing import List, Optional

from config import config
from utils.logger import get_logger
from services.slack_client import slack_client

logger = get_logger(__name__)


def _build_modal_view(
    post_text: str, channel_id: str, ts: str, current_image_urls: Optional[List[str]] = None
) -> dict:
    """Constructs the Slack Modal view JSON with multi-image support (up to 3)."""
    current_image_urls = current_image_urls or []
    # Normalise: accept a bare string from older callers
    if isinstance(current_image_urls, str):
        current_image_urls = [current_image_urls] if current_image_urls else []

    image_element: dict = {
        "type": "plain_text_input",
        "action_id": "image_input",
        "placeholder": {"type": "plain_text", "text": "Paste a public image URL here (Priority)..."},
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
                "action_id": "post_input",
            },
            "label": {"type": "plain_text", "text": "Edit your post"},
        },
        {
            "type": "input",
            "block_id": "image_block",
            "optional": True,
            "element": image_element,
            "label": {"type": "plain_text", "text": "Option A: Manual Image URL"},
        },
        {
            "type": "input",
            "block_id": "file_block",
            "optional": True,
            "element": {
                "type": "file_input",
                "action_id": "file_input",
                "filetypes": ["png", "jpg", "jpeg"],
                "max_files": 3,
            },
            "label": {
                "type": "plain_text",
                "text": "Option B: Upload from System (Max 3) - TAKES PRIORITY",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": ":warning: *Note:* Use only one option. Uploaded files take priority over the URL field.",
            },
        },
    ]

    # Live previews for already-uploaded images
    if current_image_urls:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "*Current Previews:*"}})
        for idx, url in enumerate(current_image_urls[:3]):
            if url:
                blocks.append({"type": "image", "image_url": url, "alt_text": f"Image Preview {idx + 1}"})

    return {
        "type": "modal",
        "callback_id": "edit_post_modal",
        "private_metadata": json.dumps(
            {"channel_id": channel_id, "ts": ts, "current_image_urls": current_image_urls}
        ),
        "title": {"type": "plain_text", "text": "Edit LinkedIn Post"},
        "submit": {"type": "plain_text", "text": "Submit"},
        "blocks": blocks,
    }


def open_edit_modal(
    trigger_id: str,
    post_text: str,
    channel_id: str,
    ts: str,
    initial_image_urls: Optional[List[str]] = None,
    response_url: Optional[str] = None,
) -> None:
    """Opens the edit modal. If the trigger has expired, sends an ephemeral nudge via response_url."""
    import requests as _requests  # local import to avoid circular; only used for ephemeral fallback

    logger.info(f"Opening modal with token ending ...{config.SLACK_BOT_TOKEN[-4:]}")
    payload = {
        "trigger_id": trigger_id,
        "view": _build_modal_view(post_text, channel_id, ts, initial_image_urls),
    }
    res_data = slack_client.post("views.open", payload)
    logger.info(f"Modal Open Response: {res_data}")

    if not res_data.get("ok"):
        error_code = res_data.get("error")
        logger.error(f"Slack API Error opening modal: {error_code} — {res_data.get('response_metadata')}")

        # Notify user when the server was cold-starting and the trigger expired
        if error_code == "expired_trigger_id" and response_url:
            try:
                _requests.post(
                    response_url,
                    json={
                        "response_type": "ephemeral",
                        "replace_original": False,
                        "text": "⏳ *The server was cold-starting!* Your action timed out. Please click *Edit* again.",
                    },
                    timeout=5,
                )
            except Exception as e:
                logger.error(f"Failed to send ephemeral cold-start notice: {e}")


def update_edit_modal(
    view_id: str, post_text: str, channel_id: str, ts: str, image_urls: List[str]
) -> None:
    """Refreshes an open modal with updated image previews after a file is selected."""
    payload = {
        "view_id": view_id,
        "view": _build_modal_view(post_text, channel_id, ts, image_urls),
    }
    res_data = slack_client.post("views.update", payload)
    logger.info(f"Modal Update Response: {res_data}")

    if not res_data.get("ok"):
        logger.error(
            f"Slack API Error updating modal: {res_data.get('error')} — {res_data.get('response_metadata')}"
        )