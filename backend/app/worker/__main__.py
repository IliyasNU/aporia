"""The email worker process: `python -m app.worker` (or `--once` for a single pass)."""

import argparse
import logging
import signal
import time
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.worker.email_jobs import clean_up, run_batch

logger = logging.getLogger("app.worker")
CLEANUP_EVERY_SECONDS = 3600


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.worker")
    parser.add_argument("--once", action="store_true", help="process due jobs once and exit")
    args = parser.parse_args()
    settings = get_settings()
    configure_logging(settings)

    stopping = False

    def stop(*_: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    logger.info("Email worker started")
    last_cleanup = 0.0
    while not stopping:
        try:
            with SessionLocal() as db:
                sent = run_batch(db)
                if time.monotonic() - last_cleanup > CLEANUP_EVERY_SECONDS:
                    clean_up(db)
                    last_cleanup = time.monotonic()
            # Only a pass that reached the database counts as healthy
            # (python -m app.worker.healthcheck reads this file's age).
            Path(settings.worker_heartbeat_file).touch()
        except Exception:
            # e.g. the database restarting: log, wait, try again.
            logger.exception("Email worker iteration failed")
            sent = 0
        if args.once:
            break
        if sent == 0:
            time.sleep(settings.worker_poll_seconds)
    logger.info("Email worker stopped")


if __name__ == "__main__":
    main()
