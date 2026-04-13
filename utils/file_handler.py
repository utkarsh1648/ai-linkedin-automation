import os
import uuid
import requests
import logging
from config import config

logger = logging.getLogger(__name__)

def download_slack_file(file_url: str, bot_token: str) -> str:
    """
    Downloads a file from Slack using the bot token and saves it to the local media directory.
    Returns the public URL for the file.
    """
    try:
        # Create unique filename to avoid collisions
        ext = file_url.split('.')[-1]
        filename = f"{uuid.uuid4()}.{ext}"
        local_path = os.path.join(config.MEDIA_DIR, filename)
        
        headers = {"Authorization": f"Bearer {bot_token}"}
        response = requests.get(file_url, headers=headers, stream=True, timeout=15)
        response.raise_for_status()
        
        os.makedirs(config.MEDIA_DIR, exist_ok=True)
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        public_url = f"{config.BASE_PUBLIC_URL}/{config.MEDIA_DIR}/{filename}"
        logger.info(f"File downloaded and saved to {local_path}. Public URL: {public_url}")
        return public_url
        
    except Exception as e:
        logger.error(f"Error downloading file from Slack: {e}")
        return None

def delete_local_file(public_url: str):
    """
    Deletes a local file based on its public URL.
    """
    try:
        if not public_url:
            return
            
        # Extract filename from public URL
        filename = public_url.split('/')[-1]
        local_path = os.path.join(config.MEDIA_DIR, filename)
        
        if os.path.exists(local_path):
            os.remove(local_path)
            logger.info(f"Successfully deleted local file: {local_path}")
    except Exception as e:
        logger.error(f"Error deleting local file: {e}")
