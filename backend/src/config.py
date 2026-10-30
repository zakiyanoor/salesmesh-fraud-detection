"""
App settings read from the environment (issue #26). load_config is pure, so the
rules can be tested without starting the app; api.py applies the result.

APP_ENV                  development, test or production (default production: a forgotten setting fails safe)
FLASK_DEBUG              default false; refused in production
CORS_ORIGINS             comma-separated; default http://localhost:5173 in development and test, none in production;
                         "*" is refused because requests carry credentials
SESSION_COOKIE_SECURE    default true, false in development and test (local http)
SESSION_COOKIE_SAMESITE  Lax (default) or Strict
SESSION_LIFETIME_MINUTES default 60
CUSTOMER_REF_KEY         key for the customer references in URLs and the audit log (issue #28); at least
                         32 characters; required in production, a random key per process in development and test.
                         Never logged or returned; errors name the setting, never its value.
RATELIMIT_STORAGE_URI    Flask-Limiter storage (default memory://, which counts per process)
WEB_CONCURRENCY          Gunicorn worker processes (default 1); with memory:// and more than one worker the
                         login limit is counted per worker, so production warns
TRUST_PROXY              default false; true when a reverse proxy sets X-Forwarded-For and X-Forwarded-Proto,
                         so the rate limiter and the audit log see the client address
The session cookie is always HttpOnly.
"""

import secrets
from datetime import timedelta

APP_ENVS = ("development", "test", "production")
LOCAL_ENVS = ("development", "test")
DEV_ORIGIN = "http://localhost:5173"
SAMESITE_VALUES = ("Lax", "Strict")
DEFAULT_SESSION_MINUTES = 60
MIN_CUSTOMER_REF_KEY_LENGTH = 32
DEFAULT_RATELIMIT_STORAGE = "memory://"
TRUE, FALSE = ("1", "true", "yes", "on"), ("0", "false", "no", "off", "")


class ConfigError(RuntimeError):
    pass


def _flag(environ, name, default):
    value = environ.get(name)
    if value is None:
        return default
    value = value.strip().lower()
    if value in TRUE:
        return True
    if value in FALSE:
        return False
    raise ConfigError(f"{name} must be true or false, not {value!r}")


def load_config(environ):
    """The app settings for an environment mapping such as os.environ; raises ConfigError on unsafe values."""
    app_env = environ.get("APP_ENV", "production").strip().lower()
    if app_env not in APP_ENVS:
        raise ConfigError(f"APP_ENV must be one of {', '.join(APP_ENVS)}, not {app_env!r}")
    local = app_env in LOCAL_ENVS

    debug = _flag(environ, "FLASK_DEBUG", False)
    if debug and app_env == "production":
        raise ConfigError("FLASK_DEBUG must not be on when APP_ENV is production")

    raw_origins = environ.get("CORS_ORIGINS")
    if raw_origins is None:
        origins = [DEV_ORIGIN] if local else []
    else:
        origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
    if "*" in origins:
        raise ConfigError("CORS_ORIGINS must list origins; '*' is not allowed with credentials")

    samesite = environ.get("SESSION_COOKIE_SAMESITE", "Lax").strip().capitalize()
    if samesite not in SAMESITE_VALUES:
        raise ConfigError(f"SESSION_COOKIE_SAMESITE must be Lax or Strict, not {samesite!r}")

    try:
        minutes = int(environ.get("SESSION_LIFETIME_MINUTES", DEFAULT_SESSION_MINUTES))
    except ValueError as error:
        raise ConfigError("SESSION_LIFETIME_MINUTES must be a whole number") from error
    if minutes < 1:
        raise ConfigError("SESSION_LIFETIME_MINUTES must be at least 1")
    secure = _flag(environ, "SESSION_COOKIE_SECURE", not local)

    customer_ref_key = environ.get("CUSTOMER_REF_KEY", "").strip()
    if not customer_ref_key and local:
        customer_ref_key = secrets.token_hex(32)
    if len(customer_ref_key) < MIN_CUSTOMER_REF_KEY_LENGTH:
        raise ConfigError(f"CUSTOMER_REF_KEY must be set to at least {MIN_CUSTOMER_REF_KEY_LENGTH} characters"
                          + (" in production" if not local else ""))

    storage = environ.get("RATELIMIT_STORAGE_URI", "").strip() or DEFAULT_RATELIMIT_STORAGE
    if "://" not in storage:
        raise ConfigError("RATELIMIT_STORAGE_URI must be a storage URI such as memory:// or redis://host:6379")
    try:
        workers = int(environ.get("WEB_CONCURRENCY", 1))
    except ValueError as error:
        raise ConfigError("WEB_CONCURRENCY must be a whole number") from error
    if workers < 1:
        raise ConfigError("WEB_CONCURRENCY must be at least 1")
    warnings = []
    if app_env == "production" and storage == DEFAULT_RATELIMIT_STORAGE and workers > 1:
        warnings.append(f"RATELIMIT_STORAGE_URI is memory:// with {workers} workers: each worker counts login "
                        "attempts separately; use a shared storage or one worker")

    return {
        "APP_ENV": app_env,
        "DEBUG": debug,
        "CORS_ORIGINS": origins,
        "SESSION_COOKIE_SECURE": secure,
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": samesite,
        "PERMANENT_SESSION_LIFETIME": timedelta(minutes=minutes),
        "CUSTOMER_REF_KEY": customer_ref_key,
        "RATELIMIT_STORAGE_URI": storage,
        "WEB_CONCURRENCY": workers,
        "TRUST_PROXY": _flag(environ, "TRUST_PROXY", False),
        "WARNINGS": warnings,
    }
