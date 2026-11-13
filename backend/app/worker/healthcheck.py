"""Container healthcheck for the worker: healthy while its loop keeps running.

Exit code 0 if the heartbeat file was touched recently, 1 otherwise (missing
file, or a loop stuck for longer than WORKER_HEARTBEAT_MAX_AGE_SECONDS).
"""

import sys
import time
from pathlib import Path

from app.core.config import get_settings


def is_healthy(now: float | None = None) -> bool:
    settings = get_settings()
    heartbeat = Path(settings.worker_heartbeat_file)
    if not heartbeat.exists():
        return False
    age = (now or time.time()) - heartbeat.stat().st_mtime
    return age <= settings.worker_heartbeat_max_age_seconds


if __name__ == "__main__":
    sys.exit(0 if is_healthy() else 1)
