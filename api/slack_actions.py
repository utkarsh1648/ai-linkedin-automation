import json
import requests
from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import PlainTextResponse, JSONResponse                                         
from urllib.parse import parse_qs                                           

from config import config
from utils.logger import get_logger
from services.buffer_poster import post_to_linkedin
from services.slack_modal import open_edit_modal, update_edit_modal
from utils.file_handler import download_slack_file, delete_local_file

logger = get_logger(__name__)

router = APIRouter()

# 🔹 Background tasks for long-running operations
def task_post_to_linkedin(text: str, image_urls: list = None):
    try:
        post_to_linkedin(text, image_urls)
        logger.info(f"Successfully posted to LinkedIn {'with images' if image_urls else ''}")
        
        # Cleanup local media files
        if image_urls:
            for url in image_urls:
                if config.BASE_PUBLIC_URL in url:
                    delete_local_file(url)
            
    except Exception as e:
        logger.error(f"Failed to post to LinkedIn: {e}")

def task_update_via_response_url(response_url: str, updated_text: str):
    """Hits Slack's webhook response_url in the background to update the message visually."""
    try:
        requests.post(response_url, json={
            "replace_original": True,
            "text": updated_text,
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": updated_text
                    }
                }
            ]
        }, timeout=5)
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to update via response url: {e}")

def task_handle_modal_submission(channel_id: str, ts: str, text: str, manual_url: str, file_urls: list = None):
    """Processes modal submission in background: prioritizes file uploads, then manual URL."""
    image_urls = []
    
    if file_urls:
        logger.info(f"Processing {len(file_urls)} file uploads (Priority 1)...")
        for furl in file_urls[:3]: # Limit to 3 as requested
            public_url = download_slack_file(furl, config.SLACK_BOT_TOKEN)
            if public_url:
                image_urls.append(public_url)
    elif manual_url:
        logger.info(f"Using manual URL (Priority 2): {manual_url}")
        image_urls = [manual_url]
            
    update_slack_message(channel_id, ts, text, image_urls)

def task_handle_modal_preview(view_id: str, channel_id: str, ts: str, text: str, file_url: str):
    """Processes instant modal preview: downloads file and refreshes the modal view."""
    public_url = download_slack_file(file_url, config.SLACK_BOT_TOKEN)
    if public_url:
        update_edit_modal(view_id, text, channel_id, ts, public_url)

