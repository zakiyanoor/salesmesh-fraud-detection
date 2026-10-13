"""Scheduler (issue #12): the job is scheduled (not paused), actually executes, and its status is reported."""

import threading
import time
from datetime import datetime

import pytest
from apscheduler.schedulers.background import BackgroundScheduler

from src import ml_bridge, scheduler as scheduler_module
from src.db import DetectionRun, get_session
from src.scheduler import JOB_ID, build_scheduler, interval_minutes
from tests.helpers import ANALYST, login


def test_job_is_scheduled_with_a_first_run_time_not_paused() -> None:
    scheduler = build_scheduler(BackgroundScheduler, minutes=60, start_now=True, job=lambda: None)
    scheduler.start(paused=True)
    try:
        job = scheduler.get_job(JOB_ID)
        assert job.next_run_time is not None
        assert job.trigger.interval.total_seconds() == 3600
        assert job.max_instances == 1 and job.coalesce
    finally:
        scheduler.shutdown(wait=False)


def test_interval_comes_from_the_environment(monkeypatch) -> None:
    monkeypatch.setenv("DETECTION_INTERVAL_MINUTES", "15")
    assert interval_minutes() == 15
    scheduler = build_scheduler(BackgroundScheduler, start_now=False, job=lambda: None)
    scheduler.start(paused=True)
    try:
        job = scheduler.get_job(JOB_ID)
        assert job.trigger.interval.total_seconds() == 900
        assert (job.next_run_time - datetime.now().astimezone()).total_seconds() > 800
    finally:
        scheduler.shutdown(wait=False)
    for bad in ("0", "-5", "soon"):
        monkeypatch.setenv("DETECTION_INTERVAL_MINUTES", bad)
        with pytest.raises(ValueError):
            interval_minutes()


def test_scheduler_executes_a_job() -> None:
    ran = threading.Event()
    scheduler = build_scheduler(BackgroundScheduler, minutes=60, start_now=True, job=ran.set)
    scheduler.start()
    try:
        assert ran.wait(timeout=15), "the scheduled job never ran"
    finally:
        scheduler.shutdown(wait=False)


def latest_run():
    db_session = get_session()
    try:
        return db_session.query(DetectionRun).order_by(DetectionRun.started_at.desc()).first()
    finally:
        db_session.close()


def test_scheduler_runs_the_real_detection_job_and_records_it(database, client) -> None:
    started = datetime.utcnow()
    scheduler = build_scheduler(BackgroundScheduler, minutes=60, start_now=True)
    scheduler.start()
    try:
        deadline = time.time() + 180
        run = None
        while time.time() < deadline:
            run = latest_run()
            if run and run.started_at >= started and run.trigger == "scheduler" and run.status != "running":
                break
            time.sleep(1)
    finally:
        scheduler.shutdown(wait=True)
    assert run is not None and run.trigger == "scheduler" and run.started_at >= started, "no scheduler run recorded"
    assert run.status == "succeeded", run.error
    assert run.agents_scored == 1000 and run.flagged_count == database["flagged"]

    login(client, ANALYST)
    body = client.get("/api/detection-runs/latest").get_json()["run"]
    assert body["run_id"] == run.run_id and body["status"] == "succeeded"
    assert body["agents_scored"] == 1000 and body["flagged_count"] == run.flagged_count
    assert body["started_at"] and body["finished_at"] and body["error"] is None


def test_failed_run_reports_its_error_and_the_scheduler_survives(client, monkeypatch) -> None:
    def broken():
        raise RuntimeError("bundle unavailable (test)")

    monkeypatch.setattr(ml_bridge, "load_frozen_bundle", broken)
    assert scheduler_module.scheduled_job() is None
    run = latest_run()
    assert run.status == "failed" and "bundle unavailable (test)" in run.error and run.finished_at

    login(client, ANALYST)
    body = client.get("/api/detection-runs/latest").get_json()["run"]
    assert body["status"] == "failed" and "bundle unavailable (test)" in body["error"]


def test_status_endpoint_requires_login(client) -> None:
    assert client.get("/api/detection-runs/latest").status_code == 401
