import io
import requests
from config import config
from utils.logger import get_logger

logger = get_logger(__name__)

# Slack API base URL
_SLACK_API_BASE = "https://slack.com/api"


class SlackClient:
    """Thin wrapper around the Slack Web API. Centralizes auth headers and error surfacing."""

    def __init__(self, token: str):
        self._token = token
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        self._session = requests.Session()
        self._session.headers.update(self._headers)

    def post(self, endpoint: str, payload: dict, timeout: int = 30) -> dict:
        """POST to a Slack API endpoint. Returns parsed JSON or an error dict."""
        url = f"{_SLACK_API_BASE}/{endpoint}"
        try:
            res = self._session.post(url, json=payload, timeout=timeout)
            return res.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"SlackClient: request to '{endpoint}' failed — {e}")
            return {"ok": False, "error": str(e)}

    def upload_file(
        self,
        channel_id: str,
        content: str,
        filename: str = "newsletter.html",
        title: str = "Newsletter Preview",
        initial_comment: str = "",
        thread_ts: str = None,
        timeout: int = 30,
    ) -> dict:
        """
        Uploads a text/HTML file to Slack using the v2 upload flow:
          1. files.getUploadURLExternal  — get a one-time upload URL
          2. PUT the raw bytes to that URL
          3. files.completeUploadExternal — publish the file to the channel

        Returns the Slack response from step 3, or an error dict.
        """
        encoded = content.encode("utf-8")
        size = len(encoded)

        # Step 1 — request an upload URL
        # NOTE: files.getUploadURLExternal requires form-encoded params, NOT JSON.
        # We build a separate header dict without the JSON Content-Type.
        form_headers = {"Authorization": f"Bearer {self._token}"}
        try:
            r1 = requests.post(
                f"{_SLACK_API_BASE}/files.getUploadURLExternal",
                headers=form_headers,
                data={"filename": filename, "length": size},
                timeout=timeout,
            )
            data1 = r1.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"SlackClient.upload_file: getUploadURLExternal failed — {e}")
            return {"ok": False, "error": str(e)}

        if not data1.get("ok"):
            logger.error(f"SlackClient.upload_file: getUploadURLExternal error — {data1}")
            return data1

        upload_url = data1["upload_url"]
        file_id = data1["file_id"]

        # Step 2 — PUT the raw bytes to the upload URL (no Auth header needed)
        try:
            r2 = requests.put(
                upload_url,
                data=io.BytesIO(encoded),
                headers={"Content-Type": "text/html; charset=utf-8"},
                timeout=timeout,
            )
            if r2.status_code not in (200, 201):
                logger.error(f"SlackClient.upload_file: PUT upload failed — {r2.status_code} {r2.text}")
                return {"ok": False, "error": f"PUT failed with status {r2.status_code}"}
        except requests.exceptions.RequestException as e:
            logger.error(f"SlackClient.upload_file: PUT upload exception — {e}")
            return {"ok": False, "error": str(e)}

        # Step 3 — ensure the bot is in the channel, then complete the upload
        # conversations.join succeeds silently if already a member.
        # For private channels this will fail (already_in_channel or cant_join) —
        # in that case the user must manually /invite the bot.
        try:
            join_res = requests.post(
                f"{_SLACK_API_BASE}/conversations.join",
                headers=self._headers,
                json={"channel": channel_id},
                timeout=10,
            ).json()
            if not join_res.get("ok") and join_res.get("error") != "already_in_channel":
                logger.warning(
                    f"SlackClient.upload_file: could not join channel '{channel_id}' "
                    f"({join_res.get('error')}) — if it is a private channel, run "
                    f"'/invite @<bot-name>' in Slack and retry."
                )
        except requests.exceptions.RequestException as e:
            logger.warning(f"SlackClient.upload_file: conversations.join request failed — {e}")

        complete_payload = {
            "files": [{"id": file_id, "title": title}],
            "channel_id": channel_id,
            "initial_comment": initial_comment,
        }
        if thread_ts:
            complete_payload["thread_ts"] = thread_ts

        try:
            r3 = requests.post(
                f"{_SLACK_API_BASE}/files.completeUploadExternal",
                headers=self._headers,
                json=complete_payload,
                timeout=timeout,
            )
            data3 = r3.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"SlackClient.upload_file: completeUploadExternal failed — {e}")
            return {"ok": False, "error": str(e)}

        if not data3.get("ok"):
            logger.error(f"SlackClient.upload_file: completeUploadExternal error — {data3}")
        else:
            logger.info(f"SlackClient.upload_file: file '{filename}' uploaded (id={file_id})")

        return data3



# Module-level singleton — avoids reconstructing headers on every call
slack_client = SlackClient(config.SLACK_BOT_TOKEN)
