"""
Account administration from the command line (issue #18), through the same
accounts service and rules as the API, audited the same way (category admin,
with "channel": "cli"). The acting account must be an active admin and
authenticates with its password.

Usage (from backend/):
  python -m src.manage_accounts deactivate ADM001 --as admin_01
  python -m src.manage_accounts reactivate ADM001 --as admin_01
  python -m src.manage_accounts role ADM001 fraud_analyst --as admin_01
The password is read from the environment variable named by --password-env,
or prompted for.

First administrator (issue #20), on a new database with no admin account yet:
  python -m src.manage_accounts create-admin <username> --password-env ADMIN_PASSWORD
It refuses once any admin account exists. The password is read from the named
environment variable, checked by the same rule as every account, never printed,
and the creation is audited without it.

Local recovery (issue #19), for a forgotten password:
  python -m src.manage_accounts reset-password <admin_id or username> --new-password-env NEW_PASSWORD
It needs no admin password because it only works with direct access to the
database (the .env credentials on the server); anyone who can run it could
already change the database. The new password comes from the named
environment variable, is never printed, and the reset is audited without it.
"""

import argparse
import getpass
import os
import uuid

from sqlalchemy import text
from werkzeug.security import generate_password_hash

from src import accounts, audit
from src.auth import MIN_PASSWORD_LENGTH, ROLE_ADMIN, Administrator, create_admin_table, validate_password, verify_login
from src.db import get_session

RECOVERY_HELP = (
    "Local recovery for a forgotten password. Runs with direct database access on the server (the .env "
    "database credentials), so it does not need an admin password: anyone who can run it can already change "
    "the database. The new password is read from the environment variable named by --new-password-env, never "
    f"from the command line, and is never printed. It must be at least {MIN_PASSWORD_LENGTH} characters. "
    "The reset is written to the audit log (action password_reset, channel \"local recovery\") without the password."
)


class CommandError(RuntimeError):
    pass


def acting_admin(username, password):
    admin = verify_login(username, password)
    if admin is None:
        raise CommandError("invalid username or password")
    if not admin["is_active"] or admin["role"] != ROLE_ADMIN:
        raise CommandError("the acting account must be an active admin")
    return admin


def run(action, target_id, actor, new_role=None):
    """Applies one change as `actor` (dict from acting_admin); returns (changed, account payload)."""
    db_session = get_session()
    try:
        if action == "role":
            account, old_role = accounts.change_role(db_session, actor["admin_id"], target_id, new_role)
            change = None if old_role == account.role else {"old_role": old_role, "new_role": account.role}
            name = "role_change"
        else:
            active = action == "reactivate"
            account, was_active = accounts.set_active(db_session, actor["admin_id"], target_id, active)
            change = None if was_active == active else {"role": account.role}
            name = "account_reactivated" if active else "account_deactivated"
        if change is None:
            db_session.rollback()
            return False, accounts.account_payload(account)
        audit.record(db_session, actor["admin_id"], name, "admin", details={
            "target_admin_id": account.admin_id, "target_username": account.username, "channel": "cli", **change})
        payload = accounts.account_payload(account)
        db_session.commit()
        return True, payload
    except Exception:
        db_session.rollback()
        raise
    finally:
        db_session.close()


def local_actor():
    """The audit actor for a local recovery: the operating-system user who ran it."""
    try:
        return f"local:{getpass.getuser()}"
    except Exception:
        return "local:unknown"


def reset_password(account, new_password):
    """Local recovery: new password and its audit entry in one transaction; returns the account payload."""
    db_session = get_session()
    try:
        admin = accounts.reset_password(db_session, account, new_password)
        audit.record(db_session, local_actor(), "password_reset", "admin", details={
            "target_admin_id": admin.admin_id, "target_username": admin.username, "channel": "local recovery"})
        payload = accounts.account_payload(admin)
        db_session.commit()
        return payload
    except Exception:
        db_session.rollback()
        raise
    finally:
        db_session.close()


