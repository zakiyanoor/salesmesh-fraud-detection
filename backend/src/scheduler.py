"""
Detection scheduler (issue #12).

The old job was added with next_run_time=None, which APScheduler treats as
"paused": it was registered but never ran. build_scheduler() adds the job with
a real first run time (now, unless DETECTION_RUN_ON_START=false, in which case
after one interval), max_instances=1 and coalesce=True so runs never overlap
or pile up.

Settings (environment):
  DETECTION_INTERVAL_MINUTES  minutes between runs (default 1440, one day)
  DETECTION_RUN_ON_START      run once immediately on start (default true)

Every run writes a detection_runs row (running, then succeeded or failed with
the error), which GET /api/detection-runs/latest reports. A failed run is
logged and the scheduler keeps going.

Usage (from backend/): python -m src.scheduler
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.util import undefined

from src.scoring_service import run_detection_cycle

DEFAULT_INTERVAL_MINUTES = 1440
JOB_ID = "detection_cycle"
log = logging.getLogger(__name__)


def interval_minutes() -> float:
    value = os.getenv("DETECTION_INTERVAL_MINUTES", str(DEFAULT_INTERVAL_MINUTES))
    try:
        minutes = float(value)
    except ValueError:
        raise ValueError(f"DETECTION_INTERVAL_MINUTES must be a number, got {value!r}") from None
    if minutes <= 0:
        raise ValueError(f"DETECTION_INTERVAL_MINUTES must be positive, got {value!r}")
    return minutes


def run_on_start() -> bool:
    return os.getenv("DETECTION_RUN_ON_START", "true").strip().lower() not in ("0", "false", "no")


def scheduled_job() -> dict | None:
    try:
        result = run_detection_cycle(trigger="scheduler")
        log.info("Detection cycle complete: %s", result)
        return result
    except Exception:
        log.exception("Detection cycle failed; the error is stored on its detection_runs row")
        return None


def build_scheduler(scheduler_cls=BlockingScheduler, minutes: float | None = None, start_now: bool | None = None,
                    job=scheduled_job):
    minutes = interval_minutes() if minutes is None else minutes
    start_now = run_on_start() if start_now is None else start_now
    scheduler = scheduler_cls()
    scheduler.add_job(job, "interval", minutes=minutes, id=JOB_ID, replace_existing=True, max_instances=1,
                      coalesce=True, next_run_time=datetime.now().astimezone() if start_now else undefined)
    return scheduler


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    scheduler = build_scheduler()
    print(f"Scheduler started: detection cycle every {interval_minutes():g} min"
          f"{', first run now' if run_on_start() else ''}.")
    scheduler.start()
