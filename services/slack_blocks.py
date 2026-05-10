import json
from typing import List, Optional, Dict


def build_post_section(text: str) -> dict:
    """Returns a Slack mrkdwn section block for the given text."""
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def build_image_blocks(image_urls: List[str]) -> List[dict]:
    """Returns a list of Slack image blocks (max 3)."""
    return [
        {
            "type": "image",
            "image_url": url,
            "alt_text": "Post Image Preview",
            "title": {"type": "plain_text", "text": "📸 Social Media Card Preview"}
        }
        for url in image_urls[:4]
        if url
    ]


def build_channel_checkboxes(channels: Dict[str, dict]) -> dict:
    """Returns a checkbox block for selecting destination channels."""
    options = []
    for cid, info in channels.items():
        name = info.get("name", "Unknown Channel")
        icon = info.get("icon") or "🔗"
        
        options.append({
            "text": {
                "type": "plain_text",
                "text": f"{icon} {name}",
                "emoji": True
            },
            "value": cid
        })
    
    return {
        "type": "actions",
        "block_id": "channel_selection",
        "elements": [
            {
                "type": "checkboxes",
                "action_id": "select_channels",
                "initial_options": options,  # Pre-select all by default
                "options": options
            }
        ]
    }


def build_action_buttons(post_id: str) -> dict:
    """Returns the Approve / Reject / Edit actions block using a storage ID."""
    value = post_id
    
    return {
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Approve & Broadcast"},
                "style": "primary",
                "action_id": "approve_post",
                "value": value,
                "confirm": {
                    "title": {"type": "plain_text", "text": "Are you sure?"},
                    "text": {"type": "plain_text", "text": "This will post to all selected channels."},
                    "confirm": {"type": "plain_text", "text": "Broadcast"},
                    "deny": {"type": "plain_text", "text": "Cancel"}
                }
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Reject"},
                "style": "danger",
                "action_id": "reject_post",
                "value": value,
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Edit"},
                "action_id": "edit_post",
                "value": value,
            },
        ],
    }


def build_multi_platform_message(
    posts_data: Dict[str, str],
    channels: Dict[str, str],
    post_id: str,
    image_urls: Optional[List[str]] = None,
    show_images: bool = False,
) -> List[dict]:
    """
    Assembles a unified Slack message for multiple platforms.
    """
    blocks = []
    
    blocks.append(build_post_section("*🔥 AI News - Multi-Platform Preview*"))
    
    # Toggle button for image previews
    if image_urls:
        if show_images:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🙈 Hide Previews"},
                        "action_id": "toggle_images",
                        "value": f"{post_id}:hide"
                    }
                ]
            })
            blocks.extend(build_image_blocks(image_urls))
        else:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "👁️ Show Image Previews"},
                        "action_id": "toggle_images",
                        "value": f"{post_id}:show"
                    }
                ]
            })

    # Build a style -> (name, icon) map for pretty headers
    style_meta = {}
    for cid, info in channels.items():
        st = info.get("style")
        if st not in style_meta:
            style_meta[st] = {
                "name": info.get("name"),
                "icon": info.get("icon")
            }

    # Add sections for each style generated
    for style, text in posts_data.items():
        meta = style_meta.get(style, {})
        display_name = meta.get("name", style.capitalize())
        icon = meta.get("icon") or "✨"
        blocks.append(build_post_section(f"*{icon} {display_name}:*\n{text}"))

    # Checkboxes for platform selection
    blocks.append({
        "type": "divider"
    })
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": "*Select platforms to broadcast:*"}
    })
    blocks.append(build_channel_checkboxes(channels))
    
    # Broadcast/Action buttons
    blocks.append(build_action_buttons(post_id))
    
    return blocks
