import os
import uuid
import requests
from config import config
from utils.logger import get_logger

logger = get_logger(__name__)

def upload_to_imgbb(file_path: str) -> str:
    """
    Uploads a local file to ImgBB and returns the direct image URL.
    """
    imgbb_key = getattr(config, 'IMGBB_API_KEY', None)
    if not imgbb_key:
        logger.warning("No IMGBB_API_KEY found. Falling back to local hosting.")
        return None

    try:
        url = "https://api.imgbb.com/1/upload"
        with open(file_path, "rb") as file:
            res = requests.post(url, data={"key": imgbb_key}, files={"image": file}, timeout=20)
            if res.status_code != 200:
                logger.error(f"ImgBB failed with {res.status_code}: {res.text}")
            res.raise_for_status()
            data = res.json()
            return data["data"]["url"]
    except Exception as e:
        logger.error(f"Error uploading to ImgBB: {e}")
        return None

def download_slack_file(file_url: str, bot_token: str, base_url: str = None) -> str:
    """
    Downloads a file from Slack as a temporary local copy, 
    then optionally uploads to ImgBB for permanent hosting.
    """
    try:
        # Clean extension and prepare local path
        ext = file_url.split('.')[-1].split('?')[0]
        if len(ext) > 4: ext = "png"
        filename = f"{uuid.uuid4()}.{ext}"
        local_path = os.path.join(config.MEDIA_DIR, filename)
        
        os.makedirs(config.MEDIA_DIR, exist_ok=True)
        if not bot_token.startswith("xoxb-"):
            logger.error("Bot token does not start with xoxb-. File download will fail.")

        class SlackSession(requests.Session):
            def rebuild_auth(self, prepared_request, response):
                # Prevent requests from stripping the Authorization header on redirects 
                # (Slack redirects from files.slack.com to slack-edge.com)
                pass

        session = SlackSession()
        headers = {"Authorization": f"Bearer {bot_token}"}
        
        response = session.get(file_url, headers=headers, stream=True, timeout=15)
        response.raise_for_status()
        
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        file_size = os.path.getsize(local_path)
        logger.info(f"Downloaded slack file to {local_path}, size: {file_size} bytes")
        
        # Priority: Try Cloud Hosting (ImgBB)
        if getattr(config, 'IMGBB_API_KEY', None):
            cloud_url = upload_to_imgbb(local_path)
            if cloud_url:
                logger.info(f"File uploaded to ImgBB: {cloud_url}")
                return cloud_url

        # Fallback: Local public URL (via dynamically captured base_url or Ngrok/Render fallback)
        actual_base = base_url if base_url else config.BASE_PUBLIC_URL
        public_url = f"{actual_base}/{config.MEDIA_DIR}/{filename}"
        logger.info(f"Using local public URL: {public_url}")
        return public_url
        
    except Exception as e:
        logger.error(f"Error in file handling: {e}")
        return None

def delete_local_file(public_url: str):
    """
    Deletes a local file based on its public URL.
    """
    try:
        if not public_url:
            return
            
        filename = public_url.split('/')[-1]
        local_path = os.path.join(config.MEDIA_DIR, filename)
        
        if os.path.exists(local_path):
            os.remove(local_path)
            logger.info(f"Successfully deleted local file: {local_path}")
    except Exception as e:
        logger.error(f"Error deleting local file: {e}")
