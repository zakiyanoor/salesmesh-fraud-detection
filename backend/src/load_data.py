"""
Loads the v3 synthetic data into PostgreSQL (issue #4).

Reads exactly five files from ml/data/synthetic: clients, agents, agent_identity,
agent_categories and activation_records. It never reads labels.csv or rings.csv
(ground truth, evaluation only), nor any other file in that folder.

The reload is idempotent and runs in one transaction:
1. each file's sha256 must match ml/results/FREEZE.md (the frozen v3 data);
2. row counts must match EXPECTED_COUNTS, checked on the files and again in
   the database before commit; any mismatch raises DataLoadError and rolls back;
3. rows are upserted (INSERT ... ON CONFLICT DO UPDATE);
4. rows no longer in the files (for example the v2 agents) are removed with
   their derived rows. If that would delete review decisions, the load stops
   unless allow_deleting_reviews is set;
5. a data_loads row records the hashes and counts. A second run with the same
   files finds nothing to change and reports "unchanged".

Usage (from backend/): python -m src.load_data [--force]
"""

import argparse
import hashlib
import re
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import delete, func, select, text
from sqlalchemy.dialects.postgresql import insert

from src.db import (
    ActivationRecord, Agent, AgentCategory, AgentIdentity, AgentScore, Client, DataLoad, DuplicateEvidence,
    FeatureVector, FraudFlag, ReviewDecision, create_all_tables, engine,
)

ML_DIR = Path(__file__).resolve().parents[2] / "ml"
SYNTHETIC_DATA_DIR = ML_DIR / "data" / "synthetic"
FREEZE_PATH = ML_DIR / "results" / "FREEZE.md"
DATA_FILES = {
    "clients": "clients.csv",
    "agents": "agents.csv",
    "agent_identity": "agent_identity.csv",
    "agent_categories": "agent_categories.csv",
    "activation_records": "activation_records.csv",
}
FORBIDDEN_FILES = {"labels.csv", "rings.csv"}
EXPECTED_COUNTS = {
    "agents": 1000, "activation_records": 135494, "clients": 20, "categories": 12,
    "agent_identity": 1000, "agent_categories": 1441,
}
CHUNK = 5000
STRING_COLUMNS = {"agent_id", "client_id", "customer_id", "record_id", "phone_number", "national_id_number"}


class DataLoadError(RuntimeError):
    pass


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def frozen_hashes(freeze_path=FREEZE_PATH):
    rows = re.findall(r"^\| [^|]+ \| `data/synthetic/([^`]+)` \| `([0-9a-f]{64})` \|$",
                      Path(freeze_path).read_text(encoding="utf-8"), flags=re.M)
    return dict(rows)


def read_files(data_dir=SYNTHETIC_DATA_DIR):
    frames = {}
    for table, name in DATA_FILES.items():
        if name in FORBIDDEN_FILES:
            raise DataLoadError(f"{name} holds ground truth and is never loaded")
        path = Path(data_dir) / name
        header = pd.read_csv(path, nrows=0).columns
        frames[table] = pd.read_csv(path, dtype={c: str for c in header if c in STRING_COLUMNS}, keep_default_na=False)
    return frames


def file_counts(frames):
    return {
        "agents": len(frames["agents"]), "activation_records": len(frames["activation_records"]),
        "clients": len(frames["clients"]), "categories": int(frames["clients"]["category"].nunique()),
        "agent_identity": len(frames["agent_identity"]), "agent_categories": len(frames["agent_categories"]),
    }


def database_counts(conn):
    count = lambda model: conn.execute(select(func.count()).select_from(model)).scalar()  # noqa: E731
    return {
        "agents": count(Agent), "activation_records": count(ActivationRecord), "clients": count(Client),
        "categories": conn.execute(select(func.count(func.distinct(Client.category)))).scalar(),
        "agent_identity": count(AgentIdentity), "agent_categories": count(AgentCategory),
    }


