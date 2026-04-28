"""
Pluggable subscriber store.

The default driver is JSON — zero dependencies, single file, same pattern
as news_cache.json. Switch backends via the SUBSCRIBER_DRIVER env var:

  SUBSCRIBER_DRIVER=json      (default — no dependencies)
  SUBSCRIBER_DRIVER=sqlite    (requires: nothing extra, ships with Python)
  SUBSCRIBER_DRIVER=postgres  (requires: pip install psycopg2-binary + DATABASE_URL)

Adding a new backend (community contribution)
---------------------------------------------
1. Subclass BaseSubscriberStore and implement all abstract methods.
2. Register the driver name in _resolve_store() below.
3. Document the required env vars in .env.example.

All four public functions at the bottom of this file stay the same regardless
of which driver is active — no other file in the project needs to change.
"""

import json
import threading
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List

from config import config
from utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Subscriber schema (shared across all drivers)
# ---------------------------------------------------------------------------
# {
#   "email":             "user@example.com",
#   "name":              "Jane Doe",
#   "contact":           "+91-9876543210",   # phone / any contact detail
#   "unsubscribe_token": "<uuid4>",
#   "subscribed_at":     "2026-04-22T10:00:00+00:00",
#   "is_active":         true
# }


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class BaseSubscriberStore(ABC):
    """Contract every subscriber-store driver must satisfy."""

    @abstractmethod
    def init(self) -> None:
        """Initialise the store (create file / table / collection). Idempotent."""

    @abstractmethod
    def add_subscriber(self, email: str, name: str = "", contact: str = "") -> dict:
        """
        Add a new subscriber or reactivate a removed one.
        Returns: {"status": "subscribed"|"reactivated"|"already_subscribed",
                  "email": str, "unsubscribe_token": str}
        """

    @abstractmethod
    def remove_by_token(self, token: str) -> bool:
        """Soft-delete by unsubscribe token. Returns True if a record was found."""

    @abstractmethod
    def get_all_active(self) -> List[dict]:
        """Return active subscribers as [{email, name, contact, unsubscribe_token}]."""

    @abstractmethod
    def is_subscribed(self, email: str) -> bool:
        """Return True if the email is an active subscriber."""


# ---------------------------------------------------------------------------
# JSON driver (default)
# ---------------------------------------------------------------------------

