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
The session cookie is always HttpOnly.
"""

from datetime import timedelta

APP_ENVS = ("development", "test", "production")
LOCAL_ENVS = ("development", "test")
DEV_ORIGIN = "http://localhost:5173"
SAMESITE_VALUES = ("Lax", "Strict")
DEFAULT_SESSION_MINUTES = 60
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

    return {
        "APP_ENV": app_env,
        "DEBUG": debug,
        "CORS_ORIGINS": origins,
        "SESSION_COOKIE_SECURE": _flag(environ, "SESSION_COOKIE_SECURE", not local),
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": samesite,
        "PERMANENT_SESSION_LIFETIME": timedelta(minutes=minutes),
    }
