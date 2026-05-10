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
                logger.error(f"ImgBB API Error (Status {res.status_code}): {res.text}")
                return None
            
            data = res.json()
            if data.get("success"):
                image_url = data["data"]["url"]
                logger.info(f"ImgBB: Successfully uploaded. Direct URL: {image_url}")
                return image_url
            else:
                logger.error(f"ImgBB API returned success=False: {data}")
                return None
    except Exception as e:
        logger.error(f"ImgBB Upload Exception: {e}")
        return None

def download_slack_file_local(file_url: str, bot_token: str) -> Optional[str]:
    """
    Downloads a file from Slack and returns the local file path.
    Does NOT upload to cloud.
    """
    try:
        ext = file_url.split('.')[-1].split('?')[0]
        if len(ext) > 4: ext = "png"
        filename = f"{uuid.uuid4()}.{ext}"
        local_path = os.path.join(config.MEDIA_DIR, filename)
        
        os.makedirs(config.MEDIA_DIR, exist_ok=True)
        
        class SlackSession(requests.Session):
            def rebuild_auth(self, prepared_request, response): pass

        session = SlackSession()
        headers = {"Authorization": f"Bearer {bot_token}"}
        
        response = session.get(file_url, headers=headers, stream=True, timeout=15)
        response.raise_for_status()
        
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        return local_path
    except Exception as e:
        logger.error(f"Error downloading slack file locally: {e}")
        return None

def download_slack_file(file_url: str, bot_token: str, base_url: str = None) -> Optional[str]:
    """
    Downloads a file from Slack and returns a public URL (ImgBB preferred).
    """
    local_path = download_slack_file_local(file_url, bot_token)
    if not local_path:
        return None
        
    try:
        # Priority: Try Cloud Hosting (ImgBB)
        if config.IMGBB_API_KEY:
            cloud_url = upload_to_imgbb(local_path)
            if cloud_url:
                # Cleanup local temp
                try: os.remove(local_path)
                except: pass
                return cloud_url

        # Fallback: Local public URL
        actual_base = base_url if base_url else config.BASE_PUBLIC_URL
        filename = os.path.basename(local_path)
        public_url = f"{actual_base}/{config.MEDIA_DIR}/{filename}"
        return public_url
        
    except Exception as e:
        logger.error(f"Error in file handling wrapper: {e}")
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
