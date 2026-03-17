import os
import requests
from dotenv import load_dotenv

load_dotenv()

def send_slack_notification(message):
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    payload = {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*AI Generated LinkedIn Post*\n\n{message}"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Approve"},
                        "style": "primary",
                        "value": "approve",
                        "action_id": "approve_post"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Reject"},
                        "style": "danger",
                        "value": "reject",
                        "action_id": "reject_post"
                    }
                ]
            }
        ]
    }
     
    response = requests.post(webhook_url, json=payload)
    if response.status_code != 200:
        raise ValueError(f"Request to Slack returned an error {response.status_code}, the response is:\n{response.text}")

    return response