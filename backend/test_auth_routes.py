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
import game_manager


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


# --- dev-login escape hatch ---

def test_dev_login_is_forbidden_unless_node_env_is_development(client):
    with patch("app.IS_DEV", False):
        resp = client.get("/api/auth/dev-login?admin=1")
    assert resp.status_code == 403
    with client.session_transaction() as sess:
        assert "discord_id" not in sess


def test_dev_login_grants_an_admin_session_in_development(client):
    with patch("app.IS_DEV", True):
        resp = client.get("/api/auth/dev-login?admin=1")
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/admin"
    with client.session_transaction() as sess:
        assert sess["is_admin"] is True
        assert sess["discord_id"] == "dev-TestPlayer"


def test_dev_login_without_admin_flag_lands_in_the_lobby(client):
    with patch("app.IS_DEV", True):
        resp = client.get("/api/auth/dev-login?name=Ada")
    assert resp.headers["Location"] == "/lobby"
    with client.session_transaction() as sess:
        assert sess["is_admin"] is False
        assert sess["discord_username"] == "Ada"


def test_dev_login_ignores_the_signup_toggle(client):
    """Sign-ups being closed must not block the escape hatch."""
    import game_manager
    with patch.dict(game_manager.settings, {"signup_open": False}):
        with patch("app.IS_DEV", True):
            resp = client.get("/api/auth/dev-login?admin=1")
    assert resp.headers["Location"] == "/admin"


# --- the sign-up gate rides along on the auth responses ---
#
# Clients decide where to send someone from a single /api/auth/me call, so the
# toggle has to travel with it.

def test_auth_me_reports_whether_signups_are_open(client):
    with client.session_transaction() as sess:
        sess["discord_id"] = "u1"
        sess["discord_username"] = "Player"
        sess["is_admin"] = False

    with patch.dict(game_manager.settings, {"signup_open": False}):
        assert client.get("/api/auth/me").get_json()["signup_open"] is False
    with patch.dict(game_manager.settings, {"signup_open": True}):
        assert client.get("/api/auth/me").get_json()["signup_open"] is True


def test_auth_exchange_reports_whether_signups_are_open(client):
    mock_token = MagicMock(status_code=200)
    mock_token.json.return_value = {"access_token": "test-token"}
    mock_user = MagicMock(status_code=200)
    mock_user.json.return_value = {"id": "u2", "username": "Player"}
    mock_member = MagicMock(status_code=200)
    mock_member.json.return_value = {"roles": []}

    with patch.dict(game_manager.settings, {"signup_open": False}),          patch("app.http_requests.post", return_value=mock_token),          patch("app.http_requests.get", side_effect=[mock_user, mock_member]):
        resp = client.get(f"/api/auth/exchange?code=c&redirect_uri={REDIRECT_URI}")

    data = resp.get_json()
    assert data["is_admin"] is False
    assert data["signup_open"] is False
