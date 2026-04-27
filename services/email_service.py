"""
Email dispatch service with a pluggable driver model.

Supported drivers (set via EMAIL_DRIVER env var):
  - "resend"  : Resend API (https://resend.com) — recommended, great deliverability
  - "smtp"    : Any SMTP server (Gmail, Outlook, custom relay)

Usage:
    service = EmailService()
    results = service.send_newsletter(recipients, subject, html_body, plain_body)
"""

import smtplib
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

from config import config
from utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Driver abstractions
# ---------------------------------------------------------------------------

class BaseEmailDriver(ABC):
    """Interface every email driver must implement."""

    @abstractmethod
    def send(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        html_body: str,
        plain_body: str,
    ) -> bool:
        """Send a single email. Returns True on success, False on failure."""


class ResendDriver(BaseEmailDriver):
    """Sends email via the Resend API (https://resend.com)."""

    def __init__(self):
        if not config.RESEND_API_KEY:
            raise ValueError("RESEND_API_KEY is not set. Add it to your .env file.")
        try:
            import resend as _resend
            self._resend = _resend
            self._resend.api_key = config.RESEND_API_KEY
        except ImportError:
            raise ImportError("The 'resend' package is required. Run: pip install resend")

    def send(self, to_email: str, to_name: str, subject: str, html_body: str, plain_body: str) -> bool:
        to_address = f"{to_name} <{to_email}>" if to_name else to_email
        from_address = (
            f"{config.EMAIL_SENDER_NAME} <{config.EMAIL_SENDER}>"
            if config.EMAIL_SENDER_NAME
            else config.EMAIL_SENDER
        )
        try:
            params = {
                "from": from_address,
                "to": [to_address],
                "subject": subject,
                "html": html_body,
                "text": plain_body,
            }
            self._resend.Emails.send(params)
            return True
        except Exception as e:
            logger.error(f"ResendDriver: failed to send to '{to_email}': {e}")
            return False


class SmtpDriver(BaseEmailDriver):
    """Sends email via SMTP with STARTTLS (works with Gmail, Outlook, Mailgun SMTP, etc.)."""

    def __init__(self):
        if not config.SMTP_USER or not config.SMTP_PASSWORD:
            raise ValueError("SMTP_USER and SMTP_PASSWORD must be set for the SMTP driver.")

    def send(self, to_email: str, to_name: str, subject: str, html_body: str, plain_body: str) -> bool:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = (
            f"{config.EMAIL_SENDER_NAME} <{config.EMAIL_SENDER or config.SMTP_USER}>"
        )
        msg["To"] = f"{to_name} <{to_email}>" if to_name else to_email

        msg.attach(MIMEText(plain_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
                server.ehlo()
                server.starttls()
                server.login(config.SMTP_USER, config.SMTP_PASSWORD)
                server.sendmail(config.SMTP_USER, to_email, msg.as_string())
            return True
        except Exception as e:
            logger.error(f"SmtpDriver: failed to send to '{to_email}': {e}")
            return False


# ---------------------------------------------------------------------------
# Email Service
# ---------------------------------------------------------------------------

class EmailService:
    """
    Orchestrates newsletter delivery to a list of subscribers.
    Driver is selected from config.EMAIL_DRIVER ("resend" or "smtp").
    """

    def __init__(self):
        self._driver = self._resolve_driver()
        logger.info(f"EmailService initialised with driver: {config.EMAIL_DRIVER}")

    def _resolve_driver(self) -> BaseEmailDriver:
        if config.EMAIL_DRIVER == "smtp":
            return SmtpDriver()
        # Default to Resend
        return ResendDriver()

    def send_newsletter(
        self,
        recipients: List[dict],
        subject: str,
        html_template: str,
        plain_template: str,
    ) -> dict:
        """
        Sends the newsletter to every recipient individually so each email
        carries a personalised greeting and a unique unsubscribe token.

        Args:
            recipients: list of dicts with keys: email, name, unsubscribe_token, html_body, plain_body
                        (html_body and plain_body are pre-rendered per recipient by the caller)
            subject: email subject line
            html_template: unused; kept for backwards-compat signature
            plain_template: unused; kept for backwards-compat signature

        Returns:
            {"sent": int, "failed": int, "errors": list[str]}
        """
        sent, failed, errors = 0, 0, []

        for recipient in recipients:
            email = recipient["email"]
            name = recipient.get("name", "")
            html_body = recipient.get("html_body", html_template)
            plain_body = recipient.get("plain_body", plain_template)

            ok = self._driver.send(email, name, subject, html_body, plain_body)
            if ok:
                sent += 1
                logger.info(f"Newsletter sent to: {email}")
            else:
                failed += 1
                errors.append(email)

        logger.info(f"Newsletter dispatch complete — sent: {sent}, failed: {failed}")
        return {"sent": sent, "failed": failed, "errors": errors}