class JSONSubscriberStore(BaseSubscriberStore):
    """
    Stores subscribers as a JSON array in a local file.
    Same zero-dependency approach as news_cache.json.

    Thread-safe: a module-level lock prevents concurrent write corruption.
    Set SUBSCRIBERS_JSON_PATH to control the file location.
    On Render: commit the file or mount a persistent disk so it survives deploys.
    """

    _lock = threading.Lock()

    def init(self) -> None:
        """Create an empty JSON file if it doesn't exist."""
        import os
        if not os.path.exists(config.SUBSCRIBERS_JSON_PATH):
            self._write([])
            logger.info(f"Created subscriber file at '{config.SUBSCRIBERS_JSON_PATH}'")
        else:
            logger.info(f"JSON subscriber store ready at '{config.SUBSCRIBERS_JSON_PATH}'")

    # --- Internal helpers ---

    def _read(self) -> List[dict]:
        try:
            with open(config.SUBSCRIBERS_JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _write(self, data: List[dict]) -> None:
        with open(config.SUBSCRIBERS_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # --- Interface implementation ---

    def add_subscriber(self, email: str, name: str = "", contact: str = "") -> dict:
        email = email.strip().lower()
        name = name.strip()
        contact = contact.strip()

        with self._lock:
            subscribers = self._read()

            # Check for existing record
            for sub in subscribers:
                if sub["email"] == email:
                    if sub["is_active"]:
                        return {"status": "already_subscribed", "email": email,
                                "unsubscribe_token": sub["unsubscribe_token"]}
                    # Reactivate
                    sub.update({
                        "name": name or sub["name"],
                        "contact": contact or sub.get("contact", ""),
                        "is_active": True,
                        "subscribed_at": datetime.now(timezone.utc).isoformat(),
                    })
                    self._write(subscribers)
                    logger.info(f"Reactivated subscriber: {email}")
                    return {"status": "reactivated", "email": email,
                            "unsubscribe_token": sub["unsubscribe_token"]}

            # New subscriber
            token = str(uuid.uuid4())
            subscribers.append({
                "email": email,
                "name": name,
                "contact": contact,
                "unsubscribe_token": token,
                "subscribed_at": datetime.now(timezone.utc).isoformat(),
                "is_active": True,
            })
            self._write(subscribers)
            logger.info(f"New subscriber: {email}")
            return {"status": "subscribed", "email": email, "unsubscribe_token": token}

    def remove_by_token(self, token: str) -> bool:
        with self._lock:
            subscribers = self._read()
            found = False
            for sub in subscribers:
                if sub["unsubscribe_token"] == token and sub["is_active"]:
                    sub["is_active"] = False
                    found = True
                    break
            if found:
                self._write(subscribers)
                logger.info(f"Unsubscribed via token: {token[:8]}...")
        return found

    def get_all_active(self) -> List[dict]:
        subscribers = self._read()
        return [
            {
                "email": s["email"],
                "name": s.get("name", ""),
                "contact": s.get("contact", ""),
                "unsubscribe_token": s["unsubscribe_token"],
            }
            for s in subscribers
            if s.get("is_active")
        ]

    def is_subscribed(self, email: str) -> bool:
        email = email.strip().lower()
        return any(
            s["email"] == email and s.get("is_active")
            for s in self._read()
        )


# ---------------------------------------------------------------------------
# SQLite driver (optional — uncomment and set SUBSCRIBER_DRIVER=sqlite)
# ---------------------------------------------------------------------------

class SQLiteSubscriberStore(BaseSubscriberStore):
    """
    SQLite-backed store. Ships with Python, no extra packages needed.
    Set SUBSCRIBERS_DB_PATH to control the file location.
    """

    _CREATE_TABLE = """
    CREATE TABLE IF NOT EXISTS subscribers (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        email             TEXT UNIQUE NOT NULL,
        name              TEXT NOT NULL DEFAULT '',
        contact           TEXT NOT NULL DEFAULT '',
        unsubscribe_token TEXT UNIQUE NOT NULL,
        subscribed_at     TEXT NOT NULL,
        is_active         INTEGER NOT NULL DEFAULT 1
    )
    """

    def _conn(self):
        from contextlib import contextmanager
        import sqlite3

        @contextmanager
        def _ctx():
            conn = sqlite3.connect(config.SUBSCRIBERS_DB_PATH)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

        return _ctx()

    def init(self) -> None:
        with self._conn() as conn:
            conn.execute(self._CREATE_TABLE)
        logger.info(f"SQLite subscriber store ready at '{config.SUBSCRIBERS_DB_PATH}'")

    def add_subscriber(self, email: str, name: str = "", contact: str = "") -> dict:
        email = email.strip().lower()
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT is_active, unsubscribe_token FROM subscribers WHERE email=?", (email,)
            ).fetchone()
            if row:
                if row["is_active"]:
                    return {"status": "already_subscribed", "email": email,
                            "unsubscribe_token": row["unsubscribe_token"]}
                conn.execute(
                    "UPDATE subscribers SET is_active=1, name=?, contact=?, subscribed_at=? WHERE email=?",
                    (name, contact, now, email),
                )
                return {"status": "reactivated", "email": email,
                        "unsubscribe_token": row["unsubscribe_token"]}
            token = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO subscribers (email, name, contact, unsubscribe_token, subscribed_at) "
                "VALUES (?,?,?,?,?)", (email, name, contact, token, now),
            )
            return {"status": "subscribed", "email": email, "unsubscribe_token": token}

    def remove_by_token(self, token: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                "UPDATE subscribers SET is_active=0 WHERE unsubscribe_token=? AND is_active=1",
                (token,),
            )
        return cur.rowcount > 0

    def get_all_active(self) -> List[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT email, name, contact, unsubscribe_token FROM subscribers WHERE is_active=1"
            ).fetchall()
        return [dict(r) for r in rows]

    def is_subscribed(self, email: str) -> bool:
        with self._conn() as conn:
            return conn.execute(
                "SELECT 1 FROM subscribers WHERE email=? AND is_active=1", (email.strip().lower(),)
            ).fetchone() is not None


# ---------------------------------------------------------------------------
# PostgreSQL driver (optional — requires: pip install psycopg2-binary)
# ---------------------------------------------------------------------------

