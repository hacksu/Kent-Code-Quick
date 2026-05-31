"""Tests for refactored ws_handler: join_lobby, join_game, start_game, watch_game."""
from gevent import monkey
monkey.patch_all()

import pytest
from unittest.mock import patch
from app import app, socketio
import game_manager
from game_manager import create_game, add_to_lobby, start_game


@pytest.fixture(autouse=True)
def reset_game():
    game_manager.game = None
    yield
    game_manager.game = None


def admin_ws_client():
    """Return a WS client with an active admin session."""
    app.secret_key = "test-session-secret"
    http_client = app.test_client()
    with http_client.session_transaction() as sess:
        sess["is_admin"] = True
        sess["discord_id"] = "admin-discord-id"
        sess["discord_username"] = "AdminUser"
    return socketio.test_client(app, flask_test_client=http_client)


# --- join_lobby ---

def test_join_lobby_adds_to_lobby_and_issues_token():
    ws = socketio.test_client(app)
    ws.emit("join_lobby", {"name": "Alice"})
    received = ws.get_received()
    token_msgs = [m for m in received if m["name"] == "token_assigned"]
    assert len(token_msgs) == 1
    token = token_msgs[0]["args"][0]["token"]
    g = game_manager.game
    assert g is not None
    assert token in g.lobby
    assert g.lobby[token].name == "Alice"


def test_join_lobby_returns_game_locked_when_active():
    g = create_game()
    add_to_lobby(g, None, "Bob", "sid-bob")
    start_game(g)
    ws = socketio.test_client(app)
    ws.emit("join_lobby", {"name": "Late"})
    received = ws.get_received()
    names = [m["name"] for m in received]
    assert "game_locked" in names
    assert "token_assigned" not in names


def test_join_lobby_returns_game_locked_when_ended():
    g = create_game()
    g.status = "ended"
    ws = socketio.test_client(app)
    ws.emit("join_lobby", {"name": "Late"})
    received = ws.get_received()
    names = [m["name"] for m in received]
    assert "game_locked" in names


def test_join_lobby_rehydrates_existing_token():
    g = create_game()
    token, entry = add_to_lobby(g, None, "Alice", "old-sid")
    ws = socketio.test_client(app)
    ws.emit("join_lobby", {"name": "Alice", "token": token})
    received = ws.get_received()
    token_msgs = [m for m in received if m["name"] == "token_assigned"]
    assert len(token_msgs) == 0
    assert len(g.lobby) == 1


def test_join_lobby_broadcasts_lobby_update():
    ws1 = socketio.test_client(app)
    ws1.emit("join_lobby", {"name": "Alice"})
    ws1.get_received()
    ws2 = socketio.test_client(app)
    ws2.emit("join_lobby", {"name": "Bob"})
    received1 = ws1.get_received()
    lobby_updates = [m for m in received1 if m["name"] == "lobby_update"]
    assert len(lobby_updates) >= 1
    assert lobby_updates[-1]["args"][0]["lobby_count"] == 2


# --- start_game ---

def test_start_game_requires_admin_session():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1")
    ws = socketio.test_client(app)
    ws.emit("start_game", {})
    assert game_manager.game.status == "waiting"


def test_start_game_transitions_to_active():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1")
    ws = admin_ws_client()
    with patch("ws_handler.gevent.spawn"):
        ws.emit("start_game", {})
    assert game_manager.game.status == "active"
    assert len(game_manager.game.participants) == 1
    assert len(game_manager.game.lobby) == 0


def test_start_game_emits_game_start_to_lobby_participants():
    g = create_game()
    participant_ws = socketio.test_client(app)
    participant_ws.emit("join_lobby", {"name": "Alice"})
    participant_ws.get_received()
    admin_ws = admin_ws_client()
    with patch("ws_handler.gevent.spawn"):
        admin_ws.emit("start_game", {})
    received = participant_ws.get_received()
    game_start_msgs = [m for m in received if m["name"] == "game_start"]
    assert len(game_start_msgs) == 1
    payload = game_start_msgs[0]["args"][0]
    assert "token" in payload


def test_start_game_spawns_timer():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1")
    ws = admin_ws_client()
    with patch("ws_handler.gevent.spawn") as mock_spawn:
        ws.emit("start_game", {})
    assert mock_spawn.call_count == 1


# --- join_game ---

def test_join_game_with_valid_token_gets_game_state():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1")
    start_game(g)
    token = list(g.participants.keys())[0]
    ws = socketio.test_client(app)
    ws.emit("join_game", {"token": token})
    received = ws.get_received()
    state_msgs = [m for m in received if m["name"] == "game_state"]
    assert len(state_msgs) == 1
    assert state_msgs[0]["args"][0]["status"] == "active"


def test_join_game_with_invalid_token_gets_game_locked():
    g = create_game()
    start_game(g)
    ws = socketio.test_client(app)
    ws.emit("join_game", {"token": "not-a-real-token"})
    received = ws.get_received()
    names = [m["name"] for m in received]
    assert "game_locked" in names


# --- end_event ---

def test_end_event_requires_admin_session():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1")
    start_game(g)
    ws = socketio.test_client(app)
    ws.emit("end_event", {})
    assert game_manager.game.status == "active"


def test_end_event_ends_game():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1")
    start_game(g)
    ws = admin_ws_client()
    ws.emit("end_event", {})
    assert game_manager.game.status == "ended"
    assert game_manager.game.ended_at is not None
