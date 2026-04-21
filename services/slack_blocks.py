import json
from typing import List, Optional


def build_post_section(text: str) -> dict:
    """Returns a Slack mrkdwn section block for the given text."""
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def build_image_blocks(image_urls: List[str]) -> List[dict]:
    """Returns a list of Slack image blocks (max 3)."""
    return [
        {"type": "image", "image_url": url, "alt_text": "Post Image Preview"}
        for url in image_urls[:3]
        if url
    ]


def build_action_buttons(text: str, image_urls: Optional[List[str]] = None) -> dict:
    """Returns the Approve / Reject / Edit actions block with state encoded in button values."""
    value = json.dumps({"text": text, "image_urls": image_urls or []})
    return {
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Approve"},
                "style": "primary",
                "action_id": "approve_post",
                "value": value,
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


def build_post_message(
    text: str,
    image_urls: Optional[List[str]] = None,
    header: str = "",
) -> List[dict]:
    """
    Assembles a full Slack message block list:
      section (header + body) → optional image previews → action buttons
    """
    display_text = f"{header}\n\n{text}" if header else text
    blocks: List[dict] = [build_post_section(display_text)]
    if image_urls:
        blocks.extend(build_image_blocks(image_urls))
    blocks.append(build_action_buttons(text, image_urls))
    return blocks
