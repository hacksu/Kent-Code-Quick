"""Tests for GET /api/config.

The devdocs URL is loaded by the participant's browser as an iframe, so it must
resolve on the client, not inside the Docker network.
"""
from gevent import monkey
monkey.patch_all()

import pytest
from unittest.mock import patch
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_config_defaults_to_request_host_on_9292(client):
    with patch.dict("os.environ", {"DEVDOCS_URL": ""}):
        resp = client.get("/api/config", headers={"Host": "10.0.0.5:5001"})
    assert resp.status_code == 200
    assert resp.get_json()["devdocs_url"] == "http://10.0.0.5:9292"


def test_config_default_handles_host_without_port(client):
    with patch.dict("os.environ", {"DEVDOCS_URL": ""}):
        resp = client.get("/api/config", headers={"Host": "kcq.example.org"})
    assert resp.get_json()["devdocs_url"] == "http://kcq.example.org:9292"


def test_config_env_override_wins_and_strips_trailing_slash(client):
    with patch.dict("os.environ", {"DEVDOCS_URL": "https://docs.example.org/"}):
        resp = client.get("/api/config", headers={"Host": "10.0.0.5:5001"})
    assert resp.get_json()["devdocs_url"] == "https://docs.example.org"
