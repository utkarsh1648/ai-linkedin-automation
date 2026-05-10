import requests
from config import config
from utils.logger import get_logger
from typing import List

logger = get_logger(__name__)

def broadcast_to_buffer(posts: dict, selected_channels: dict, image_urls: list = None) -> list:
    """
    Broadcasts posts to multiple Buffer channels.
    :param posts: Dict mapping styles to text, e.g. {"professional": "...", "short": "..."}
    :param selected_channels: Dict mapping channel_id to style, e.g. {"id1": "professional"}
    :param image_urls: List of public image URLs to attach.
    """
    results = []
    url = "https://api.buffer.com"
    headers = {
        "Authorization": f"Bearer {config.BUFFER_TOKEN}",
        "Content-Type": "application/json"
    }

    from services.visual_service import VisualService
    from utils.file_handler import upload_to_imgbb
    import os

    visual_service = VisualService()

    for channel_id, style in selected_channels.items():
        # Get the text for this specific style, fallback to 'linkedin'
        text = posts.get(style, posts.get("linkedin", "No content available"))
        
        assets_block = ""
        current_images = image_urls or []
        
        if current_images:
            # Smart Instagram Image Handling
            if style == "instagram":
                ig_images = []
                from utils.file_handler import download_slack_file # Re-using download logic
                
                logger.info(f"Instagram: Performing Universal Scan on {len(current_images)} images...")
                for idx, img_url in enumerate(current_images):
                    try:
                        # 1. Get the image locally to check it
                        local_path = None
                        if config.BASE_PUBLIC_URL in img_url:
                            # Already local
                            filename = img_url.split('/')[-1]
                            local_path = os.path.join(config.MEDIA_DIR, filename)
                        else:
                            # Cloud URL? Download it temporarily
                            temp_filename = f"ig_temp_{idx}_{os.path.basename(img_url.split('?')[0])}"
                            local_path = os.path.join(config.MEDIA_DIR, temp_filename)
                            import requests
                            r = requests.get(img_url, timeout=10)
                            with open(local_path, "wb") as f:
                                f.write(r.content)

                        # 2. Check and Square
                        if os.path.exists(local_path):
                            is_square = visual_service.is_square(local_path)
                            
                            # RULE: Instagram MUST use Cloud URLs (ImgBB) to avoid Ngrok blocks
                            if is_square and config.BASE_PUBLIC_URL not in img_url:
                                # It's square AND already in the cloud? Safe to use as-is.
                                ig_images.append(img_url)
                            else:
                                # It's either NOT square OR it's local (Ngrok). 
                                # We must process and/or upload it to ImgBB.
                                logger.info(f"Instagram: Processing/Uploading image {idx+1} to Cloud...")
                                final_path = local_path
                                if not is_square:
                                    final_path = visual_service.square_image(local_path)
                                
                                cloud_url = upload_to_imgbb(final_path)
                                if cloud_url:
                                    ig_images.append(cloud_url)
                                
                            # Cleanup temp file if we downloaded it
                            if f"ig_temp_{idx}_" in local_path:
                                try: os.remove(local_path)
                                except: pass
                    except Exception as e:
                        logger.error(f"Failed to process image {idx+1} for Instagram: {e}")
                        ig_images.append(img_url) # Final fallback
                
                images_to_use = ig_images[:10]
            else:
                # Other platforms get the original set
                images_to_use = current_images
            
            images_str = ", ".join([f'{{url: "{u}"}}' for u in images_to_use])
            assets_block = f'assets: {{ images: [ {images_str} ] }}'
            logger.info(f"Attaching {len(images_to_use)} images for {style}")

        # Add Instagram-specific metadata
        metadata_block = ""
        if style == "instagram":
            metadata_block = "metadata: { instagram: { type: post, shouldShareToFeed: true } }"

        mutation = f"""
        mutation CreatePost($text: String!, $channelId: ChannelId!) {{
          createPost(input: {{
            text: $text
            channelId: $channelId
            {assets_block}
            {metadata_block}
            schedulingType: automatic
            mode: shareNow
          }}) {{
            ... on PostActionSuccess {{
              post {{ 
                id 
                text 
                status
              }}
            }}
            ... on MutationError {{
              message
            }}
          }}
        }}
        """

        payload = {
            "query": mutation,
            "variables": {"text": text, "channelId": channel_id}
        }

        try:
            logger.info(f"Broadcasting to channel {channel_id} with style {style}")
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            data = response.json()
            
            # Detailed logging of the Buffer response to catch errors
            if "errors" in data or "error" in data:
                logger.error(f"Buffer Error for {channel_id}: {data}")
            else:
                logger.info(f"Buffer Success for {channel_id}: {data}")
                
            results.append({"channel_id": channel_id, "response": data})
        except Exception as e:
            logger.error(f"Failed to post to channel {channel_id}: {e}")
            results.append({"channel_id": channel_id, "error": str(e)})
            
    return results