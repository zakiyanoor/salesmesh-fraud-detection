"""
Authentication module for the SalesMesh fraud detection system.

Implements FR-01 (login before accessing dashboard functions) and NFR-02
(only authenticated users access protected routes), per Deliverable 3.6.2:
username/password authentication with hashed password storage, session
management, and role-based access control.

Adds the Administrator entity (not explicitly in the original ERD, but
required to support login), a login_required decorator that protects any
Flask route it is applied to, and a role_required decorator that further
restricts a route to one role.

Roles:
  fraud_analyst       -> proposes review decisions
  compliance_officer  -> confirms review decisions proposed by someone else
"""

from functools import wraps
from flask import g, session, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Boolean, Column, String, true
from sqlalchemy.orm import validates
from src.db import Base, get_session, engine

ROLE_FRAUD_ANALYST = "fraud_analyst"
ROLE_COMPLIANCE_OFFICER = "compliance_officer"
# Issue #18: administers accounts, reads the audit log and downloads reports;
# never proposes or confirms review decisions (separation of duties).
ROLE_ADMIN = "admin"
VALID_ROLES = (ROLE_FRAUD_ANALYST, ROLE_COMPLIANCE_OFFICER, ROLE_ADMIN)
DEACTIVATED = "Account is deactivated"

MIN_PASSWORD_LENGTH = 12


class Administrator(Base):
    __tablename__ = "administrators"

    admin_id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default=true())

    @validates("role")
    def validate_role(self, key, value):
        if value not in VALID_ROLES:
            raise ValueError(f"role must be one of {VALID_ROLES}, got {value!r}")
        return value


def create_admin_table():
    """Creates the administrators table if it does not already exist."""
    Base.metadata.create_all(engine, tables=[Administrator.__table__])
    print("Administrators table created successfully.")


def validate_password(password):
    """The password rule for new accounts and password resets; raises ValueError."""
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long")


def create_admin_user(admin_id, username, password, role):
    validate_password(password)

    db_session = get_session()
    try:
        existing = db_session.query(Administrator).filter(Administrator.username == username).first()
        if existing:
            print(f"Username '{username}' already exists.")
            return

        admin = Administrator(
            admin_id=admin_id,
            username=username,
            password_hash=generate_password_hash(password),
            role=role,
        )
        db_session.add(admin)
        db_session.commit()
        print(f"Administrator '{username}' ({role}) created successfully.")
    finally:
        db_session.close()


def verify_login(username, password):
    """The account dict (with is_active) if the password matches, else None."""
    db_session = get_session()
    try:
        admin = db_session.query(Administrator).filter(Administrator.username == username).first()
        if admin and check_password_hash(admin.password_hash, password):
            return {"admin_id": admin.admin_id, "username": admin.username, "role": admin.role,
                    "is_active": admin.is_active}
        return None
    finally:
        db_session.close()


def refresh_session():
    """
    Re-reads the logged-in account on every request, so a deactivation or role
    change takes effect at once. Returns an error response, or None if the
    session is valid (and session["role"] is current).
    """
    if "admin_id" not in session:
        return jsonify({"error": "Authentication required"}), 401
    db_session = get_session()
    try:
        admin = db_session.get(Administrator, session["admin_id"])
        if admin is None or not admin.is_active:
            # For this request's access_denied audit entry; the session itself is cleared.
            g.denied_admin_id, g.denied_role = session.get("admin_id"), session.get("role")
            session.clear()
            return jsonify({"error": DEACTIVATED if admin is not None else "Authentication required"}), 401
        session["role"] = admin.role
        if admin.role not in VALID_ROLES:
            # A legacy or hand-edited account whose role no longer exists gets no access at all.
            return jsonify({"error": f"Unknown role {admin.role!r}; an admin must assign a valid role"}), 403
        return None
    finally:
        db_session.close()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        denied = refresh_session()
        return denied if denied is not None else f(*args, **kwargs)
    return decorated


def role_required(*roles):
    """
    Restricts a route to accounts with one of the given roles.

    Returns 401 if nobody is logged in or the account is deactivated (same as
    login_required, so it can be used on its own) and 403 for any other role.
    """
    if not roles or any(role not in VALID_ROLES for role in roles):
        raise ValueError(f"roles must be from {VALID_ROLES}, got {roles!r}")
    message = (f"This action requires the '{roles[0]}' role" if len(roles) == 1
               else f"This action requires one of the roles: {', '.join(roles)}")

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            denied = refresh_session()
            if denied is not None:
                return denied
            if session.get("role") not in roles:
                return jsonify({"error": message}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


# Demo and test accounts (issue #26): development and test only, passwords from the environment.
DEMO_ACCOUNTS = (
    ("ADM_ANALYST_01", "analyst_01", ROLE_FRAUD_ANALYST, "DEMO_ANALYST_PASSWORD"),
    ("ADM_COMPLIANCE_01", "compliance_01", ROLE_COMPLIANCE_OFFICER, "DEMO_COMPLIANCE_PASSWORD"),
    ("ADM_ADMIN_01", "admin_01", ROLE_ADMIN, "DEMO_ADMIN_PASSWORD"),
)
DEMO_APP_ENVS = ("development", "test")


def seed_demo_accounts(environ):
    """
    Creates analyst_01, compliance_01 and admin_01 (existing usernames are left as they are).
    Refused unless APP_ENV is development or test; each password comes from its DEMO_*_PASSWORD
    variable and must meet validate_password. Checks everything before creating anything.
    """
    app_env = environ.get("APP_ENV", "production").strip().lower()
    if app_env not in DEMO_APP_ENVS:
        raise RuntimeError(f"Demo accounts are for development and test only; APP_ENV is {app_env!r}")
    missing = [variable for *_, variable in DEMO_ACCOUNTS if not environ.get(variable)]
    if missing:
        raise RuntimeError(f"Set {', '.join(missing)} (in backend/.env) before creating the demo accounts")
    for *_, variable in DEMO_ACCOUNTS:
        try:
            validate_password(environ[variable])
        except ValueError as error:
            raise RuntimeError(f"{variable}: {error}") from None
    create_admin_table()
    for admin_id, username, role, variable in DEMO_ACCOUNTS:
        create_admin_user(admin_id=admin_id, username=username, password=environ[variable], role=role)


if __name__ == "__main__":
    import os
    import sys

    try:
        seed_demo_accounts(os.environ)
    except RuntimeError as error:
        sys.exit(str(error))
