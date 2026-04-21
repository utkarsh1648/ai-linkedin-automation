import json
import requests
from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import PlainTextResponse, JSONResponse
from urllib.parse import parse_qs

from config import config
from utils.logger import get_logger
from services.buffer_poster import post_to_linkedin
from services.slack_modal import open_edit_modal, update_edit_modal
from services.slack_blocks import build_post_message, build_post_section
from services.slack_client import slack_client
from utils.file_handler import download_slack_file, delete_local_file

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Background task helpers
# ---------------------------------------------------------------------------

def _task_post_to_linkedin(text: str, image_urls: list = None) -> None:
    """Posts to LinkedIn and cleans up any locally-hosted images afterwards."""
    try:
        post_to_linkedin(text, image_urls)
        logger.info(f"Posted to LinkedIn {'with images' if image_urls else ''}")
    except Exception as e:
        logger.error(f"Failed to post to LinkedIn: {e}")
    finally:
        # Remove locally-served files that are no longer needed
        if image_urls:
            for url in image_urls:
                if config.BASE_PUBLIC_URL in url:
                    delete_local_file(url)


def _task_update_via_response_url(response_url: str, updated_text: str) -> None:
    """Hits Slack's response_url in the background to replace the original message text."""
    try:
        requests.post(
            response_url,
            json={
                "replace_original": True,
                "text": updated_text,
                "blocks": [build_post_section(updated_text)],
            },
            timeout=5,
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to update via response_url: {e}")


def _task_handle_modal_submission(
    channel_id: str, ts: str, text: str, manual_url: str, file_urls: list = None, base_url: str = None
) -> None:
    """
    Processes a modal submission in the background.
    Priority: uploaded files > manual URL > no image.
    """
    image_urls = []

    if file_urls:
        logger.info(f"Processing {len(file_urls)} uploaded file(s) (Priority 1)")
        for furl in file_urls[:3]:
            public_url = download_slack_file(furl, config.SLACK_BOT_TOKEN, base_url)
            if public_url:
                image_urls.append(public_url)
    elif manual_url:
        logger.info(f"Using manual URL (Priority 2): {manual_url}")
        image_urls = [manual_url]

    _update_slack_message(channel_id, ts, text, image_urls)


def _task_handle_modal_preview(
    view_id: str, channel_id: str, ts: str, text: str, file_urls: list, base_url: str = None
) -> None:
    """Downloads selected files and refreshes the modal with image previews."""
    public_urls = []
    for file_url in file_urls[:3]:
        url = download_slack_file(file_url, config.SLACK_BOT_TOKEN, base_url)
        if url:
            public_urls.append(url)
    if public_urls:
        update_edit_modal(view_id, text, channel_id, ts, public_urls)


def _update_slack_message(channel_id: str, ts: str, new_text: str, image_urls: list = None) -> None:
    """Updates an existing Slack message with edited content and action buttons."""
    blocks = build_post_message(
        text=new_text,
        image_urls=image_urls,
        header="*📝 Edited LinkedIn Post (pending approval):*",
    )
    payload = {"channel": channel_id, "ts": ts, "text": new_text, "blocks": blocks}
    res = slack_client.post("chat.update", payload)
    logger.info(f"Slack Message Update Response: {res}")


# ---------------------------------------------------------------------------
# Route handler
# ---------------------------------------------------------------------------

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

        # --- Modal submission ---
        if payload["type"] == "view_submission":
            state_values = payload["view"]["state"]["values"]
            edited_text = state_values["post_block"]["post_input"]["value"]
            manual_image_url = state_values.get("image_block", {}).get("image_input", {}).get("value")
            files = state_values.get("file_block", {}).get("file_input", {}).get("files", [])
            file_urls = [f.get("url_private_download") for f in files if f.get("url_private_download")]

            private_metadata = json.loads(payload["view"]["private_metadata"])
            channel_id = private_metadata["channel_id"]
            ts = private_metadata["ts"]
            base_url = str(request.base_url).rstrip("/")

            logger.info("Modal submitted — offloading to background task")
            background_tasks.add_task(
                _task_handle_modal_submission, channel_id, ts, edited_text, manual_image_url, file_urls, base_url
            )
            return JSONResponse(content={"response_action": "clear"})

        # --- Interactive button actions ---
        if payload["type"] == "block_actions":
            action_data = payload["actions"][0]
            action_id = action_data["action_id"]
            user_info = payload.get("user", {})
            user = user_info.get("username") or user_info.get("name", "Unknown")

            # File selected inside the modal — refresh previews
            if action_id == "file_input":
                files = action_data.get("files", [])
                if files:
                    file_urls = [f.get("url_private_download") for f in files if f.get("url_private_download")]
                    state_values = payload["view"]["state"]["values"]
                    post_text = state_values.get("post_block", {}).get("post_input", {}).get("value", "")
                    private_metadata = json.loads(payload["view"]["private_metadata"])
                    base_url = str(request.base_url).rstrip("/")
                    background_tasks.add_task(
                        _task_handle_modal_preview,
                        payload["view"]["id"],
                        private_metadata["channel_id"],
                        private_metadata["ts"],
                        post_text,
                        file_urls,
                        base_url,
                    )
                return PlainTextResponse("OK")

            value_data = json.loads(action_data["value"])
            post_text = value_data["text"]
            current_image_urls = value_data.get("image_urls") or []

            if action_id == "edit_post":
                trigger_id = payload.get("trigger_id")
                channel_id = payload.get("channel", {}).get("id")
                ts = payload.get("message", {}).get("ts")
                logger.info(f"Edit clicked by {user} — trigger={trigger_id}, ts={ts}")
                if not trigger_id:
                    logger.error("No trigger_id in payload — message may be stale")
                background_tasks.add_task(
                    open_edit_modal, trigger_id, post_text, channel_id, ts, current_image_urls,
                    payload.get("response_url"),
                )
                return PlainTextResponse("OK")

            if action_id == "approve_post":
                logger.info(f"Post approved by {user}")
                background_tasks.add_task(_task_post_to_linkedin, post_text, current_image_urls)
                updated_text = f"✅ *Approved by {user}*\n🚀 Posted to LinkedIn {'(with images)' if current_image_urls else ''}"

            elif action_id == "reject_post":
                logger.info(f"Post rejected by {user}")
                updated_text = f"❌ *Rejected by {user}*"
                for url in current_image_urls:
                    if config.BASE_PUBLIC_URL in url:
                        background_tasks.add_task(delete_local_file, url)

            else:
                logger.warning(f"Unknown action_id: {action_id}")
                return PlainTextResponse("Unknown action")

            background_tasks.add_task(_task_update_via_response_url, payload["response_url"], updated_text)
            return PlainTextResponse("OK")

    except Exception as e:
        logger.error(f"Error in slack_actions: {e}", exc_info=True)
        return PlainTextResponse("Internal Error", status_code=500)

    return PlainTextResponse("OK")