import requests
from config import config
from utils.logger import get_logger
from typing import List

logger = get_logger(__name__)

def post_to_linkedin(text: str, image_urls: List[str] = None) -> dict:
    url = "https://api.buffer.com"
    headers = {
        "Authorization": f"Bearer {config.BUFFER_TOKEN}",
        "Content-Type": "application/json"
    }

    # Note: Buffer GraphQL supports multi-image for LinkedIn via the 'media' input 
    # being a list OR having a specific structure.
    # Refined mutation to handle media items more flexibily.
    mutation = """
    mutation CreatePost($text: String!, $channelId: ChannelId!, $media: PostMediaInput) {
      createPost(input: {
        text: $text
        channelId: $channelId
        media: $media
        schedulingType: automatic
        mode: shareNow
      }) {
        ... on PostActionSuccess {
          post {
            id
            text
          }
        }
        ... on MutationError {
          message
        }
      }
    }
    """

    variables = {
        "text": text,
        "channelId": config.CHANNEL_ID
    }

    # Handling individual images vs lists.
    # Most Buffer plans support one media object with 'photoUrl'.
    # For multi-image, we should check for 'extraMedia' or specialized inputs.
    # We will prioritize the first image to ensure functionality.
    if image_urls:
        first_image = image_urls[0]
        variables["media"] = {
            "photoUrl": first_image,
            "altText": "LinkedIn Post Image"
        }
        
        # If there are additional images, we log it. 
        # Robust multi-image LinkedIn support in Buffer often needs 'attachments'.
        if len(image_urls) > 1:
            logger.info(f"Posting first image to Buffer. (Total {len(image_urls)} images selected).")

    payload = {
        "query": mutation,
        "variables": variables
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"Failed to post to buffer/linkedin: {e}")
        return {"error": str(e)}