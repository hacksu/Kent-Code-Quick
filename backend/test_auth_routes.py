"""Tests for the auth routes (/api/auth/*).

The app uses a client-initiated Discord OAuth flow: the frontend builds the
authorize URL and redirects, Discord returns to the SPA, and the SPA calls
GET /api/auth/exchange?code=...&redirect_uri=... to swap the code for a session.
"""
from gevent import monkey
monkey.patch_all()

import pytest
from unittest.mock import patch, MagicMock
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


REDIRECT_URI = "http://localhost:5001/auth/callback"


def test_auth_me_returns_401_when_not_logged_in(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_auth_me_returns_user_when_session_set(client):
    with client.session_transaction() as sess:
        sess["discord_id"] = "123"
        sess["discord_username"] = "TestUser"
        sess["is_admin"] = True
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["discord_id"] == "123"
    assert data["discord_username"] == "TestUser"
    assert data["is_admin"] is True


def test_auth_me_is_admin_false_by_default(client):
    with client.session_transaction() as sess:
        sess["discord_id"] = "456"
        sess["discord_username"] = "NotAdmin"
    resp = client.get("/api/auth/me")
    data = resp.get_json()
    assert data["is_admin"] is False


def test_auth_logout_clears_session(client):
    with client.session_transaction() as sess:
        sess["discord_id"] = "123"
        sess["is_admin"] = True
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 200
    resp2 = client.get("/api/auth/me")
    assert resp2.status_code == 401


def test_auth_exchange_sets_session_and_is_admin_with_role(client):
    mock_token = MagicMock(status_code=200)
    mock_token.json.return_value = {"access_token": "test-access-token"}

    mock_user = MagicMock(status_code=200)
    mock_user.json.return_value = {"id": "discord-user-123", "username": "TestUser"}

    mock_member = MagicMock(status_code=200)
    mock_member.json.return_value = {"roles": ["123456789"]}  # matches DISCORD_ADMIN_ROLE_ID

    with patch("app.http_requests.post", return_value=mock_token), \
         patch("app.http_requests.get", side_effect=[mock_user, mock_member]):
        resp = client.get(f"/api/auth/exchange?code=test-code&redirect_uri={REDIRECT_URI}")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["is_admin"] is True
    assert data["discord_username"] == "TestUser"
    with client.session_transaction() as sess:
        assert sess["discord_id"] == "discord-user-123"
        assert sess["is_admin"] is True


def test_auth_exchange_sets_is_admin_false_without_role(client):
    mock_token = MagicMock(status_code=200)
    mock_token.json.return_value = {"access_token": "test-token"}

    mock_user = MagicMock(status_code=200)
    mock_user.json.return_value = {"id": "user-no-role", "username": "NoRole"}

    mock_member = MagicMock(status_code=200)
    mock_member.json.return_value = {"roles": ["999999999"]}

    with patch("app.http_requests.post", return_value=mock_token), \
         patch("app.http_requests.get", side_effect=[mock_user, mock_member]):
        resp = client.get(f"/api/auth/exchange?code=code2&redirect_uri={REDIRECT_URI}")

    assert resp.status_code == 200
    assert resp.get_json()["is_admin"] is False
    with client.session_transaction() as sess:
        assert sess["is_admin"] is False


def test_auth_exchange_missing_code_returns_400(client):
    resp = client.get(f"/api/auth/exchange?redirect_uri={REDIRECT_URI}")
    assert resp.status_code == 400
