"""
Account administration (issue #18), used by the admin-only API endpoints.

Rules:
- an admin cannot change the role of, or deactivate, their own account;
- the last active admin can never be demoted or deactivated. The active admin
  rows are locked (SELECT ... FOR UPDATE) before the check, so two admins
  removing each other at the same moment cannot leave the system with none.
"""

from werkzeug.security import generate_password_hash

from src.auth import ROLE_ADMIN, VALID_ROLES, Administrator, validate_password


class AccountError(Exception):
    def __init__(self, message, status):
        super().__init__(message)
        self.status = status


def account_payload(admin):
    return {"admin_id": admin.admin_id, "username": admin.username, "role": admin.role, "is_active": admin.is_active}


def list_accounts(db_session):
    return [account_payload(a) for a in db_session.query(Administrator).order_by(Administrator.username)]


def _target(db_session, actor_id, target_id):
    if actor_id == target_id:
        raise AccountError("Admins cannot change or deactivate their own account", 403)
    admin = db_session.query(Administrator).filter(Administrator.admin_id == target_id).with_for_update().first()
    if admin is None:
        raise AccountError("Account not found", 404)
    return admin


def _ensure_not_last_admin(db_session, target):
    active_admins = (db_session.query(Administrator)
                     .filter(Administrator.role == ROLE_ADMIN, Administrator.is_active.is_(True))
                     .with_for_update().all())
    if target.role == ROLE_ADMIN and target.is_active and len(active_admins) <= 1:
        raise AccountError("The last active admin cannot be demoted or deactivated", 409)


def change_role(db_session, actor_id, target_id, new_role):
    """Returns (account, old_role); the caller commits."""
    if new_role not in VALID_ROLES:
        raise AccountError(f"role must be one of {list(VALID_ROLES)}", 400)
    target = _target(db_session, actor_id, target_id)
    old_role = target.role
    if old_role == ROLE_ADMIN and new_role != ROLE_ADMIN:
        _ensure_not_last_admin(db_session, target)
    target.role = new_role
    return target, old_role


def find_account(db_session, account):
    """An account by admin_id, or else by username (row locked); AccountError 404 if neither matches."""
    query = db_session.query(Administrator).with_for_update()
    admin = query.filter(Administrator.admin_id == account).first() or query.filter(Administrator.username == account).first()
    if admin is None:
        raise AccountError("Account not found", 404)
    return admin


def reset_password(db_session, account, new_password):
    """
    Local recovery (#19): sets a new password with the creation rule and hashing; the caller commits.
    Accounts have no lockout or failed-attempt fields, so there is nothing else to clear.
    """
    try:
        validate_password(new_password)
    except ValueError as e:
        raise AccountError(str(e), 400) from None
    admin = find_account(db_session, account)
    admin.password_hash = generate_password_hash(new_password)
    return admin


def set_active(db_session, actor_id, target_id, active):
    """Returns (account, was_active); the caller commits."""
    target = _target(db_session, actor_id, target_id)
    was_active = target.is_active
    if not active:
        _ensure_not_last_admin(db_session, target)
    target.is_active = active
    return target, was_active
