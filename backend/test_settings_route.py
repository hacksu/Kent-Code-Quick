"""Tests for the landing-page sign-up switch (/api/settings)."""
from gevent import monkey
monkey.patch_all()

import pytest
from app import app
import game_manager


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def admin_client(tmp_path, monkeypatch):
    monkeypatch.setenv("RESULTS_DIR", str(tmp_path))
    app.config["TESTING"] = True
    app.secret_key = "test-session-secret"
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess["is_admin"] = True
            sess["discord_id"] = "admin-discord-id"
            sess["discord_username"] = "AdminUser"
        yield c


@pytest.fixture(autouse=True)
def reset_settings():
    game_manager.settings = dict(game_manager.DEFAULT_SETTINGS)
    yield
    game_manager.settings = dict(game_manager.DEFAULT_SETTINGS)


def test_signup_is_closed_by_default(client):
    assert client.get("/api/config").get_json()["signup_open"] is False


def test_admin_can_open_and_close_signup(admin_client):
    resp = admin_client.post("/api/settings", json={"signup_open": True})
    assert resp.status_code == 200
    assert resp.get_json()["signup_open"] is True
    assert admin_client.get("/api/config").get_json()["signup_open"] is True

    resp = admin_client.post("/api/settings", json={"signup_open": False})
    assert resp.get_json()["signup_open"] is False
    assert admin_client.get("/api/config").get_json()["signup_open"] is False


def test_non_admin_cannot_change_signup(client):
    resp = client.post("/api/settings", json={"signup_open": True})
    assert resp.status_code == 403
    assert game_manager.get_settings()["signup_open"] is False


def test_non_admin_cannot_read_settings(client):
    assert client.get("/api/settings").status_code == 403


def test_admin_can_read_settings(admin_client):
    assert admin_client.get("/api/settings").get_json() == {"signup_open": False}


def test_missing_field_is_rejected(admin_client):
    resp = admin_client.post("/api/settings", json={})
    assert resp.status_code == 400
    assert game_manager.get_settings()["signup_open"] is False


def test_signup_switch_survives_a_restart(tmp_path, monkeypatch):
    monkeypatch.setenv("RESULTS_DIR", str(tmp_path))
    game_manager.set_signup_open(True)

    game_manager.settings = dict(game_manager.DEFAULT_SETTINGS)  # simulate a restart
    assert game_manager.load_settings()["signup_open"] is True


def test_resetting_a_round_does_not_close_signup(tmp_path, monkeypatch):
    monkeypatch.setenv("RESULTS_DIR", str(tmp_path))
    game_manager.set_signup_open(True)
    game_manager.reset_game()
    assert game_manager.get_settings()["signup_open"] is True
