import json
import requests
from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import PlainTextResponse, JSONResponse
from urllib.parse import parse_qs

from config import config
from utils.logger import get_logger
from services.buffer_poster import broadcast_to_buffer
from services.slack_modal import open_edit_modal, update_edit_modal
from services.slack_blocks import build_multi_platform_message, build_post_section
from services.slack_client import slack_client
from services.pending_posts import pending_post_service
from utils.file_handler import download_slack_file, delete_local_file

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Background task helpers
# ---------------------------------------------------------------------------

def _task_broadcast_to_buffer(posts: dict, selected_channels: dict, image_urls: list = None) -> None:
    """Broadcasts to all selected Buffer channels and cleans up images."""
    try:
        broadcast_to_buffer(posts, selected_channels, image_urls)
        logger.info(f"Broadcast complete to {len(selected_channels)} channels.")
    except Exception as e:
        logger.error(f"Failed to broadcast to Buffer: {e}")
    finally:
        if image_urls:
            for url in image_urls:
                if config.BASE_PUBLIC_URL in url:
                    delete_local_file(url)
        
        # Optional Local Cleanup (Ignored by Git)
        try:
            from utils.cleanup import cleanup_pending_posts, cleanup_media_folder
            cleanup_pending_posts()
            cleanup_media_folder()
        except (ImportError, ModuleNotFoundError):
            # This is expected if the file is ignored/missing in other environments
            pass


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


async def _task_open_edit_modal(view_id: str, post_id: str, channel_id: str, ts: str, response_url: str) -> None:
    """Fetches data and replaces the loading modal with the real editor."""
    stored_data = pending_post_service.get_post(post_id)
    if not stored_data:
        logger.warning(f"Async Task: No stored data found for post_id: {post_id}")
        return
    
    posts = stored_data["posts"]
    image_urls = stored_data.get("image_urls", [])
    
    # We use update_edit_modal instead of open_edit_modal here
    update_edit_modal(
        view_id,
        posts,
        channel_id,
        ts,
        image_urls
    )


def _task_handle_modal_submission(
    channel_id: str, ts: str, posts: dict, manual_url: str, file_urls: list = None, 
    base_url: str = None, current_image_urls: list = None, post_id: str = None,
    removed_urls: list = None # NEW
) -> None:
    """Processes a modal submission."""
    # 0. Immediate Loader for UX
    slack_client.post("chat.update", {
        "channel": channel_id,
        "ts": ts,
        "text": "⏳ Processing changes...",
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "⏳ *Processing your changes and optimizing images...*\nThis will take a moment while we handle cloud uploads."}
            }
        ]
    })

    # Start with the images we already had
    final_images = current_image_urls or []
    
    # FILTER OUT any that were marked for removal
    if removed_urls:
        final_images = [img for img in final_images if img not in removed_urls]
    
    # If the user changed the Manual URL, update the first slot (usually the AI image)
    # But for simplicity, we'll just handle new uploads here.
    
    from services.visual_service import VisualService
    import os
    visual_service = VisualService()

    if file_urls:
        for furl in file_urls:
            public_url = download_slack_file(furl, config.SLACK_BOT_TOKEN, base_url)
            if public_url:
                if public_url not in final_images:
                    final_images.append(public_url)
    
    # Also handle the manual_url if it's not already in the list
    if manual_url and manual_url not in final_images:
        final_images.insert(0, manual_url)
    
    # Deduplicate and Cap at 4
    seen = set()
    final_images = [x for x in final_images if not (x in seen or seen.add(x))]
    final_images = final_images[:4]

    # Save the updated image list back to storage
    if post_id:
        stored_data = pending_post_service.get_post(post_id)
        if stored_data:
            stored_data["image_urls"] = final_images
            pending_post_service.update_post(post_id, stored_data)

    _update_slack_message(channel_id, ts, posts, final_images)


