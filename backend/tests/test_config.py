"""App settings from the environment (issue #26): debug, CORS and the session cookie flags."""

from datetime import timedelta

import pytest

from src.config import DEV_ORIGIN, ConfigError, load_config
from tests.helpers import ANALYST, login

KEY = {"CUSTOMER_REF_KEY": "k" * 32}  # production requires one (issue #28)


def test_production_is_the_default_and_is_strict() -> None:
    config = load_config(dict(KEY))
    assert config["APP_ENV"] == "production" and config["DEBUG"] is False
    assert config["CORS_ORIGINS"] == []
    assert config["SESSION_COOKIE_SECURE"] is True and config["SESSION_COOKIE_HTTPONLY"] is True
    assert config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert config["PERMANENT_SESSION_LIFETIME"] == timedelta(minutes=60)


@pytest.mark.parametrize("app_env", ["development", "test"])
def test_local_environments_allow_the_dev_server_over_http(app_env) -> None:
    config = load_config({"APP_ENV": app_env})
    assert config["CORS_ORIGINS"] == [DEV_ORIGIN] and config["SESSION_COOKIE_SECURE"] is False
    assert config["SESSION_COOKIE_HTTPONLY"] is True


def test_settings_are_read_from_the_environment() -> None:
    config = load_config({
        **KEY, "APP_ENV": "production", "CORS_ORIGINS": "https://a.example, https://b.example",
        "SESSION_COOKIE_SAMESITE": "strict", "SESSION_LIFETIME_MINUTES": "15",
    })
    assert config["CORS_ORIGINS"] == ["https://a.example", "https://b.example"]
    assert config["SESSION_COOKIE_SAMESITE"] == "Strict"
    assert config["PERMANENT_SESSION_LIFETIME"] == timedelta(minutes=15)
    assert load_config({"APP_ENV": "development", "FLASK_DEBUG": "true"})["DEBUG"] is True


@pytest.mark.parametrize("environ, message", [
    ({"APP_ENV": "staging"}, "APP_ENV"),
    ({"APP_ENV": "production", "FLASK_DEBUG": "1"}, "FLASK_DEBUG"),
    ({"FLASK_DEBUG": "maybe"}, "FLASK_DEBUG"),
    ({"CORS_ORIGINS": "*"}, "CORS_ORIGINS"),
    ({"SESSION_COOKIE_SAMESITE": "None"}, "SAMESITE"),
    ({"SESSION_LIFETIME_MINUTES": "0"}, "SESSION_LIFETIME_MINUTES"),
    ({"SESSION_LIFETIME_MINUTES": "an hour"}, "SESSION_LIFETIME_MINUTES"),
    ({"SESSION_COOKIE_SECURE": "sometimes"}, "SESSION_COOKIE_SECURE"),
])
def test_unsafe_or_unknown_values_are_refused(environ, message) -> None:
    with pytest.raises(ConfigError, match=message):
        load_config(environ)


def test_login_cookie_carries_the_flags_and_an_expiry(client) -> None:
    from src.api import app

    login(client, ANALYST)
    cookie = client.get_cookie("session")
    assert cookie is not None and cookie.http_only and cookie.same_site == "Lax" and cookie.expires is not None
    previous = app.config["SESSION_COOKIE_SECURE"]
    app.config["SESSION_COOKIE_SECURE"] = True
    try:
        response = client.post("/api/login", json={"username": ANALYST["username"], "password": ANALYST["password"]})
        assert "Secure" in response.headers["Set-Cookie"] and "HttpOnly" in response.headers["Set-Cookie"]
    finally:
        app.config["SESSION_COOKIE_SECURE"] = previous


def test_cors_answers_only_configured_origins(client) -> None:
    allowed = client.get("/api/health", headers={"Origin": DEV_ORIGIN})
    assert allowed.headers.get("Access-Control-Allow-Origin") == DEV_ORIGIN
    assert allowed.headers.get("Access-Control-Allow-Credentials") == "true"
    other = client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert "Access-Control-Allow-Origin" not in other.headers


@pytest.mark.parametrize("environ", [{}, {"CUSTOMER_REF_KEY": ""}, {"CUSTOMER_REF_KEY": "short-key-value"}],
                         ids=["unset", "empty", "too-short"])
def test_production_requires_a_customer_ref_key_and_never_shows_it(environ) -> None:
    with pytest.raises(ConfigError, match="CUSTOMER_REF_KEY") as error:
        load_config({"APP_ENV": "production", **environ})
    assert "short-key-value" not in str(error.value)


def test_local_environments_get_a_random_customer_ref_key_unless_one_is_set() -> None:
    first, second = (load_config({"APP_ENV": "development"})["CUSTOMER_REF_KEY"] for _ in range(2))
    assert len(first) == 64 and first != second
    assert load_config({"APP_ENV": "test", **KEY})["CUSTOMER_REF_KEY"] == "k" * 32
    with pytest.raises(ConfigError, match="CUSTOMER_REF_KEY"):
        load_config({"APP_ENV": "test", "CUSTOMER_REF_KEY": "too short"})


# --- Deployment settings (issue #20) ---

def test_limiter_storage_workers_and_proxy_trust_have_safe_defaults() -> None:
    config = load_config(dict(KEY))
    assert config["RATELIMIT_STORAGE_URI"] == "memory://" and config["WEB_CONCURRENCY"] == 1
    assert config["TRUST_PROXY"] is False and config["WARNINGS"] == []
    assert load_config({**KEY, "RATELIMIT_STORAGE_URI": ""})["RATELIMIT_STORAGE_URI"] == "memory://"


def test_limiter_storage_workers_and_proxy_trust_are_read_from_the_environment() -> None:
    config = load_config({**KEY, "RATELIMIT_STORAGE_URI": "redis://cache:6379", "WEB_CONCURRENCY": "3",
                          "TRUST_PROXY": "true"})
    assert config["RATELIMIT_STORAGE_URI"] == "redis://cache:6379" and config["WEB_CONCURRENCY"] == 3
    assert config["TRUST_PROXY"] is True and config["WARNINGS"] == []


def test_production_warns_when_memory_storage_meets_several_workers() -> None:
    (warning,) = load_config({**KEY, "WEB_CONCURRENCY": "2"})["WARNINGS"]
    assert "memory://" in warning and "2 workers" in warning
    assert load_config({"APP_ENV": "development", "WEB_CONCURRENCY": "2"})["WARNINGS"] == []


@pytest.mark.parametrize("environ, message", [
    ({"RATELIMIT_STORAGE_URI": "localhost:6379"}, "RATELIMIT_STORAGE_URI"),
    ({"WEB_CONCURRENCY": "two"}, "WEB_CONCURRENCY"),
    ({"WEB_CONCURRENCY": "0"}, "WEB_CONCURRENCY"),
    ({"TRUST_PROXY": "perhaps"}, "TRUST_PROXY"),
])
def test_unsafe_deployment_values_are_refused(environ, message) -> None:
    with pytest.raises(ConfigError, match=message):
        load_config({**KEY, **environ})
