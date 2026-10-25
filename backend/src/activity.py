"""
Daily activity for one agent (issue #28): activations per day of the data window, how many completed,
the days that hold a record in this agent's duplicate evidence for the latest run, and activations per
hour of day.

- The data window runs from the first to the last day in activation_records (all agents), so every agent's
  table covers the same days.
- Days and hours are as recorded in the data (naive local timestamps); nothing is converted.
- The flag belongs to the agent for the whole run, so no day is called flagged; a day only says whether it
  holds duplicate evidence.
- No customer IDs and no identity data. Read only, counted in SQL on the agent_id index.
"""

from datetime import timedelta

from sqlalchemy import text

from src.db import DuplicateEvidence

HOURS = range(24)


def data_window(db_session):
    """(first_day, last_day) of all activation records, or (None, None) when there are none."""
    first, last = db_session.execute(text("SELECT min(timestamp), max(timestamp) FROM activation_records")).one()
    return (first.date(), last.date()) if first else (None, None)


def evidence_days(db_session, run, agent_id):
    """The days that hold at least one record in the agent's duplicate evidence for the run."""
    if run is None:
        return set()
    record_ids = set()
    for (ids,) in db_session.query(DuplicateEvidence.record_ids).filter(
            DuplicateEvidence.run_id == run.run_id, DuplicateEvidence.agent_id == agent_id):
        record_ids.update(i for i in ids.split(",") if i)
    if not record_ids:
        return set()
    rows = db_session.execute(text(
        "SELECT DISTINCT CAST(timestamp AS date) FROM activation_records "
        "WHERE agent_id = :a AND record_id = ANY(:ids)"), {"a": agent_id, "ids": sorted(record_ids)})
    return {d for (d,) in rows}


def agent_activity(db_session, run, agent_id):
    first, last = data_window(db_session)
    per_day = {d: (n, c) for d, n, c in db_session.execute(text(
        "SELECT CAST(timestamp AS date), count(*), count(*) FILTER (WHERE activation_status = 'completed') "
        "FROM activation_records WHERE agent_id = :a GROUP BY 1"), {"a": agent_id})}
    per_hour = dict(db_session.execute(text(
        "SELECT CAST(extract(hour FROM timestamp) AS integer), count(*) FROM activation_records "
        "WHERE agent_id = :a GROUP BY 1"), {"a": agent_id}).all())
    marked = evidence_days(db_session, run, agent_id)

    days = []
    if first is not None:
        day = first
        while day <= last:
            activations, completed = per_day.get(day, (0, 0))
            days.append({"date": day.isoformat(), "activations": activations, "completed": completed,
                         "duplicate_evidence": day in marked})
            day += timedelta(days=1)
    return {
        "agent_id": agent_id,
        "run_id": run.run_id if run else None,
        "first_day": first.isoformat() if first else None,
        "last_day": last.isoformat() if last else None,
        "days": days,
        "hours": [{"hour": h, "activations": int(per_hour.get(h, 0))} for h in HOURS],
        "totals": {"activations": sum(n for n, _ in per_day.values()),
                   "completed": sum(c for _, c in per_day.values())},
        "note": "Days and hours are as recorded in the data.",
    }
