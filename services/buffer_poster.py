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

    assets_block = ""
    if image_urls:
        images_str = ", ".join([f'{{url: "{url}"}}' for url in image_urls])
        assets_block = f'assets: {{ images: [ {images_str} ] }}'

    mutation = f"""
    mutation CreatePost($text: String!, $channelId: ChannelId!) {{
      createPost(input: {{
        text: $text
        channelId: $channelId
        {assets_block}
        schedulingType: automatic
        mode: shareNow
      }}) {{
        ... on PostActionSuccess {{
          post {{
            id
            text
          }}
        }}
        ... on MutationError {{
          message
        }}
      }}
    }}
    """

    variables = {
        "text": text,
        "channelId": config.CHANNEL_ID
    }
        
    payload = {
        "query": mutation,
        "variables": variables
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        # Buffer GraphQL often returns HTTP 200 with an "errors" array inside the JSON if things fail
        data = response.json()
        logger.info(f"Buffer GraphQL Response: {data}")
        return data
    except Exception as e:
        logger.error(f"Failed to post to buffer/linkedin: {e}")
        return {"error": str(e)}