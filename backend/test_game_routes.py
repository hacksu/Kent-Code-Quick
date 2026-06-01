"""Tests for /api/game HTTP routes."""
from gevent import monkey
monkey.patch_all()

import pytest
from app import app
import game_manager
from game_manager import create_game, add_to_lobby, start_game


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def reset_game():
    game_manager.game = None
    yield
    game_manager.game = None


def set_admin_session(client):
    with client.session_transaction() as sess:
        sess["is_admin"] = True
        sess["discord_id"] = "admin-id"
        sess["discord_username"] = "Admin"


def test_get_game_defaults_to_waiting_when_no_game(client):
    resp = client.get("/api/game")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "waiting"


def test_get_game_returns_current_status(client):
    create_game()
    resp = client.get("/api/game")
    assert resp.get_json()["status"] == "waiting"


def test_create_game_requires_admin(client):
    resp = client.post("/api/game", json={"duration_ms": 60_000})
    assert resp.status_code == 403


def test_create_game_creates_waiting_game(client):
    set_admin_session(client)
    resp = client.post("/api/game", json={"duration_ms": 60_000})
    assert resp.status_code == 201
    assert resp.get_json()["status"] == "waiting"
    assert resp.get_json()["duration_ms"] == 60_000


def test_create_game_uses_default_duration(client):
    set_admin_session(client)
    resp = client.post("/api/game", json={})
    assert resp.get_json()["duration_ms"] == 45 * 60 * 1000


def test_get_game_results_requires_admin(client):
    create_game()
    resp = client.get("/api/game/results")
    assert resp.status_code == 403


def test_get_game_results_returns_404_when_no_game(client):
    set_admin_session(client)
    resp = client.get("/api/game/results")
    assert resp.status_code == 404


def test_get_game_results_returns_game_state(client):
    set_admin_session(client)
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1")
    start_game(g)
    resp = client.get("/api/game/results")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "active"
    assert len(data["participants"]) == 1
