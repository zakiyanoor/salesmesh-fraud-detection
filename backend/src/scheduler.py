from __future__ import annotations
from apscheduler.schedulers.blocking import BlockingScheduler
from src.pipeline import run_detection_cycle

DETECTION_INTERVAL_HOURS = 24


def scheduled_job() -> None:
    result = run_detection_cycle()
    print(f"Detection cycle complete: {result}")


if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(scheduled_job, "interval", hours=DETECTION_INTERVAL_HOURS, next_run_time=None)
    print(f"Scheduler started. Detection cycle runs every {DETECTION_INTERVAL_HOURS}h.")
    scheduler.start()