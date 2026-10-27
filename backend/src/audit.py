"""
Audit log (issue #18): one append-only table, admin_action_log.

Every entry has an actor (admin_id, "anonymous" or "system:<model_version>"),
an action, a category (AUDIT_CATEGORIES), an actor_type ("user" or "system"),
optional details (JSON text) and the request IP masked to its first two parts.
Rows are never updated or deleted: there is no endpoint for it, and a
PostgreSQL trigger (src.db.migrate_schema) rejects UPDATE, DELETE and TRUNCATE.

Details never hold phone numbers, national IDs or passwords.
"""

import ipaddress
import json
import uuid
from datetime import datetime, timedelta

from src.auth import Administrator
from src.db import AUDIT_CATEGORIES, AdminActionLog, get_session

ANONYMOUS = "anonymous"
MAX_LIMIT = 1000


def mask_ip(address):
    """IPv4 keeps its first two parts (10.20.*.*); IPv6 its first two groups (2001:db8:*)."""
    if not address:
        return None
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return "masked"
    if ip.version == 4:
        first, second = str(ip).split(".")[:2]
        return f"{first}.{second}.*.*"
    groups = ip.exploded.split(":")
    return f"{int(groups[0], 16):x}:{int(groups[1], 16):x}:*"


def record(db_session, actor, action, category, actor_type="user", target_agent_id=None, details=None,
           request_ip=None):
    """Adds one entry to db_session without committing (the caller commits it with the action it records)."""
    if category not in AUDIT_CATEGORIES:
        raise ValueError(f"category must be one of {AUDIT_CATEGORIES}, got {category!r}")
    entry = AdminActionLog(
        log_id=f"AL{uuid.uuid4().hex}", admin_id=actor, action=action, target_agent_id=target_agent_id,
        timestamp=datetime.utcnow(), category=category, actor_type=actor_type,
        details=json.dumps(details, sort_keys=True, default=str) if details is not None else None,
        request_ip=mask_ip(request_ip),
    )
    db_session.add(entry)
    return entry


def record_now(*args, **kwargs):
    """record() in its own session, committed at once."""
    db_session = get_session()
    try:
        record(db_session, *args, **kwargs)
        db_session.commit()
    finally:
        db_session.close()


def parse_day(value, name, end=False):
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{name} must be a date (YYYY-MM-DD) or ISO datetime") from None
    if end and len(value) == 10:
        return moment + timedelta(days=1)
    return moment


def filtered_query(db_session, args):
    """
    Audit entries matching the request filters, newest first. Filters:
    category, actor (exact admin_id), agent_id, date_from, date_to (a date
    includes that whole day). Raises ValueError on a bad filter.
    """
    query = db_session.query(AdminActionLog)
    category = args.get("category")
    if category:
        if category not in AUDIT_CATEGORIES:
            raise ValueError(f"category must be one of {list(AUDIT_CATEGORIES)}")
        query = query.filter(AdminActionLog.category == category)
    if args.get("actor"):
        # An account ID, or a username: the matching account's ID is searched too.
        actor = args["actor"].strip()
        ids = {actor} | {a for (a,) in db_session.query(Administrator.admin_id).filter(Administrator.username == actor)}
        query = query.filter(AdminActionLog.admin_id.in_(sorted(ids)))
    if args.get("agent_id"):
        query = query.filter(AdminActionLog.target_agent_id == args["agent_id"])
    if args.get("date_from"):
        query = query.filter(AdminActionLog.timestamp >= parse_day(args["date_from"], "date_from"))
    if args.get("date_to"):
        query = query.filter(AdminActionLog.timestamp < parse_day(args["date_to"], "date_to", end=True))
    return query.order_by(AdminActionLog.timestamp.desc(), AdminActionLog.log_id.desc())


def active_filters(args):
    return {k: args[k] for k in ("category", "actor", "agent_id", "date_from", "date_to") if args.get(k)}


# Actions that are only written when they happened, and actions that record a refusal or a failure.
SUCCESS_ACTIONS = {
    "login", "logout", "propose_decision", "withdraw_decision", "agree_decision", "overrule_decision", "confirm_decision",
    "correct_decision", "customer_viewed", "report_download", "role_change", "account_deactivated",
    "account_reactivated", "password_reset",
}
FAILED_ACTIONS = {"login_failure", "access_denied", "review_refused"}


def result_of(action, details):
    """"Success" or "Failed" where the entry says which, else "" (for example a flag change)."""
    if action in FAILED_ACTIONS:
        return "Failed"
    if action in SUCCESS_ACTIONS:
        return "Success"
    if action == "ai_detection_run" and isinstance(details, dict) and details.get("status") in ("succeeded", "failed"):
        return "Success" if details["status"] == "succeeded" else "Failed"
    return ""


def entry_payload(entry):
    return {
        "log_id": entry.log_id,
        "timestamp": entry.timestamp.isoformat(),
        "actor": entry.admin_id,
        "admin_id": entry.admin_id,
        "actor_type": entry.actor_type,
        "category": entry.category,
        "action": entry.action,
        "target_agent_id": entry.target_agent_id,
        "details": json.loads(entry.details) if entry.details else None,
        "request_ip": entry.request_ip,
    }
