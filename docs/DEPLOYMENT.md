# Deployment

This document describes a private demonstration deployment of the system on one Linux server (issue #20). It follows the supervisor review: the frontend and the API are served from one origin over HTTPS, the API runs under Gunicorn, the detection scheduler runs as its own process, the settings are production settings, and a smoke test checks the running system. All commands run from the repository root on the server unless stated otherwise.

## 1. Overview

`docker-compose.yml` defines four services and one setup task.

| Service | Image | Role |
|---|---|---|
| `proxy` | `salesmesh-proxy` (`deploy/Dockerfile.proxy`) | Caddy. Serves the built frontend, forwards `/api/*` to the API, obtains and renews the HTTPS certificate. The only service with published ports (80 and 443). |
| `api` | `salesmesh-api` (`backend/Dockerfile`) | Gunicorn with one worker and four threads, running `src.api:app` on port 8000 inside the Compose network. |
| `scheduler` | `salesmesh-api` | `python -m src.scheduler`: one detection run when it starts, then one every 1440 minutes. Exactly one copy. |
| `db` | `postgres:17` | PostgreSQL with its data in the named volume `db-data`. Not reachable from outside the server. |
| `load-data` | `salesmesh-api` | Setup profile only. Loads the five synthetic input files once. |

The images hold no secrets and no `.env` file. The API image contains the backend and only the files of `ml/` that the backend reads at run time: the Python modules, `results/FREEZE.md`, the scoring bundle, `operating_point.json`, and the `summary.json` and `test_metrics.csv` of the final evaluation run. No file of `ml/data`, and in particular neither `labels.csv` nor `rings.csv`, is part of any image.

## 2. Server requirements

- A 64 bit Linux server, for example Ubuntu Server 24.04 LTS, with at least 2 processor cores, 4 GB of memory and 20 GB of free disk space. A detection run holds about 135,000 activation records in memory.
- Ports 80 and 443 open to the internet (TCP, and UDP 443 for HTTP/3), and port 22 for administration.
- For a public certificate, a domain name whose DNS record points at the server (section 4).
- Git, Docker Engine with the Compose plugin, and Python 3 for the smoke test.

A firewall that allows only these ports can be set with `ufw`:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443
sudo ufw enable
```

## 3. Installing Docker and getting the code

Docker Engine is installed from Docker's own package repository, as described in the official installation guide for Ubuntu (https://docs.docker.com/engine/install/ubuntu/):

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git python3
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"    # then sign out and in again
docker compose version
```

The code is cloned on the server and the release to deploy is checked out:

```bash
git clone https://github.com/<owner>/salesmesh-fraud-detection.git
cd salesmesh-fraud-detection
git checkout main    # or a release tag
```

The frozen files must keep their exact bytes. `.gitattributes` pins the line endings of every text file hashed in `ml/results/FREEZE.md`, so a normal clone reproduces them on Linux. The images are built from this checkout, so building on the server (or in CI on Linux) is the safe choice.

## 4. Pointing a domain at the server

- Create an `A` record (and an `AAAA` record if the server has IPv6) for the chosen name, for example `fraud.example.org`, with the public address of the server.
- Wait until `dig +short fraud.example.org` returns that address.
- Set `SITE_ADDRESS=fraud.example.org` in the env file (section 5). On its first start Caddy obtains a certificate from Let's Encrypt over port 80 or 443 and renews it automatically. The certificate and its key are stored in the `caddy-data` volume.
- Without a domain, `SITE_ADDRESS=localhost` gives a certificate signed by Caddy's own local authority. Browsers do not trust it, so this setting is for tests on the server itself only (the smoke test then needs `--insecure`).
- The site sends `Strict-Transport-Security` for one year, so a browser that has visited the domain refuses plain HTTP for it afterwards.

## 5. Creating the env file

All settings come from `deploy/.env.production`, which is created from the example and never committed (`.gitignore` excludes it). The three secrets are generated on the server:

```bash
cp deploy/.env.production.example deploy/.env.production
chmod 600 deploy/.env.production
for name in FLASK_SECRET_KEY CUSTOMER_REF_KEY DB_PASSWORD; do
  sed -i "s/^$name=.*/$name=$(openssl rand -hex 32)/" deploy/.env.production
done
sed -i "s/^SITE_ADDRESS=.*/SITE_ADDRESS=fraud.example.org/" deploy/.env.production
grep -c '=$' deploy/.env.production    # empty values left: CORS_ORIGINS and DB_SSLMODE only, so 2
```

Each line of the example has a comment. The important production values are `APP_ENV=production`, an empty `CORS_ORIGINS` (one origin needs no CORS), `SESSION_COOKIE_SECURE=true`, `TRUST_PROXY=true` (Caddy sets `X-Forwarded-For`), `RATELIMIT_STORAGE_URI=memory://` with `WEB_CONCURRENCY=1`, and `DB_HOST=db`. The scheduler settings `DETECTION_INTERVAL_MINUTES=1440` and `DETECTION_RUN_ON_START=true` are set for the scheduler service in `docker-compose.yml`, which takes precedence over the env file.

## 6. First start

The database starts first. The setup commands run as single use containers (`docker compose run --rm`), and the remaining services start only after the first detection run.

```bash
docker compose build
docker compose up -d --wait db

# 1. Schema: tables, columns, checks and the append only triggers (safe to repeat).
docker compose run --rm api python -m src.migrate

# 2. Data: the five synthetic input files, checked against FREEZE.md and the expected row counts.
docker compose --profile setup run --rm load-data

# 3. The first administrator. The password is typed without echo, passed by variable name, never as an argument.
read -rs ADMIN_PASSWORD && export ADMIN_PASSWORD
docker compose run --rm -e ADMIN_PASSWORD api python -m src.manage_accounts create-admin <username> --password-env ADMIN_PASSWORD
unset ADMIN_PASSWORD

# 4. The first detection run with the frozen lof_v3_4f model (trigger "manual").
docker compose run --rm api python -m src.pipeline

# 5. The API, the scheduler and the proxy.
docker compose up -d --wait
```

`create-admin` works only while no account has the admin role. It applies the usual password rule (at least 12 characters), writes an `account_created` entry to the audit log without the password, and refuses on every later attempt. Further accounts are managed as described in `docs/OPERATIONS.md`. The demonstration accounts of `python -m src.auth` are refused in production.

### How the first load receives the data without the labels

The `load-data` service in `docker-compose.yml` mounts exactly five files, read only, from the checkout: `clients.csv`, `agents.csv`, `agent_identity.csv`, `agent_categories.csv` and `activation_records.csv` in `ml/data/synthetic`. `labels.csv` and `rings.csv` are never mounted, `.dockerignore` excludes all of `ml/data` from the build context, and the loader itself refuses those two names. The loader checks each file's sha256 against `ml/results/FREEZE.md` and the row counts before it commits, so a changed or incomplete file stops the load and leaves the database as it was. The ground truth files stay on the server's disk as part of the git checkout, but they never enter an image or a container.

## 7. Checking health

```bash
docker compose ps                                    # api healthy, proxy, scheduler and db running
curl -fsS https://fraud.example.org/api/health      # {"status":"ok"}
docker compose logs --tail 50 api proxy scheduler
docker compose run --rm --no-deps api python -c "from src.ml_bridge import load_frozen_bundle; load_frozen_bundle(); print('frozen bundle matches FREEZE.md')"
```

## 8. Smoke test

`deploy/smoke_test.py` uses only the Python standard library and checks the live address: the app at `/` and at a deep link, `/api/health`, `/api/me` before signing in (401), signing in with an existing account, the `Secure` and `HttpOnly` flags of the session cookie, the latest detection run, signing out, the login rate limit (the sixth failed attempt within a minute returns 429), and the absence of an `Access-Control-Allow-Origin` header for a foreign origin. The password comes from the environment and is never printed.

```bash
export SMOKE_USERNAME=<username>
read -rs SMOKE_PASSWORD && export SMOKE_PASSWORD
python3 deploy/smoke_test.py https://fraud.example.org
unset SMOKE_PASSWORD
```

The test waits one minute before the rate limit check, so that its own sign in does not count, and exits with status 1 if any check fails. It leaves sign in, sign out and failed sign in entries in the audit log, which is append only. For a local test with `SITE_ADDRESS=localhost`, add `--insecure`.

## 9. Scheduler checks

```bash
docker compose ps scheduler
docker compose logs --tail 20 scheduler    # "Scheduler started: detection cycle every 1440 min, first run now."
docker compose exec -T db sh -c 'psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT run_id, trigger, status, started_at, finished_at FROM detection_runs ORDER BY started_at DESC LIMIT 5"'
```

A row with `trigger = scheduler` and `status = succeeded` appears within a few minutes of the start, and then once a day. Every restart of the scheduler container starts one more run, because `DETECTION_RUN_ON_START` is true. The service must run as exactly one copy (`deploy.replicas: 1`); a second copy would start overlapping runs, because nothing in the database prevents two runs at the same time. A failed run is stored with its error and the scheduler continues.

## 10. Restart and recovery test

```bash
docker compose restart                    # every service; data and certificates are kept in the volumes
docker compose up -d --wait
docker compose exec api sh -c 'kill 1'    # simulated crash of Gunicorn; restart: unless-stopped brings it back
sleep 15 && docker compose ps api
sudo reboot                               # after the reboot Docker starts the stack again
```

After each step, `/api/health` answers, a sign in works, and `detection_runs` still holds the earlier rows. Running the smoke test after the reboot completes the test.

## 11. Upgrading

```bash
docker compose exec -T db sh -c 'pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc' > ~/backups/salesmesh-before-upgrade.dump    # section 12
git fetch && git checkout <new tag or commit>
docker compose build
docker compose run --rm api python -m src.migrate
docker compose up -d --wait
python3 deploy/smoke_test.py https://fraud.example.org
```

`src.migrate` only adds what is missing (`ADD COLUMN IF NOT EXISTS`, new tables, new checks and triggers), so it can be repeated. The data is loaded once; a later `load-data` run reports "unchanged" while the files are unchanged.

## 12. Backups

```bash
mkdir -p ~/backups
docker compose exec -T db sh -c 'pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc' > ~/backups/salesmesh-$(date +%Y%m%d-%H%M).dump
```

The dump holds the audit log, the review decisions and the masked but fictional personal data, so it is stored with restricted permissions and copied to a second location. A restore is tested on an empty database, for example on a second server or a separate Compose project:

```bash
docker compose exec -T db sh -c 'createdb -U "$DB_USER" restore_check && pg_restore -U "$DB_USER" -d restore_check --no-owner' < ~/backups/<file>.dump
docker compose exec -T db sh -c 'psql -U "$DB_USER" -d restore_check -c "SELECT count(*) FROM admin_action_log"'
```

`pg_restore` creates the triggers after it has loaded the rows, so the append only triggers do not block a restore into an empty database.

## 13. Rollback

```bash
git checkout <previous tag or commit>
docker compose build
docker compose up -d --wait
```

The migrations only add columns and tables, so the previous release normally runs on the newer schema. If it does not, the database is restored from the backup taken before the upgrade: stop the stack, remove the `db-data` volume with `docker volume rm salesmesh_db-data`, start `db`, restore the dump with `pg_restore`, and start the stack again.

## 14. Rotating secrets

- **`FLASK_SECRET_KEY`:** generate a new value in the env file and run `docker compose up -d --force-recreate api`. Every session ends and every user signs in again.
- **`CUSTOMER_REF_KEY`:** as above. Customer links change, and the customer references already in the audit log can no longer be matched to new links; the entries themselves are kept.
- **`DB_PASSWORD`:** the env file value is only applied when the `db` volume is first created, so the role's password is changed in the database first and then in the env file:

  ```bash
  docker compose exec db sh -c 'psql -U "$DB_USER" -d "$DB_NAME"'    # then: \password <DB_USER>
  # edit DB_PASSWORD in deploy/.env.production to the same value
  docker compose up -d --force-recreate api scheduler
  ```

- **Account passwords:** `python -m src.manage_accounts reset-password` (see `docs/OPERATIONS.md`), run as `docker compose run --rm -e NEW_PASSWORD api python -m src.manage_accounts reset-password <account> --new-password-env NEW_PASSWORD`.

## 15. Using an outside database

A managed PostgreSQL service can replace the `db` service. In the env file, set `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_NAME` and `DB_PASSWORD` to the values the provider gives, `DB_SSLMODE=require` (or `verify-full`), and `DB_CREATE_DATABASE=false`, so that `src.migrate` uses the existing database and does not connect to a database called `postgres`. The `db` service is then not started, and every command adds `--no-deps`:

```bash
docker compose run --rm --no-deps api python -m src.migrate
docker compose --profile setup run --rm --no-deps load-data
docker compose up -d --no-deps --wait api scheduler proxy
```

The triggers use standard PL/pgSQL functions and a custom setting (`SET LOCAL salesmesh.audit_maintenance`), which the table owner may use on common managed services. The first load is one transaction of about 135,000 rows, so it should run from a server close to the database. The free plans of managed services limit the number of connections; the API and the scheduler together use at most a few.

## 16. Security notes and limitations

- **The append only audit rule protects against the application, not against the database owner.** Database triggers refuse updates, deletes and truncation of `admin_action_log`, and a closed review decision cannot be changed. A person with the database owner password can still drop or disable the triggers, or set the maintenance setting that the migrations use. In the `db` service the role created from `DB_USER` is the superuser of that database server. A stronger arrangement would run the migrations as an owner role and the application as a role that owns no table; this deployment does not implement it. The database password must therefore be treated as the key to the audit trail.
- **Rate limiting** counts in the memory of the one Gunicorn worker. More workers need a shared storage in `RATELIMIT_STORAGE_URI` (for example Redis, with the `redis` Python package added to the image); with `memory://` and more than one worker the API logs a warning.
- **The data is synthetic.** The personal data in the database is fictional, and identity numbers are masked in every response. The deployment is a private demonstration; there is no public registration, and accounts are created only by an administrator.
- **Request bodies** are limited to 1 MB by the proxy, and the Content Security Policy allows scripts from the site itself and the one inline colour scheme script, identified by its hash.