class PostgreSQLSubscriberStore(BaseSubscriberStore):
    """
    PostgreSQL-backed store. Great for Render Postgres or Supabase.
    Requires: pip install psycopg2-binary
    Set: SUBSCRIBER_DRIVER=postgres  DATABASE_URL=postgresql://...
    """

    _CREATE_TABLE = """
    CREATE TABLE IF NOT EXISTS subscribers (
        id                SERIAL PRIMARY KEY,
        email             TEXT UNIQUE NOT NULL,
        name              TEXT NOT NULL DEFAULT '',
        contact           TEXT NOT NULL DEFAULT '',
        unsubscribe_token TEXT UNIQUE NOT NULL,
        subscribed_at     TIMESTAMPTZ NOT NULL,
        is_active         BOOLEAN NOT NULL DEFAULT TRUE
    )
    """

    def __init__(self):
        if not config.DATABASE_URL:
            raise ValueError("DATABASE_URL is required for the postgres driver.")
        try:
            import psycopg2  # noqa
        except ImportError:
            raise ImportError("Run: pip install psycopg2-binary")

    from contextlib import contextmanager

    @contextmanager
    def _conn(self):
        import psycopg2
        conn = psycopg2.connect(config.DATABASE_URL)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init(self) -> None:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(self._CREATE_TABLE)
        logger.info("PostgreSQL subscriber store ready")

    def add_subscriber(self, email: str, name: str = "", contact: str = "") -> dict:
        email = email.strip().lower()
        now = datetime.now(timezone.utc)
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT is_active, unsubscribe_token FROM subscribers WHERE email=%s", (email,)
                )
                row = cur.fetchone()
                if row:
                    if row[0]:
                        return {"status": "already_subscribed", "email": email, "unsubscribe_token": row[1]}
                    cur.execute(
                        "UPDATE subscribers SET is_active=TRUE, name=%s, contact=%s, subscribed_at=%s WHERE email=%s",
                        (name, contact, now, email),
                    )
                    return {"status": "reactivated", "email": email, "unsubscribe_token": row[1]}
                token = str(uuid.uuid4())
                cur.execute(
                    "INSERT INTO subscribers (email, name, contact, unsubscribe_token, subscribed_at) "
                    "VALUES (%s,%s,%s,%s,%s)", (email, name, contact, token, now),
                )
                return {"status": "subscribed", "email": email, "unsubscribe_token": token}

    def remove_by_token(self, token: str) -> bool:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE subscribers SET is_active=FALSE WHERE unsubscribe_token=%s AND is_active=TRUE",
                    (token,),
                )
                return cur.rowcount > 0

    def get_all_active(self) -> List[dict]:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT email, name, contact, unsubscribe_token FROM subscribers WHERE is_active=TRUE"
                )
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, r)) for r in cur.fetchall()]

    def is_subscribed(self, email: str) -> bool:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM subscribers WHERE email=%s AND is_active=TRUE",
                            (email.strip().lower(),))
                return cur.fetchone() is not None


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def _resolve_store() -> BaseSubscriberStore:
    driver = config.SUBSCRIBER_DRIVER
    if driver == "sqlite":
        logger.info("Subscriber store driver: SQLite")
        return SQLiteSubscriberStore()
    if driver == "postgres":
        logger.info("Subscriber store driver: PostgreSQL")
        return PostgreSQLSubscriberStore()
    if driver != "json":
        logger.warning(
            f"Unknown SUBSCRIBER_DRIVER='{driver}' — falling back to JSON. "
            "Valid options: json, sqlite, postgres"
        )
    logger.info("Subscriber store driver: JSON")
    return JSONSubscriberStore()


# ---------------------------------------------------------------------------
# Module-level singleton + public API (driver-agnostic)
# ---------------------------------------------------------------------------

_store: BaseSubscriberStore = _resolve_store()
_store.init()


def add_subscriber(email: str, name: str = "", contact: str = "") -> dict:
    return _store.add_subscriber(email, name, contact)


def remove_by_token(token: str) -> bool:
    return _store.remove_by_token(token)


def get_all_active() -> List[dict]:
    return _store.get_all_active()


def is_subscribed(email: str) -> bool:
    return _store.is_subscribed(email)
