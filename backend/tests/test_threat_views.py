"""Threat intelligence views computed once per detection run and stored in threat_views (issue #28)."""

from sqlalchemy import inspect

from src.db import engine, migrate_schema


def test_threat_views_table_has_the_expected_columns_and_key(database) -> None:
    migrate_schema()  # idempotent: a second run on an existing table changes nothing
    table = inspect(engine)
    columns = {c["name"]: c for c in table.get_columns("threat_views")}
    assert set(columns) == {"run_id", "view", "view_version", "payload", "created_at"}
    assert not any(c["nullable"] for c in columns.values())
    assert table.get_pk_constraint("threat_views")["constrained_columns"] == ["run_id", "view"]
    assert [fk["referred_table"] for fk in table.get_foreign_keys("threat_views")] == ["detection_runs"]
