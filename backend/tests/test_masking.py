"""Data minimisation (issue #4): no endpoint returns an unmasked phone or national ID number."""

import re

import pytest

from src.api import app, mask_tail
from src.db import AgentIdentity, get_session
from tests.helpers import ALL_ACCOUNTS, ANALYST, login

PLACEHOLDERS = {"decision_id": "NONEXISTENT"}
FULL_PHONE = re.compile(r"\+2547\d{8}")


@pytest.fixture(scope="module")
def identities(database):
    db_session = get_session()
    try:
        return [(i.agent_id, i.phone_number, i.national_id_number) for i in db_session.query(AgentIdentity)]
    finally:
        db_session.close()


def get_urls(agent_ids):
    urls = []
    for rule in app.url_map.iter_rules():
        if "GET" not in rule.methods or rule.endpoint == "static":
            continue
        if "agent_id" in rule.arguments:
            urls += [rule.rule.replace("<agent_id>", a) for a in agent_ids]
        else:
            path = rule.rule
            for name in rule.arguments:
                path = path.replace(f"<{name}>", PLACEHOLDERS[name])
            urls.append(path)
    return urls


def assert_no_full_value(text, identities, where):
    assert not FULL_PHONE.search(text), f"{where}: unmasked phone number"
    for _, phone, national_id in identities:
        assert phone not in text and phone[1:] not in text, f"{where}: phone {phone[-3:]} unmasked"
        # Not preceded by a letter or digit: customer ids (CUST + 8 digits) may share digits by chance.
        assert not re.search(rf"(?<![0-9A-Za-z]){national_id}(?!\d)", text), f"{where}: national ID {national_id[-3:]} unmasked"


def test_mask_keeps_only_the_last_three_digits() -> None:
    assert mask_tail("+254730520966") == "**********966"
    assert mask_tail("74095151") == "*****151"
    assert mask_tail(None) is None


def test_no_endpoint_returns_an_unmasked_phone_or_id(client, identities, known_agent_id) -> None:
    agent_ids = [known_agent_id] + [a for a, _, _ in identities[:40]]
    for account in ALL_ACCOUNTS:
        response = client.post("/api/login", json={"username": account["username"], "password": account["password"]})
        assert_no_full_value(response.get_data().decode("utf-8", errors="replace"), identities, "POST /api/login")
        for url in get_urls(agent_ids):
            response = client.get(url)
            assert_no_full_value(response.get_data().decode("utf-8", errors="replace"), identities, f"GET {url}")
        client.post("/api/logout")
    get_rules = [r for r in app.url_map.iter_rules() if "GET" in r.methods and r.endpoint != "static"]
    assert len(get_urls(["X"])) == len(get_rules) >= 9


def test_agent_detail_shows_the_masked_identity(client, identities, known_agent_id) -> None:
    login(client, ANALYST)
    identity = client.get(f"/api/agents/{known_agent_id}").get_json()["identity"]
    _, phone, national_id = next(i for i in identities if i[0] == known_agent_id)
    assert identity["phone_number"] == "*" * (len(phone) - 3) + phone[-3:]
    assert identity["national_id_number"] == "*" * (len(national_id) - 3) + national_id[-3:]
    assert identity["full_name"]
