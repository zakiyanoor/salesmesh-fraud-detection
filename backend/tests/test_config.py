"""App settings from the environment (issue #26): debug, CORS and the session cookie flags."""

from datetime import timedelta

import pytest

from src.config import DEV_ORIGIN, ConfigError, load_config
from tests.helpers import ANALYST, login


def test_production_is_the_default_and_is_strict() -> None:
    config = load_config({})
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
        "APP_ENV": "production", "CORS_ORIGINS": "https://a.example, https://b.example",
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
