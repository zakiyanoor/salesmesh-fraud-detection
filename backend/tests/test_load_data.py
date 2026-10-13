"""Loader (issue #4): the five v3 files only, never labels; loud failures; idempotent reload; safe migration."""

import inspect
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine, inspect as sa_inspect, text

from src import load_data
from src.load_data import DATA_FILES, DataLoadError, EXPECTED_COUNTS

BACKEND = Path(__file__).resolve().parents[1]
TEST_DB = "salesmesh_fraud_detection_test"


def run_module(module, *args):
    env = {**os.environ, "DB_NAME": TEST_DB}
    return subprocess.run([sys.executable, "-m", module, *args], cwd=BACKEND, env=env,
                          capture_output=True, text=True, timeout=600)


def make_test_db_engine():
    from src.db import DB_HOST, DB_PASSWORD, DB_PORT, DB_USER

    return create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TEST_DB}")


def test_loader_reads_exactly_the_five_named_files(monkeypatch):
    opened = []
    real = pd.read_csv

    def spy(path, *args, **kwargs):
        opened.append(Path(path).name)
        return real(path, *args, **kwargs)

    monkeypatch.setattr(load_data.pd, "read_csv", spy)
    frames = load_data.read_files()
    assert set(opened) == set(DATA_FILES.values())
    assert set(frames) == set(DATA_FILES)
    assert load_data.file_counts(frames) == EXPECTED_COUNTS


def test_labels_and_rings_are_never_loaded(monkeypatch):
    assert not {"labels.csv", "rings.csv"} & set(DATA_FILES.values())
    monkeypatch.setitem(load_data.DATA_FILES, "labels", "labels.csv")
    with pytest.raises(DataLoadError, match="never loaded"):
        load_data.read_files()
    source = inspect.getsource(load_data)
    assert source.count('"labels.csv"') == 1 and source.count('"rings.csv"') == 1  # FORBIDDEN_FILES only


def test_identity_numbers_keep_their_digits_as_text():
    identity = load_data.read_files()["agent_identity"]
    assert identity["phone_number"].str.fullmatch(r"\+2547\d{8}").all()
    assert identity["national_id_number"].str.fullmatch(r"\d{8}").all()


def test_count_mismatch_fails_loudly_before_touching_the_database():
    wrong = {**EXPECTED_COUNTS, "agents": 999}
    with pytest.raises(DataLoadError, match="agents"):
        load_data.load_all(expected=wrong)


def test_changed_file_fails_the_frozen_hash_check(tmp_path):
    for name in DATA_FILES.values():
        shutil.copy(load_data.SYNTHETIC_DATA_DIR / name, tmp_path / name)
    with open(tmp_path / "clients.csv", "a", encoding="utf-8") as f:
        f.write("CL99,Client 99,banking,250\n")
    with pytest.raises(DataLoadError, match="FREEZE"):
        load_data.load_all(data_dir=tmp_path)


def test_migration_is_safe_to_run_twice():
    for _ in range(2):
        result = run_module("src.migrate")
        assert result.returncode == 0, result.stderr
    engine = make_test_db_engine()
    try:
        columns = {t: {c["name"] for c in sa_inspect(engine).get_columns(t)} for t in
                   ["agents", "activation_records", "clients", "agent_identity", "agent_categories",
                    "agent_scores", "duplicate_evidence", "detection_runs", "data_loads"]}
    finally:
        engine.dispose()
    assert "account_status" in columns["agents"]
    assert {"quality_score", "commission_kes", "client_id", "category"} <= columns["activation_records"]
    assert "commission_per_activation_kes" in columns["clients"]
    assert {"run_id", "anomaly_score", "flagged", "flag_source", "reasons", "created_at"} <= columns["agent_scores"]
    assert {"customer_id", "client_id", "other_agent_id", "reason", "record_ids"} <= columns["duplicate_evidence"]


def test_reload_is_idempotent_and_reports_counts():
    first = run_module("src.load_data")
    assert first.returncode == 0, first.stderr
    second = run_module("src.load_data")
    assert second.returncode == 0, second.stderr
    assert "Load unchanged" in second.stdout
    forced = run_module("src.load_data", "--force")
    assert forced.returncode == 0, forced.stderr
    assert "Load loaded" in forced.stdout
    for line in ["agents               1000", "activation_records   135494", "clients              20",
                 "categories           12"]:
        assert line in forced.stdout
    engine = make_test_db_engine()
    try:
        with engine.connect() as conn:
            assert conn.execute(text("SELECT count(*) FROM agents")).scalar() == 1000
            assert conn.execute(text("SELECT count(*) FROM activation_records")).scalar() == 135494
            assert conn.execute(text("SELECT count(DISTINCT record_id) FROM activation_records")).scalar() == 135494
            assert conn.execute(text("SELECT count(*) FROM agents WHERE length(agent_id) <> 6")).scalar() == 0
    finally:
        engine.dispose()