def update_slack_message(channel_id: str, ts: str, new_text: str, image_urls: list = None):
    """Update an existing Slack message with new content."""
    url = "https://slack.com/api/chat.update"
    headers = {
        "Authorization": f"Bearer {config.SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*📝 Edited LinkedIn Post (pending approval):*\n\n{new_text}"
            }
        }
    ]

    # Add image preview blocks
    if image_urls:
        for img_url in image_urls[:3]:
            blocks.append({
                "type": "image",
                "image_url": img_url,
                "alt_text": "Post Image Preview"
            })

    # Add action buttons with state in 'value'
    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Approve"},
                "style": "primary",
                "action_id": "approve_post",
                "value": json.dumps({"text": new_text, "image_urls": image_urls})
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Reject"},
                "style": "danger",
                "action_id": "reject_post",
                "value": json.dumps({"text": new_text, "image_urls": image_urls})
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Edit"},
                "action_id": "edit_post",
                "value": json.dumps({"text": new_text, "image_urls": image_urls})
            }
        ]
    })

    payload = {
        "channel": channel_id,
        "ts": ts,
        "text": new_text,
        "blocks": blocks
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        logger.info(f"Slack Message Update Response: {res.json()}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to update slack message: {e}")

@router.post("/slack/actions")
async def slack_actions(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    try:
        body_str = body.decode()
        parsed = parse_qs(body_str)

        if "payload" not in parsed:
            logger.warning(f"No payload in request. Body: {body_str}")
            return PlainTextResponse("Invalid payload", status_code=400)

        payload = json.loads(parsed["payload"][0])
        logger.info(f"Slack Action Type: {payload.get('type')}")

        # 1️⃣ HANDLE MODAL SUBMISSION
        if payload["type"] == "view_submission":
            state_values = payload["view"]["state"]["values"]
            edited_text = state_values["post_block"]["post_input"]["value"]
            
            # Get manual URL if provided
            manual_image_url = state_values.get("image_block", {}).get("image_input", {}).get("value")
            
            # Check for file upload (get URLs now, download in background)
            file_urls_to_download = []
            files = state_values.get("file_block", {}).get("file_input", {}).get("files", [])
            if files:
                file_urls_to_download = [f.get("url_private") for f in files if f.get("url_private")]

            private_metadata = json.loads(payload["view"]["private_metadata"])
            channel_id = private_metadata["channel_id"]
            ts = private_metadata["ts"]

            logger.info(f"Modal Submitted. Offloading processing to background task...")
            
            # Offload EVERYTHING (download + update) to background task to respond to Slack (<3s)
            background_tasks.add_task(
                task_handle_modal_submission, 
                channel_id, ts, edited_text, manual_image_url, file_urls_to_download
            )

            return JSONResponse(content={"response_action": "clear"})

        # 2️⃣ HANDLE INTERACTIVE ACTIONS (Buttons)
        if payload["type"] == "block_actions":
            action_data = payload["actions"][0]
            action_id = action_data["action_id"]
            user = payload["user"]["username"]
            
            # 🔹 HANDLE INSTANT MODAL PREVIEW (When file is selected)
            if action_id == "file_input":
                view_id = payload["view"]["id"]
                files = action_data.get("files", [])
                if files:
                    file_url = files[0].get("url_private")
                    
                    # Extract current text to preserve it
                    state_values = payload["view"]["state"]["values"]
                    post_text = state_values.get("post_block", {}).get("post_input", {}).get("value", "")
                    
                    private_metadata = json.loads(payload["view"]["private_metadata"])
                    channel_id = private_metadata["channel_id"]
                    ts = private_metadata["ts"]
                    
                    logger.info(f"File selected in modal. Offloading preview to background...")
                    background_tasks.add_task(task_handle_modal_preview, view_id, channel_id, ts, post_text, file_url)
                return PlainTextResponse("OK")

            value_data = json.loads(action_data["value"])
            post_text = value_data["text"]
            current_image_urls = value_data.get("image_urls", [])
            
            # Migration check: if old data has 'image_url' (singular), convert to list
            if "image_url" in value_data and not current_image_urls:
                old_url = value_data.get("image_url")
                current_image_urls = [old_url] if old_url else []

            if action_id == "edit_post":
                trigger_id = payload.get("trigger_id")
                channel_id = payload.get("channel", {}).get("id")
                ts = payload.get("message", {}).get("ts")
                
                logger.info(f"Edit button clicked. TriggerID: {trigger_id}, MessageTS: {ts}")
                
                # Offload to background task to ensure 200 OK reaches Slack in <3s
                background_tasks.add_task(open_edit_modal, trigger_id, post_text, channel_id, ts, current_image_urls)
                return PlainTextResponse("OK")

            if action_id == "approve_post":
                logger.info(f"Post Approved by {user}")
                background_tasks.add_task(task_post_to_linkedin, post_text, current_image_urls)
                updated_text = f"✅ *Approved by {user}*\n🚀 Posted to LinkedIn {'(with images)' if current_image_urls else ''}"
            
            elif action_id == "reject_post":
                logger.info(f"Post Rejected by {user}")
                updated_text = f"❌ *Rejected by {user}*"
                
                # Cleanup local media files if post is rejected
                if current_image_urls:
                    for url in current_image_urls:
                        if config.BASE_PUBLIC_URL in url:
                            background_tasks.add_task(delete_local_file, url)
            
            else:
                logger.warning(f"Unknown action_id: {action_id}")
                return PlainTextResponse("Unknown action")

            response_url = payload["response_url"]
            
            # Since the message was originally sent via chat.postMessage, we MUST use response_url
            # to update it, and we do it in the background to guarantee a 0ms HTTP 200 OK return.
            background_tasks.add_task(task_update_via_response_url, response_url, updated_text)

            return PlainTextResponse("OK")

    except Exception as e:
        logger.error(f"Error in slack_actions: {e}", exc_info=True)
        return PlainTextResponse("Internal Error", status_code=500)

    return PlainTextResponse("OK")