def check_counts(counts, where, expected=EXPECTED_COUNTS):
    wrong = {k: (counts.get(k), v) for k, v in expected.items() if counts.get(k) != v}
    if wrong:
        raise DataLoadError(f"row counts in the {where} do not match (got, expected): {wrong}")


def records(frame, columns, timestamps=()):
    df = frame[list(columns)].copy()
    for column in timestamps:
        df[column] = pd.to_datetime(df[column]).dt.to_pydatetime()
    return df.astype(object).to_dict("records")


def upsert(conn, model, rows, keys):
    table = model.__table__
    for start in range(0, len(rows), CHUNK):
        statement = insert(table).values(rows[start:start + CHUNK])
        update = {c.name: statement.excluded[c.name] for c in table.columns if c.name not in keys}
        conn.execute(statement.on_conflict_do_update(index_elements=list(keys), set_=update))


def remove_stale(conn, frames, allow_deleting_reviews=False):
    """Deletes rows that are not in the files, with the rows derived from them. Returns counts."""
    conn.execute(text("CREATE TEMP TABLE keep_agents (agent_id VARCHAR PRIMARY KEY) ON COMMIT DROP"))
    conn.execute(text("CREATE TEMP TABLE keep_records (record_id VARCHAR PRIMARY KEY) ON COMMIT DROP"))
    conn.execute(text("INSERT INTO keep_agents VALUES (:a)"), [{"a": a} for a in frames["agents"]["agent_id"]])
    conn.execute(text("INSERT INTO keep_records VALUES (:r)"),
                 [{"r": r} for r in frames["activation_records"]["record_id"]])
    stale = "SELECT agent_id FROM agents WHERE agent_id NOT IN (SELECT agent_id FROM keep_agents)"
    stale_vectors = f"SELECT vector_id FROM feature_vectors WHERE agent_id IN ({stale})"
    stale_flags = f"SELECT flag_id FROM fraud_flags WHERE vector_id IN ({stale_vectors})"
    reviews = conn.execute(text(f"SELECT count(*) FROM review_decisions WHERE flag_id IN ({stale_flags})")).scalar()
    if reviews and not allow_deleting_reviews:
        raise DataLoadError(f"{reviews} review decisions belong to agents not in the new data; "
                            "rerun with allow_deleting_reviews to delete them")
    removed = {"review_decisions": reviews}
    if reviews:
        # Issue #28: review rows are write once; only this explicitly allowed path may delete them.
        conn.execute(text("SET LOCAL salesmesh.review_maintenance = 'on'"))
    stale_decisions = f"SELECT decision_id FROM review_decisions WHERE flag_id IN ({stale_flags})"
    statements = [
        ("review_corrections", f"DELETE FROM review_corrections WHERE decision_id IN ({stale_decisions})"),
        ("review_decisions", f"DELETE FROM review_decisions WHERE flag_id IN ({stale_flags})"),
        ("fraud_flags", f"DELETE FROM fraud_flags WHERE vector_id IN ({stale_vectors})"),
        ("feature_vectors", f"DELETE FROM feature_vectors WHERE agent_id IN ({stale})"),
        ("agent_scores", f"DELETE FROM agent_scores WHERE agent_id IN ({stale})"),
        ("duplicate_evidence", f"DELETE FROM duplicate_evidence WHERE agent_id IN ({stale})"),
        ("activation_records", "DELETE FROM activation_records WHERE record_id NOT IN (SELECT record_id FROM keep_records)"),
        ("agent_identity", f"DELETE FROM agent_identity WHERE agent_id IN ({stale})"),
        ("agent_categories", f"DELETE FROM agent_categories WHERE agent_id IN ({stale})"),
        ("agents", "DELETE FROM agents WHERE agent_id NOT IN (SELECT agent_id FROM keep_agents)"),
    ]
    for name, sql in statements:
        removed[name] = conn.execute(text(sql)).rowcount
    keep_categories = set(zip(frames["agent_categories"]["agent_id"], frames["agent_categories"]["category"]))
    existing = conn.execute(select(AgentCategory.agent_id, AgentCategory.category)).all()
    gone = [{"a": a, "c": c} for a, c in existing if (a, c) not in keep_categories]
    if gone:
        conn.execute(text("DELETE FROM agent_categories WHERE agent_id = :a AND category = :c"), gone)
    removed["agent_categories"] += len(gone)
    removed["clients"] = conn.execute(
        delete(Client).where(Client.client_id.not_in(list(frames["clients"]["client_id"])))).rowcount
    return removed


