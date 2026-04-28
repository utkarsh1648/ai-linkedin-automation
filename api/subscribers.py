from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr

from utils.logger import get_logger
from services.subscriber_store import add_subscriber, remove_by_token, is_subscribed

logger = get_logger(__name__)

router = APIRouter(tags=["subscribers"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class SubscribeRequest(BaseModel):
    email: EmailStr
    name: str = ""
    contact: str = ""  # phone number or any other contact detail


class SubscribeResponse(BaseModel):
    status: str         # "subscribed" | "reactivated" | "already_subscribed"
    email: str
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/subscribe", response_model=SubscribeResponse)
async def subscribe(body: SubscribeRequest):
    """
    Subscribe an email address to the AI News Digest newsletter.
    Idempotent — re-subscribing a previously unsubscribed email reactivates it.
    """
    result = add_subscriber(email=body.email, name=body.name, contact=body.contact)
    status = result["status"]

    messages = {
        "subscribed": f"Welcome! You're now subscribed as {body.email}.",
        "reactivated": f"Welcome back! Your subscription for {body.email} has been reactivated.",
        "already_subscribed": f"{body.email} is already an active subscriber.",
    }
    logger.info(f"Subscribe request — {status}: {body.email}")
    return SubscribeResponse(status=status, email=body.email, message=messages.get(status, "OK"))


@router.get("/unsubscribe", response_class=HTMLResponse)
async def unsubscribe(token: str):
    """
    Token-based unsubscribe. The token is embedded in each newsletter's footer link.
    Returns a confirmation HTML page — no login required.
    """
    removed = remove_by_token(token)

    if removed:
        logger.info(f"Unsubscribe successful for token: {token[:8]}...")
        return _unsubscribe_page(
            success=True,
            message="You've been unsubscribed. You won't receive any more emails from us.",
        )

    # Token not found or already inactive — still show a friendly page
    logger.warning(f"Unsubscribe attempt with unknown/expired token: {token[:8]}...")
    return _unsubscribe_page(
        success=False,
        message="This unsubscribe link has already been used or is invalid.",
    )


# ---------------------------------------------------------------------------
# HTML confirmation page
# ---------------------------------------------------------------------------

def _unsubscribe_page(success: bool, message: str) -> str:
    icon = "✅" if success else "ℹ️"
    heading = "Unsubscribed" if success else "Already removed"
    accent = "#6366f1"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1.0" />
  <title>{heading} — AI News Digest</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:system-ui,-apple-system,Arial,sans-serif;
          background:#f8fafc;color:#1e293b;
          display:flex;align-items:center;justify-content:center;
          min-height:100vh;padding:20px}}
    .card{{background:#fff;border-radius:16px;border:1px solid #e2e8f0;
           max-width:440px;width:100%;padding:48px 40px;text-align:center;
           box-shadow:0 4px 24px rgba(0,0,0,.06)}}
    .icon{{font-size:48px;margin-bottom:20px}}
    h1{{font-size:24px;font-weight:700;margin-bottom:12px;color:#1e293b}}
    p{{font-size:15px;line-height:1.6;color:#64748b;margin-bottom:28px}}
    a{{display:inline-block;background:{accent};color:#fff;text-decoration:none;
       padding:12px 28px;border-radius:8px;font-weight:600;font-size:15px}}
    a:hover{{background:#4f46e5}}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">{icon}</div>
    <h1>{heading}</h1>
    <p>{message}</p>
    <a href="/">Back to Home</a>
  </div>
</body>
</html>"""
