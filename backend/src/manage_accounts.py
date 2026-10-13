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
"""

import argparse
import getpass
import os

from src import accounts, audit
from src.auth import ROLE_ADMIN, verify_login
from src.db import get_session


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


def main(argv=None):
    parser = argparse.ArgumentParser(description="Change an account as an admin (audited).")
    parser.add_argument("action", choices=["deactivate", "reactivate", "role"])
    parser.add_argument("target_admin_id")
    parser.add_argument("new_role", nargs="?")
    parser.add_argument("--as", dest="actor", required=True, help="username of the acting admin")
    parser.add_argument("--password-env", help="environment variable holding the acting admin's password")
    args = parser.parse_args(argv)
    if (args.action == "role") != (args.new_role is not None):
        parser.error("new_role is required for 'role' and not allowed otherwise")
    password = os.environ.get(args.password_env, "") if args.password_env else getpass.getpass(f"Password for {args.actor}: ")
    try:
        actor = acting_admin(args.actor, password)
        changed, account = run(args.action, args.target_admin_id, actor, args.new_role)
    except (CommandError, accounts.AccountError) as e:
        raise SystemExit(f"Refused: {e}")
    print(f"{'Changed' if changed else 'No change'}: {account}")


if __name__ == "__main__":
    main()