def load_all(data_dir=SYNTHETIC_DATA_DIR, force=False, verify_hashes=True, allow_deleting_reviews=False,
             expected=EXPECTED_COUNTS):
    """Reloads the five files; returns a report dict. Raises DataLoadError on any mismatch."""
    data_dir = Path(data_dir)
    hashes = {name: file_sha256(data_dir / name) for name in DATA_FILES.values()}
    if verify_hashes:
        frozen = frozen_hashes()
        wrong = [n for n, h in hashes.items() if frozen.get(n) != h]
        if wrong:
            raise DataLoadError(f"files differ from the frozen v3 data in ml/results/FREEZE.md: {wrong}")
    frames = read_files(data_dir)
    counts = file_counts(frames)
    check_counts(counts, "files", expected)
    create_all_tables()

    with engine.begin() as conn:
        last = conn.execute(select(DataLoad).order_by(DataLoad.loaded_at.desc()).limit(1)).first()
        if not force and last is not None and last.file_hashes == hashes and database_counts(conn) == counts:
            return {"status": "unchanged", "counts": counts, "load_id": last.load_id}

        upsert(conn, Client, records(frames["clients"], ["client_id", "name", "category", "commission_per_activation_kes"]),
               ["client_id"])
        upsert(conn, Agent, records(frames["agents"], ["agent_id", "registration_timestamp", "region", "account_status"],
                                    ["registration_timestamp"]), ["agent_id"])
        upsert(conn, AgentIdentity, records(frames["agent_identity"],
                                            ["agent_id", "full_name", "phone_number", "national_id_number"]), ["agent_id"])
        upsert(conn, AgentCategory, records(frames["agent_categories"],
                                            ["agent_id", "category", "certification_status", "certified_at"],
                                            ["certified_at"]), ["agent_id", "category"])
        upsert(conn, ActivationRecord, records(frames["activation_records"],
                                               ["record_id", "agent_id", "timestamp", "customer_id", "activation_status",
                                                "client_id", "category", "quality_score", "commission_kes"],
                                               ["timestamp"]), ["record_id"])
        removed = remove_stale(conn, frames, allow_deleting_reviews)
        in_db = database_counts(conn)
        check_counts(in_db, "database after loading", expected)
        load_id = f"DL{uuid.uuid4().hex[:12]}"
        conn.execute(insert(DataLoad).values(load_id=load_id, loaded_at=datetime.utcnow(),
                                             file_hashes=hashes, row_counts=in_db))
    return {"status": "loaded", "counts": in_db, "removed": removed, "load_id": load_id}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Reload the five v3 data files into PostgreSQL.")
    parser.add_argument("--force", action="store_true", help="reload even if the same files were loaded last")
    parser.add_argument("--allow-deleting-reviews", action="store_true")
    args = parser.parse_args(argv)
    report = load_all(force=args.force, allow_deleting_reviews=args.allow_deleting_reviews)
    print(f"Load {report['status']} ({report['load_id']}).")
    for table, n in report["counts"].items():
        print(f"  {table:20s} {n}")
    for table, n in report.get("removed", {}).items():
        if n:
            print(f"  removed {n} stale rows from {table}")


if __name__ == "__main__":
    main()
