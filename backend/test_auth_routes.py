"""Tests for Discord OAuth routes and /auth/me."""
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


def test_auth_me_returns_401_when_not_logged_in(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_auth_me_returns_user_when_session_set(client):
    with client.session_transaction() as sess:
        sess["discord_id"] = "123"
        sess["discord_username"] = "TestUser"
        sess["is_admin"] = True
    resp = client.get("/auth/me")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["discord_id"] == "123"
    assert data["discord_username"] == "TestUser"
    assert data["is_admin"] is True


def test_auth_me_is_admin_false_by_default(client):
    with client.session_transaction() as sess:
        sess["discord_id"] = "456"
        sess["discord_username"] = "NotAdmin"
    resp = client.get("/auth/me")
    data = resp.get_json()
    assert data["is_admin"] is False


def test_auth_logout_clears_session(client):
    with client.session_transaction() as sess:
        sess["discord_id"] = "123"
        sess["is_admin"] = True
    resp = client.post("/auth/logout")
    assert resp.status_code == 200
    resp2 = client.get("/auth/me")
    assert resp2.status_code == 401


def test_discord_login_redirects_to_discord(client):
    resp = client.get("/auth/discord")
    assert resp.status_code == 302
    assert "discord.com/oauth2/authorize" in resp.headers["Location"]


def test_discord_callback_exchanges_code_and_sets_session(client):
    mock_token = MagicMock()
    mock_token.status_code = 200
    mock_token.json.return_value = {"access_token": "test-access-token"}

    mock_user = MagicMock()
    mock_user.status_code = 200
    mock_user.json.return_value = {"id": "discord-user-123", "username": "TestUser"}

    mock_member = MagicMock()
    mock_member.status_code = 200
    mock_member.json.return_value = {"roles": ["123456789"]}  # matches DISCORD_ADMIN_ROLE_ID

    with patch("app.http_requests.post", return_value=mock_token), \
         patch("app.http_requests.get", side_effect=[mock_user, mock_member]):
        resp = client.get("/auth/discord/callback?code=test-code")

    assert resp.status_code == 302
    with client.session_transaction() as sess:
        assert sess["discord_id"] == "discord-user-123"
        assert sess["is_admin"] is True


def test_discord_callback_sets_is_admin_false_without_role(client):
    mock_token = MagicMock()
    mock_token.status_code = 200
    mock_token.json.return_value = {"access_token": "test-token"}

    mock_user = MagicMock()
    mock_user.status_code = 200
    mock_user.json.return_value = {"id": "user-no-role", "username": "NoRole"}

    mock_member = MagicMock()
    mock_member.status_code = 200
    mock_member.json.return_value = {"roles": ["999999999"]}

    with patch("app.http_requests.post", return_value=mock_token), \
         patch("app.http_requests.get", side_effect=[mock_user, mock_member]):
        resp = client.get("/auth/discord/callback?code=code2")

    with client.session_transaction() as sess:
        assert sess["is_admin"] is False


def test_discord_callback_missing_code_returns_400(client):
    resp = client.get("/auth/discord/callback")
    assert resp.status_code == 400