def create_first_admin(username, password, admin_id=None):
    """
    Creates the first admin account and its audit entry in one transaction; returns the account payload.
    The table lock makes two concurrent runs safe: the second one sees the first admin and is refused.
    """
    username = (username or "").strip()
    if not username or len(username) > 100:
        raise CommandError("the username must be 1 to 100 characters")
    try:
        validate_password(password)
    except ValueError as e:
        raise CommandError(str(e)) from None
    create_admin_table()
    db_session = get_session()
    try:
        db_session.execute(text("LOCK TABLE administrators IN EXCLUSIVE MODE"))
        if db_session.query(Administrator).filter(Administrator.role == ROLE_ADMIN).first() is not None:
            raise CommandError("an admin account already exists; use the Accounts page or the other commands")
        if db_session.query(Administrator).filter(Administrator.username == username).first() is not None:
            raise CommandError(f"the username {username!r} is already taken")
        admin = Administrator(admin_id=admin_id or f"ADM_{uuid.uuid4().hex[:8].upper()}", username=username,
                              password_hash=generate_password_hash(password), role=ROLE_ADMIN)
        db_session.add(admin)
        db_session.flush()
        audit.record(db_session, local_actor(), "account_created", "admin", details={
            "target_admin_id": admin.admin_id, "target_username": admin.username, "role": ROLE_ADMIN,
            "channel": "first admin"})
        payload = accounts.account_payload(admin)
        db_session.commit()
        return payload
    except Exception:
        db_session.rollback()
        raise
    finally:
        db_session.close()


def build_parser():
    parser = argparse.ArgumentParser(
        prog="python -m src.manage_accounts",
        description="Account administration. deactivate, reactivate and role act as an admin who gives a password; "
                    "reset-password is local recovery and needs direct database access instead.",
    )
    commands = parser.add_subparsers(dest="action", required=True)
    for name, text in (("deactivate", "Deactivate an account"), ("reactivate", "Reactivate an account")):
        command = commands.add_parser(name, help=f"{text} (as an admin, audited)")
        command.add_argument("target_admin_id")
    role = commands.add_parser("role", help="Change an account's role (as an admin, audited)")
    role.add_argument("target_admin_id")
    role.add_argument("new_role")
    for name in ("deactivate", "reactivate", "role"):
        command = commands.choices[name]
        command.add_argument("--as", dest="actor", required=True, help="username of the acting admin")
        command.add_argument("--password-env", help="environment variable holding the acting admin's password")

    first = commands.add_parser("create-admin", help="Create the first admin account (only while no admin exists)")
    first.add_argument("username", help="username of the new admin")
    first.add_argument("--password-env", required=True, metavar="VARIABLE",
                       help="name of the environment variable that holds the password (not the password itself)")
    first.add_argument("--admin-id", help="account id (default: ADM_ and eight random characters)")

    reset = commands.add_parser("reset-password", help="Local recovery for a forgotten password (no admin password needed)",
                                description=RECOVERY_HELP)
    reset.add_argument("account", help="admin_id or username of the account to reset")
    reset.add_argument("--new-password-env", required=True, metavar="VARIABLE",
                       help="name of the environment variable that holds the new password (not the password itself)")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.action == "create-admin":
        password = os.environ.get(args.password_env)
        if not password:
            raise SystemExit(f"Refused: environment variable {args.password_env} is not set or is empty")
        try:
            account = create_first_admin(args.username, password, args.admin_id)
        except CommandError as e:
            raise SystemExit(f"Refused: {e}")
        print(f"Created the first admin {account['username']} ({account['admin_id']}).")
        return

    if args.action == "reset-password":
        new_password = os.environ.get(args.new_password_env)
        if not new_password:
            raise SystemExit(f"Refused: environment variable {args.new_password_env} is not set or is empty")
        try:
            account = reset_password(args.account, new_password)
        except accounts.AccountError as e:
            raise SystemExit(f"Refused: {e}")
        state = "active" if account["is_active"] else "deactivated (reactivate it separately if needed)"
        print(f"Password reset for {account['username']} ({account['admin_id']}, {account['role']}); the account is {state}.")
        return

    password = os.environ.get(args.password_env, "") if args.password_env else getpass.getpass(f"Password for {args.actor}: ")
    try:
        actor = acting_admin(args.actor, password)
        changed, account = run(args.action, args.target_admin_id, actor, getattr(args, "new_role", None))
    except (CommandError, accounts.AccountError) as e:
        raise SystemExit(f"Refused: {e}")
    print(f"{'Changed' if changed else 'No change'}: {account}")


if __name__ == "__main__":
    main()
