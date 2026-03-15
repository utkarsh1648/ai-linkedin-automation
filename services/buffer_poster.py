import requests
import os
from dotenv import load_dotenv

load_dotenv()


def post_to_linkedin(text):

    url = "https://api.buffer.com"

    token = os.getenv("BUFFER_TOKEN")
    channel_id = os.getenv("CHANNEL_ID")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    mutation = """
    mutation CreatePost($text: String!, $channelId: ChannelId!) {
      createPost(input: {
        text: $text
        channelId: $channelId
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

    payload = {
        "query": mutation,
        "variables": {
            "text": text,
            "channelId": channel_id
        }
    }

    response = requests.post(url, json=payload, headers=headers)

    return response.json()