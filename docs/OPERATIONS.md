# Operations

## Managing accounts from the server

The Accounts page can change a role, deactivate an account and reactivate it. Creating accounts and resetting passwords have no API: they are done on the server, from `backend/`, with the virtual environment active and the database settings in `backend/.env`. Every change below is recorded in the audit log (category `admin`).

Change an account as an administrator. The acting administrator signs in with their own password, read from the environment variable named by `--password-env`, or asked for at the prompt:

```bash
python -m src.manage_accounts role <admin_id> <fraud_analyst|compliance_officer|admin> --as <admin username>
python -m src.manage_accounts deactivate <admin_id> --as <admin username>
python -m src.manage_accounts reactivate <admin_id> --as <admin username>
```

These follow the same rules as the Accounts page: nobody can change their own account, and the last active administrator cannot be demoted or deactivated.

Reset a forgotten password (local recovery). It needs no administrator password, because it only works with direct access to the database. The new password is read from the environment variable you name, is never printed, and is not stored in the audit entry:

```bash
python -m src.manage_accounts reset-password <admin_id or username> --new-password-env NEW_PASSWORD
```

Create the three demo accounts (`analyst_01`, `compliance_01`, `admin_01`) in a development or test database. Their passwords come from `DEMO_ANALYST_PASSWORD`, `DEMO_COMPLIANCE_PASSWORD` and `DEMO_ADMIN_PASSWORD`; existing usernames are left as they are:

```bash
python -m src.auth
```

There is no command to create other accounts or to delete one. A deactivated account cannot sign in and stays in the list, so its audit history keeps a named actor.
