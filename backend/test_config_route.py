"""Tests for GET /api/config."""
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


def test_config_env_override_wins_and_strips_trailing_slash(client):
    with patch.dict("os.environ", {"DEVDOCS_URL": "https://docs.example.org/"}):
        resp = client.get("/api/config", headers={"Host": "10.0.0.5:5001"})
    assert resp.get_json()["devdocs_url"] == "https://docs.example.org"

