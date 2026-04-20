import os
import uuid
import requests
import logging
from config import config

logger = logging.getLogger(__name__)

def upload_to_imgbb(file_path: str) -> str:
    """
    Uploads a local file to ImgBB and returns the direct image URL.
    """
    if not config.IMGBB_API_KEY:
        logger.warning("No IMGBB_API_KEY found. Falling back to local hosting.")
        return None

    try:
        url = "https://api.imgbb.com/1/upload"
        with open(file_path, "rb") as file:
            payload = {
                "key": config.IMGBB_API_KEY,
                "image": file.read(),
            }
            res = requests.post(url, data=payload, timeout=20)
            res.raise_for_status()
            data = res.json()
            return data["data"]["url"]
    except Exception as e:
        logger.error(f"Error uploading to ImgBB: {e}")
        return None

def download_slack_file(file_url: str, bot_token: str) -> str:
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
        headers = {"Authorization": f"Bearer {bot_token}"}
        
        response = requests.get(file_url, headers=headers, stream=True, timeout=15)
        response.raise_for_status()
        
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Priority: Try Cloud Hosting (ImgBB)
        if config.IMGBB_API_KEY:
            cloud_url = upload_to_imgbb(local_path)
            if cloud_url:
                logger.info(f"File uploaded to ImgBB: {cloud_url}")
                return cloud_url

        # Fallback: Local public URL (via Ngrok/Render)
        public_url = f"{config.BASE_PUBLIC_URL}/{config.MEDIA_DIR}/{filename}"
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
