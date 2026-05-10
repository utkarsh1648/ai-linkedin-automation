import requests
from config import config
from utils.logger import get_logger

logger = get_logger(__name__)

# Slack API base URL
_SLACK_API_BASE = "https://slack.com/api"


class SlackClient:
    """Thin wrapper around the Slack Web API. Centralizes auth headers and error surfacing."""

    def __init__(self, token: str):
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    def post(self, endpoint: str, payload: dict, timeout: int = 10) -> dict:
        """POST to a Slack API endpoint. Returns parsed JSON or an error dict."""
        url = f"{_SLACK_API_BASE}/{endpoint}"
        try:
            res = requests.post(url, headers=self._headers, json=payload, timeout=timeout)
            return res.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"SlackClient: request to '{endpoint}' failed — {e}")
            return {"ok": False, "error": str(e)}


# Module-level singleton — avoids reconstructing headers on every call
slack_client = SlackClient(config.SLACK_BOT_TOKEN)
