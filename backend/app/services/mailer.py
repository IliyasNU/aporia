"""Building and sending emails over SMTP (Mailpit locally, a real provider in production)."""

import smtplib
from email.message import EmailMessage
from email.utils import make_msgid

from app.core.config import get_settings


class TemporaryEmailError(Exception):
    """Worth retrying later: server unreachable, timeout, 4xx answers."""


class PermanentEmailError(Exception):
    """Retrying will not help: the server rejected the message (5xx)."""


def _header(text: str) -> str:
    # Newlines in a header would let user content (e.g. a title) inject headers.
    return " ".join(text.split())


def build_message(
    *, to: str, subject: str, body: str, unsubscribe_url: str | None = None
) -> EmailMessage:
    settings = get_settings()
    message = EmailMessage()
    message["From"] = settings.mail_from
    message["To"] = to
    message["Subject"] = _header(subject)
    message["Message-ID"] = make_msgid(domain="aporia.localhost")
    if unsubscribe_url:
        message["List-Unsubscribe"] = f"<{unsubscribe_url}>"
    message.set_content(body)
    return message


def send(message: EmailMessage) -> None:
    """Deliver one message, translating SMTP errors into temporary or permanent ones.

    Tests replace this function with an in-memory outbox.
    """
    settings = get_settings()
    try:
        with smtplib.SMTP(
            settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout_seconds
        ) as smtp:
            if settings.smtp_starttls:
                smtp.starttls()
            if settings.smtp_username and settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password.get_secret_value())
            smtp.send_message(message)
    except smtplib.SMTPResponseException as exc:
        if 500 <= exc.smtp_code < 600:
            raise PermanentEmailError(f"smtp_{exc.smtp_code}") from exc
        raise TemporaryEmailError(f"smtp_{exc.smtp_code}") from exc
    except smtplib.SMTPRecipientsRefused as exc:
        raise PermanentEmailError("smtp_recipient_refused") from exc
    except (OSError, smtplib.SMTPException) as exc:
        # Connection refused, DNS, timeouts, dropped connections...
        raise TemporaryEmailError("smtp_unavailable") from exc
