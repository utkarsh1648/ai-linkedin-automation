import json
import os
import uuid
import time
from typing import Dict, Optional, Protocol

from config import config
from utils.logger import get_logger

logger = get_logger(__name__)

class PendingPostStore(Protocol):
    def save_post(self, posts_data: Dict[str, str], image_urls: list) -> str: ...
    def get_post(self, post_id: str) -> Optional[dict]: ...
    def delete_post(self, post_id: str): ...

class JSONPendingPostStore:
    def __init__(self, storage_path: str = "pending_posts.json"):
        self.storage_path = storage_path

    def _load_all(self) -> dict:
        if os.path.exists(self.storage_path):
            with open(self.storage_path, "r", encoding="utf-8") as f:
                try:
                    return json.load(f)
                except:
                    return {}
        return {}

    def _save_all(self, data: dict):
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def save_post(self, posts_data: Dict[str, str], image_urls: list) -> str:
        post_id = str(uuid.uuid4())
        data = self._load_all()
        data[post_id] = {
            "posts": posts_data,
            "image_urls": image_urls,
            "created_at": time.time()
        }
        # Cleanup old posts (> 48h or count > 100)
        now = time.time()
        keys_to_delete = [k for k, v in data.items() if now - v.get("created_at", 0) > 172800]
        for k in keys_to_delete: del data[k]
        
        if len(data) > 100:
            oldest_keys = sorted(data.keys(), key=lambda k: data[k].get("created_at", 0))[:len(data)-100]
            for k in oldest_keys: del data[k]
                
        self._save_all(data)
        return post_id

    def get_post(self, post_id: str) -> Optional[dict]:
        return self._load_all().get(post_id)

    def delete_post(self, post_id: str):
        data = self._load_all()
        if post_id in data:
            del data[post_id]
            self._save_all(data)

class PostgresPendingPostStore:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self._init_db()

    def _get_connection(self):
        import psycopg2
        from psycopg2.extras import RealDictCursor
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    def _init_db(self):
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS pending_posts (
                        id TEXT PRIMARY KEY,
                        data JSONB NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                # Cleanup old records (older than 2 days)
                cur.execute("DELETE FROM pending_posts WHERE created_at < NOW() - INTERVAL '2 days';")
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to initialize Postgres pending_posts table: {e}")

    def save_post(self, posts_data: Dict[str, str], image_urls: list) -> str:
        post_id = str(uuid.uuid4())
        payload = {"posts": posts_data, "image_urls": image_urls}
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO pending_posts (id, data) VALUES (%s, %s)",
                    (post_id, json.dumps(payload))
                )
            conn.commit()
            conn.close()
            return post_id
        except Exception as e:
            logger.error(f"Postgres save_post error: {e}")
            return post_id

    def get_post(self, post_id: str) -> Optional[dict]:
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT data FROM pending_posts WHERE id = %s", (post_id,))
                row = cur.fetchone()
            conn.close()
            return row["data"] if row else None
        except Exception as e:
            logger.error(f"Postgres get_post error: {e}")
            return None

    def delete_post(self, post_id: str):
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("DELETE FROM pending_posts WHERE id = %s", (post_id,))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Postgres delete_post error: {e}")

def _resolve_store() -> PendingPostStore:
    if config.STORAGE_DRIVER == "postgres" and config.DATABASE_URL:
        logger.info("Using PostgreSQL driver for pending posts")
        return PostgresPendingPostStore(config.DATABASE_URL)
    logger.info("Using JSON driver for pending posts")
    return JSONPendingPostStore()

pending_post_service = _resolve_store()
