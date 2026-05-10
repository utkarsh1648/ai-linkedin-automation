import json
from typing import List, Optional

from config import config
from utils.logger import get_logger
from services.slack_client import slack_client

logger = get_logger(__name__)


def _build_loading_view(channel_id: str, ts: str, metadata: str) -> dict:
    """A lightweight view to open instantly and beat the 3s timeout."""
    return {
        "type": "modal",
        "title": {"type": "plain_text", "text": "Loading..."},
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "⏳ *Fetching your posts...* One moment please."}
            }
        ],
        "private_metadata": metadata
    }

def _build_modal_view(
    posts: dict, channel_id: str, ts: str, current_image_urls: Optional[List[str]] = None, metadata: Optional[str] = None
) -> dict:
    """Constructs the Slack Modal view JSON with inputs for ALL post styles."""
    current_image_urls = current_image_urls or []
    if isinstance(current_image_urls, str):
        current_image_urls = [current_image_urls] if current_image_urls else []

    blocks = []
    
    # Map styles to their custom names and icons from config
    style_meta = {}
    for cid, info in config.BUFFER_CHANNELS.items():
        st = info.get("style")
        if st not in style_meta:
            style_meta[st] = {
                "name": info.get("name"),
                "icon": info.get("icon")
            }

    # Dynamically add an input for each style using its custom name and icon
    for style, text in posts.items():
        meta = style_meta.get(style, {})
        display_name = meta.get("name", style.capitalize())
        icon = meta.get("icon") or "✏️"
        blocks.append({
            "type": "input",
            "block_id": f"block_{style}",
            "element": {
                "type": "plain_text_input",
                "multiline": True,
                "initial_value": text,
                "action_id": f"input_{style}",
            },
            "label": {"type": "plain_text", "text": f"{icon} Edit {display_name}", "emoji": True},
        })

    # Image inputs
    image_element: dict = {
        "type": "plain_text_input",
        "action_id": "image_input",
        "placeholder": {"type": "plain_text", "text": "Paste a public image URL here (Priority)..."},
    }
    if current_image_urls and current_image_urls[0]:
        image_element["initial_value"] = current_image_urls[0]

    blocks.append({
        "type": "input",
        "block_id": "image_block",
        "optional": True,
        "element": image_element,
        "label": {"type": "plain_text", "text": "Option A: Manual Image URL"},
    })

    # Option B: File Upload (Only show if we have room)
    remaining_slots = 4 - len(current_image_urls)
    
    if remaining_slots > 0:
        blocks.append({
            "type": "input",
            "block_id": "file_block",
            "optional": True,
            "element": {
                "type": "file_input",
                "action_id": "file_input",
                "filetypes": ["png", "jpg", "jpeg"],
                "max_files": remaining_slots,
            },
            "label": {"type": "plain_text", "text": f"Option B: Upload from System (Max {remaining_slots} more)", "emoji": True},
        })
        blocks.append({
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"ℹ️ *Note:* You have {remaining_slots} slots remaining for images."}
            ]
        })
    else:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "🚫 *Image limit reached (4/4).* Delete the URL in Option A to make room for new uploads."}
        })

    # NEW: Smart Image Guidance
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": "✨ *Smart Images:* You can upload images of any size. For *Instagram*, non-square images will be automatically \"squared\" with white padding to ensure a successful post!"}
        ]
    })

    # Live previews with DIRECT REMOVE buttons
    if current_image_urls:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "*Current Previews (Click 🗑️ to remove instantly):*"}})
        
        # Show up to 4 previews
        for idx, url in enumerate(current_image_urls[:4]):
            if url:
                # Option A is already manageable via its text input box.
                if url != image_element.get("initial_value"):
                    # Slack crashes if it can't download the image (common with Ngrok/local URLs)
                    if config.BASE_PUBLIC_URL in url:
                        blocks.append({
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": f"🖼️ *Local Image:* <{url}|View Image>\n_(Preview hidden to prevent Slack errors)_"},
                            "accessory": {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "🗑️"},
                                "action_id": "remove_image_direct",
                                "value": url,
                                "confirm": {
                                    "title": {"type": "plain_text", "text": "Remove Image?"},
                                    "text": {"type": "plain_text", "text": "Are you sure you want to remove this uploaded image?"},
                                    "confirm": {"type": "plain_text", "text": "Remove"},
                                    "deny": {"type": "plain_text", "text": "Cancel"}
                                }
                            }
                        })
                    else:
                        blocks.append({
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": f"*Image #{idx + 1}*"},
                            "accessory": {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "🗑️"},
                                "action_id": "remove_image_direct",
                                "value": url,
                                "confirm": {
                                    "title": {"type": "plain_text", "text": "Remove Image?"},
                                    "text": {"type": "plain_text", "text": "Are you sure you want to remove this uploaded image?"},
                                    "confirm": {"type": "plain_text", "text": "Remove"},
                                    "deny": {"type": "plain_text", "text": "Cancel"}
                                }
                            }
                        })
                        blocks.append({
                            "type": "image",
                            "image_url": url,
                            "alt_text": f"Preview {idx + 1}"
                        })
                else:
                    blocks.append({
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"*Image #{idx + 1} (Option A URL)*"}
                    })
                

    return {
        "type": "modal",
        "callback_id": "edit_post_modal",
        "private_metadata": metadata if metadata else json.dumps(
            {"channel_id": channel_id, "ts": ts, "current_image_urls": current_image_urls}
        ),
        "title": {"type": "plain_text", "text": "Edit Multi-Platform Post"},
        "submit": {"type": "plain_text", "text": "Submit"},
        "blocks": blocks,
    }


def open_edit_modal(
    trigger_id: str,
    channel_id: str,
    ts: str,
    metadata: Optional[str] = None,
) -> Optional[str]:
    """Opens a fast loading modal and returns its view_id."""
    payload = {
        "trigger_id": trigger_id,
        "view": _build_loading_view(channel_id, ts, metadata or ""),
    }
    res_data = slack_client.post("views.open", payload)
    
    if not res_data.get("ok"):
        logger.error(f"Slack API Error opening loading modal: {res_data.get('error')}")
        return None
        
    return res_data["view"]["id"]


def update_edit_modal(
    view_id: str, posts: dict, channel_id: str, ts: str, image_urls: List[str]
) -> None:
    """Refreshes an open modal with updated image previews and all post styles."""
    payload = {
        "view_id": view_id,
        "view": _build_modal_view(posts, channel_id, ts, image_urls),
    }
    res_data = slack_client.post("views.update", payload)
    logger.info(f"Modal Update Response: {res_data}")

    if not res_data.get("ok"):
        logger.error(
            f"Slack API Error updating modal: {res_data.get('error')} — {res_data.get('response_metadata')}"
        )