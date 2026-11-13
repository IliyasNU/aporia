import logging

from app.core.config import Settings


def configure_logging(settings: Settings) -> None:
    """Plain-text logs to stdout; the container runtime collects them.

    Never log secrets, session tokens or email addresses (SEC-05).
    """
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