def _update_slack_message(channel_id: str, ts: str, posts: dict, image_urls: list = None) -> None:
    """Updates the Slack message with new content."""
    # Store updated data and get a new ID
    post_id = pending_post_service.save_post(posts, image_urls or [])
    
    blocks = build_multi_platform_message(
        posts_data=posts,
        channels=config.BUFFER_CHANNELS,
        post_id=post_id,
        image_urls=image_urls,
    )
    payload = {"channel": channel_id, "ts": ts, "text": "Post Updated", "blocks": blocks}
    slack_client.post("chat.update", payload)


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
            return PlainTextResponse("Invalid payload", status_code=400)

        payload = json.loads(parsed["payload"][0])
        
        # --- Modal submission ---
        if payload["type"] == "view_submission":
            state_values = payload["view"]["state"]["values"]
            private_metadata = json.loads(payload["view"]["private_metadata"])
            
            post_id = private_metadata.get("post_id")
            # Fetch the original posts from storage instead of metadata
            stored_data = pending_post_service.get_post(post_id)
            posts = stored_data.get("posts", {}) if stored_data else {}

            # Extract all edited styles from their respective blocks
            for block_id, values in state_values.items():
                if block_id.startswith("block_"):
                    style = block_id.replace("block_", "")
                    input_id = f"input_{style}"
                    if input_id in values:
                        posts[style] = values[input_id]["value"]
            
            # Extract uploaded files
            files_data = state_values.get("file_block", {}).get("file_input", {}).get("files", [])
            file_urls = [f["url_private"] for f in files_data if "url_private" in f]
            
            # Extract removed images
            removed_options = state_values.get("remove_images_block", {}).get("remove_images_action", {}).get("selected_options", [])
            removed_urls = [opt["value"] for opt in removed_options]
            
            background_tasks.add_task(
                _task_handle_modal_submission, 
                private_metadata["channel_id"], 
                private_metadata["ts"], 
                posts, 
                state_values.get("image_block", {}).get("image_input", {}).get("value"),
                file_urls,
                str(request.base_url).rstrip("/"),
                current_image_urls=private_metadata.get("current_image_urls", []),
                removed_urls=removed_urls, # NEW
                post_id=post_id
            )
            return JSONResponse(content={"response_action": "clear"})

        # --- Interactive button actions ---
        if payload["type"] == "block_actions":
            action_data = payload["actions"][0]
            action_id = action_data["action_id"]
            user = payload.get("user", {}).get("name", "Unknown")
            
            # The value is now the pending post ID (except for remove_image_direct)
            post_id = action_data.get("value")
            stored_data = None
            
            if action_id not in ["remove_image_direct", "select_channels"]:
                stored_data = pending_post_service.get_post(post_id)
                if not stored_data:
                    logger.warning(f"No stored data found for post_id: {post_id}")
                    if action_id in ["approve_post", "reject_post", "edit_post"]:
                        return PlainTextResponse("Error: Session expired. Please run the pipeline again.")

            # Handle Toggle Images
            if action_id == "toggle_images":
                parts = action_data["value"].split(":")
                post_id = parts[0]
                mode = parts[1] # "show" or "hide"
                
                stored_data = pending_post_service.get_post(post_id)
                if stored_data:
                    blocks = build_multi_platform_message(
                        posts_data=stored_data["posts"],
                        channels=config.BUFFER_CHANNELS,
                        post_id=post_id,
                        image_urls=stored_data.get("image_urls"),
                        show_images=(mode == "show")
                    )
                    slack_client.post("chat.update", {
                        "channel": payload["channel"]["id"],
                        "ts": payload["message"]["ts"],
                        "text": "Preview Toggled",
                        "blocks": blocks
                    })
                return PlainTextResponse("OK")

            # Handle Approve
            if action_id == "approve_post":
                posts = stored_data["posts"]
                image_urls = stored_data.get("image_urls") or []
                
                state = payload.get("state", {}).get("values", {})
                selected_options = state.get("channel_selection", {}).get("select_channels", {}).get("selected_options", [])
                
                if not selected_options:
                    return PlainTextResponse("Please select at least one channel.")

                # Map selected IDs to styles
                all_channels = config.BUFFER_CHANNELS
                selected_map = {}
                for opt in selected_options:
                    cid = opt["value"]
                    channel_info = all_channels.get(cid, {})
                    selected_map[cid] = channel_info.get("style", "professional")
                
                logger.info(f"Post approved by {user} for {len(selected_map)} channels")
                background_tasks.add_task(_task_broadcast_to_buffer, posts, selected_map, image_urls)
                
                # Professional confirmation message
                channel_names = [all_channels.get(opt["value"], {}).get("name", "Unknown") for opt in selected_options]
                channel_list_str = "\n".join([f"• {name}" for name in channel_names])
                updated_text = (
                    f"✅ *Content Approved & Queued*\n"
                    f"────────────────────────\n"
                    f"👤 *Approver:* {user}\n"
                    f"📡 *Distribution:*\n{channel_list_str}\n"
                    f"────────────────────────\n"
                    f"🚀 _Content successfully queued for publication._"
                )
                background_tasks.add_task(_task_update_via_response_url, payload["response_url"], updated_text)
                
                # Cleanup
                pending_post_service.delete_post(post_id)
                return PlainTextResponse("OK")

            # Handle Reject
            elif action_id == "reject_post":
                image_urls = stored_data.get("image_urls") or []
                # Professional rejection message
                updated_text = (
                    f"❌ *Post Discarded*\n"
                    f"────────────────────────\n"
                    f"👤 *Rejected by:* {user}\n"
                    f"────────────────────────\n"
                    f"⚠️ _This content will not be broadcasted._"
                )
                for url in image_urls:
                    if config.BASE_PUBLIC_URL in url:
                        background_tasks.add_task(delete_local_file, url)
                background_tasks.add_task(_task_update_via_response_url, payload["response_url"], updated_text)
                
                pending_post_service.delete_post(post_id)
                
                # Final Local Cleanup (Ignored by Git)
                try:
                    from utils.cleanup import cleanup_pending_posts, cleanup_media_folder
                    cleanup_pending_posts()
                    cleanup_media_folder()
                except (ImportError, ModuleNotFoundError):
                    pass

                return PlainTextResponse("OK")

            # Handle Direct Image Removal (Instant)
            elif action_id == "remove_image_direct":
                url_to_remove = action_data.get("value") # Corrected variable name
                view_id = payload.get("view", {}).get("id")
                state_values = payload.get("view", {}).get("state", {}).get("values", {})
                private_metadata = json.loads(payload.get("view", {}).get("private_metadata", "{}"))
                
                channel_id = private_metadata.get("channel_id")
                ts = private_metadata.get("ts")
                current_image_urls = private_metadata.get("current_image_urls", [])
                
                # 1. Remove the image from the list
                new_image_urls = [url for url in current_image_urls if url != url_to_remove]
                
                # 2. ALSO preserve any text edits
                current_posts = {}
                for block_id, values in state_values.items():
                    if block_id.startswith("block_"):
                        style = block_id.replace("block_", "")
                        input_id = f"input_{style}"
                        if input_id in values:
                            current_posts[style] = values[input_id]["value"]
                
                update_edit_modal(view_id, current_posts, channel_id, ts, new_image_urls)
                return PlainTextResponse("OK")

            # Handle Edit (Restore)
            elif action_id == "edit_post":
                metadata = json.dumps({
                    "channel_id": payload.get("channel", {}).get("id"),
                    "ts": payload.get("message", {}).get("ts"),
                    "post_id": post_id
                })
                view_id = open_edit_modal(
                    payload.get("trigger_id"),
                    payload.get("channel", {}).get("id"),
                    payload.get("message", {}).get("ts"),
                    metadata=metadata
                )
                if view_id:
                    import asyncio
                    asyncio.create_task(
                        _task_open_edit_modal(
                            view_id, post_id, 
                            payload.get("channel", {}).get("id"),
                            payload.get("message", {}).get("ts"),
                            payload.get("response_url")
                        )
                    )
                return PlainTextResponse("OK")

    except Exception as e:
        logger.error(f"Error in slack_actions: {e}", exc_info=True)
        return PlainTextResponse("Error", status_code=500)

    return PlainTextResponse("OK")