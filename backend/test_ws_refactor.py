"""Tests for refactored ws_handler: join_lobby, join_game, start_game, watch_game."""
from gevent import monkey
monkey.patch_all()

import json
import time

import gevent
import pytest
from unittest.mock import patch
from app import app, socketio
import game_manager
import ws_handler
from game_manager import create_game, add_to_lobby, start_game


@pytest.fixture(autouse=True)
def reset_game():
    game_manager.game = None
    yield
    game_manager.game = None


@pytest.fixture(autouse=True)
def signups_open():
    """Most of these tests are about lobby mechanics, not the sign-up gate.

    The gate is admin-only while sign-ups are closed, so open them by default
    and let the gate's own tests close them again.
    """
    with patch.dict(game_manager.settings, {"signup_open": True}):
        yield


def admin_ws_client():
    """Return a WS client with an active admin session."""
    app.secret_key = "test-session-secret"
    http_client = app.test_client()
    with http_client.session_transaction() as sess:
        sess["is_admin"] = True
        sess["discord_id"] = "admin-discord-id"
        sess["discord_username"] = "AdminUser"
    return socketio.test_client(app, flask_test_client=http_client)


def player_ws_client(name="Alice", discord_id=None):
    """Return a WS client with a logged-in (non-admin) Discord session."""
    app.secret_key = "test-session-secret"
    http_client = app.test_client()
    with http_client.session_transaction() as sess:
        sess["is_admin"] = False
        sess["discord_id"] = discord_id or f"discord-{name}"
        sess["discord_username"] = name
    return socketio.test_client(app, flask_test_client=http_client)


# --- join_lobby ---

def test_join_lobby_adds_to_lobby_and_issues_token():
    ws = player_ws_client("Alice")
    ws.emit("join_lobby", {})
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
    ws = player_ws_client("Late")
    ws.emit("join_lobby", {})
    received = ws.get_received()
    names = [m["name"] for m in received]
    assert "game_locked" in names
    assert "token_assigned" not in names


def test_join_lobby_returns_game_locked_when_ended():
    g = create_game()
    g.status = "ended"
    ws = player_ws_client("Late")
    ws.emit("join_lobby", {})
    received = ws.get_received()
    names = [m["name"] for m in received]
    assert "game_locked" in names


def test_join_lobby_rehydrates_existing_token():
    g = create_game()
    token, entry = add_to_lobby(g, None, "Alice", "old-sid", "discord-Alice")
    ws = player_ws_client("Alice")
    ws.emit("join_lobby", {"token": token})
    received = ws.get_received()
    token_msgs = [m for m in received if m["name"] == "token_assigned"]
    assert len(token_msgs) == 0
    assert len(g.lobby) == 1


def test_join_lobby_broadcasts_lobby_update():
    ws1 = player_ws_client("Alice")
    ws1.emit("join_lobby", {})
    ws1.get_received()
    ws2 = player_ws_client("Bob")
    ws2.emit("join_lobby", {})
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
    participant_ws = player_ws_client("Alice")
    participant_ws.emit("join_lobby", {})
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


def test_start_game_defaults_allow_internal_clipboard_true():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1")
    ws = admin_ws_client()
    with patch("ws_handler.gevent.spawn"):
        ws.emit("start_game", {})
    assert game_manager.game.allow_internal_clipboard is True


def test_start_game_can_disable_internal_clipboard():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1")
    ws = admin_ws_client()
    with patch("ws_handler.gevent.spawn"):
        ws.emit("start_game", {"allow_internal_clipboard": False})
    assert game_manager.game.allow_internal_clipboard is False


# --- join_game ---

def test_join_game_with_valid_token_gets_game_state():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1", "discord-Alice")
    start_game(g)
    token = list(g.participants.keys())[0]
    ws = player_ws_client("Alice")
    ws.emit("join_game", {"token": token})
    received = ws.get_received()
    state_msgs = [m for m in received if m["name"] == "game_state"]
    assert len(state_msgs) == 1
    assert state_msgs[0]["args"][0]["status"] == "active"


def test_join_game_with_invalid_token_gets_game_locked():
    g = create_game()
    start_game(g)
    ws = player_ws_client("Nobody")
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


# --- socket authentication ---

def test_join_lobby_requires_a_discord_session():
    ws = socketio.test_client(app)
    ws.emit("join_lobby", {"name": "Impostor"})
    names = [m["name"] for m in ws.get_received()]
    assert names == ["auth_required"]
    assert game_manager.game is None or len(game_manager.game.lobby) == 0


def test_join_lobby_ignores_client_supplied_name():
    ws = player_ws_client("Alice")
    ws.emit("join_lobby", {"name": "Totally Not Alice"})
    ws.get_received()
    assert [e.name for e in game_manager.game.lobby.values()] == ["Alice"]


def test_join_game_requires_a_discord_session():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1", "discord-Alice")
    start_game(g)
    token = list(g.participants.keys())[0]
    ws = socketio.test_client(app)
    ws.emit("join_game", {"token": token})
    names = [m["name"] for m in ws.get_received()]
    assert names == ["auth_required"]


def test_join_game_rejects_another_players_token():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1", "discord-Alice")
    start_game(g)
    alice_token = list(g.participants.keys())[0]
    ws = player_ws_client("Mallory")
    ws.emit("join_game", {"token": alice_token})
    names = [m["name"] for m in ws.get_received()]
    assert "game_locked" in names
    assert "game_state" not in names
    # Alice's seat must not have been hijacked.
    assert g.participants[alice_token].discord_id == "discord-Alice"


def test_join_game_recovers_seat_by_identity_when_token_is_lost():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1", "discord-Alice")
    start_game(g)
    token = list(g.participants.keys())[0]
    ws = player_ws_client("Alice")
    ws.emit("join_game", {})  # localStorage wiped
    received = ws.get_received()
    names = [m["name"] for m in received]
    assert "game_state" in names
    reissued = [m for m in received if m["name"] == "token_assigned"]
    assert len(reissued) == 1
    assert reissued[0]["args"][0]["token"] == token


# --- players must never receive each other's source ---

def test_join_game_state_excludes_other_participants_code():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1", "discord-Alice")
    add_to_lobby(g, None, "Bob", "sid2", "discord-Bob")
    start_game(g)
    alice_token = next(t for t, p in g.participants.items() if p.name == "Alice")
    bob_token = next(t for t, p in g.participants.items() if p.name == "Bob")
    g.participants[bob_token].html = "<p>bob secret</p>"

    ws = player_ws_client("Alice")
    ws.emit("join_game", {"token": alice_token})
    state = [m for m in ws.get_received() if m["name"] == "game_state"][0]["args"][0]

    assert set(state["participants"]) == {alice_token}
    assert "bob secret" not in json.dumps(state)


def test_code_update_is_not_broadcast_to_other_players():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1", "discord-Alice")
    add_to_lobby(g, None, "Bob", "sid2", "discord-Bob")
    start_game(g)
    alice_token = next(t for t, p in g.participants.items() if p.name == "Alice")
    bob_token = next(t for t, p in g.participants.items() if p.name == "Bob")

    alice_ws = player_ws_client("Alice")
    alice_ws.emit("join_game", {"token": alice_token})
    alice_ws.get_received()
    bob_ws = player_ws_client("Bob")
    bob_ws.emit("join_game", {"token": bob_token})
    bob_ws.get_received()

    bob_ws.emit("code_update", {"html": "<p>bob secret</p>", "css": "", "js": ""})

    assert json.dumps(alice_ws.get_received()).find("bob secret") == -1
    assert g.participants[bob_token].html == "<p>bob secret</p>"


def test_code_update_reaches_admin_watchers():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1", "discord-Alice")
    start_game(g)
    token = next(iter(g.participants))

    admin_ws = admin_ws_client()
    admin_ws.emit("watch_game", {})
    admin_ws.get_received()
    player_ws = player_ws_client("Alice")
    player_ws.emit("join_game", {"token": token})
    player_ws.get_received()

    player_ws.emit("code_update", {"html": "<p>alice</p>", "css": "", "js": ""})

    updates = [m for m in admin_ws.get_received() if m["name"] == "participant_update"]
    assert len(updates) == 1
    assert updates[0]["args"][0]["html"] == "<p>alice</p>"


def test_penalties_reach_the_player_and_admins_but_not_other_players():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1", "discord-Alice")
    add_to_lobby(g, None, "Bob", "sid2", "discord-Bob")
    start_game(g)
    alice_token = next(t for t, p in g.participants.items() if p.name == "Alice")
    bob_token = next(t for t, p in g.participants.items() if p.name == "Bob")

    admin_ws = admin_ws_client()
    admin_ws.emit("watch_game", {})
    admin_ws.get_received()
    alice_ws = player_ws_client("Alice")
    alice_ws.emit("join_game", {"token": alice_token})
    alice_ws.get_received()
    bob_ws = player_ws_client("Bob")
    bob_ws.emit("join_game", {"token": bob_token})
    bob_ws.get_received()

    bob_ws.emit("tab_out", {})

    assert [m["name"] for m in bob_ws.get_received()] == ["penalty"]
    assert [m["name"] for m in alice_ws.get_received()] == []
    admin_msgs = [m for m in admin_ws.get_received() if m["name"] == "participant_update"]
    assert admin_msgs[0]["args"][0]["tab_out_count"] == 1


def test_event_end_gives_players_no_one_elses_work():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1", "discord-Alice")
    add_to_lobby(g, None, "Bob", "sid2", "discord-Bob")
    start_game(g)
    alice_token = next(t for t, p in g.participants.items() if p.name == "Alice")
    bob_token = next(t for t, p in g.participants.items() if p.name == "Bob")
    g.participants[bob_token].html = "<p>bob secret</p>"

    alice_ws = player_ws_client("Alice")
    alice_ws.emit("join_game", {"token": alice_token})
    alice_ws.get_received()
    admin_ws = admin_ws_client()
    admin_ws.emit("watch_game", {})
    admin_ws.get_received()

    admin_ws.emit("end_event", {})

    alice_end = [m for m in alice_ws.get_received() if m["name"] == "event_end"]
    assert len(alice_end) == 1
    assert "bob secret" not in json.dumps(alice_end)
    admin_end = [m for m in admin_ws.get_received() if m["name"] == "event_end"]
    assert "bob secret" in json.dumps(admin_end)


# --- timer lifecycle ---

def test_timer_stops_when_the_game_is_replaced():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1", "discord-Alice")
    start_game(g)
    ticker = gevent.spawn(ws_handler._run_timer)
    gevent.sleep(0)
    game_manager.game = create_game()  # e.g. a reset that never ended the round
    ticker.join(timeout=3)
    assert ticker.ready(), "timer greenlet leaked after its game was replaced"


# --- crash recovery, end to end ---

def test_player_rejoins_a_game_restored_from_a_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("RESULTS_DIR", str(tmp_path))
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1", "discord-Alice")
    start_game(g)
    token = next(iter(g.participants))
    g.participants[token].html = "<h1>half finished</h1>"
    game_manager.save_state_snapshot(g)

    game_manager.game = None  # the container restarts
    restored = game_manager.load_state_snapshot()
    assert restored.status == "active"

    ws = player_ws_client("Alice")
    ws.emit("join_game", {"token": token})
    state = [m for m in ws.get_received() if m["name"] == "game_state"][0]["args"][0]
    assert state["participants"][token]["html"] == "<h1>half finished</h1>"
    # The reconnecting socket takes over the seat that lost its sid on restart.
    assert game_manager.game.participants[token].sid != ""


def test_resume_timer_only_spawns_for_an_active_game(tmp_path, monkeypatch):
    monkeypatch.setenv("RESULTS_DIR", str(tmp_path))
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1", "discord-Alice")
    with patch("ws_handler.gevent.spawn") as mock_spawn:
        ws_handler.resume_timer_if_active()  # still waiting
        assert mock_spawn.call_count == 0
        start_game(g)
        ws_handler.resume_timer_if_active()
        assert mock_spawn.call_count == 1
        end_game_state = game_manager.game
        end_game_state.ended_at = time.time()
        end_game_state.status = "ended"
        ws_handler.resume_timer_if_active()
        assert mock_spawn.call_count == 1


# --- sign-up gate ---
#
# Sign-ups closed means the event is not open to players yet. The clients
# route non-admins back to the landing page; these lock in the server half,
# which is what holds when someone goes straight to /lobby.

def test_join_lobby_is_refused_while_signups_are_closed():
    with patch.dict(game_manager.settings, {"signup_open": False}):
        ws = player_ws_client("Alice")
        ws.emit("join_lobby", {})
        received = ws.get_received()
    assert [m["name"] for m in received] == ["signup_closed"]
    assert game_manager.game is None or not game_manager.game.lobby


def test_join_lobby_admits_an_admin_while_signups_are_closed():
    with patch.dict(game_manager.settings, {"signup_open": False}):
        ws = admin_ws_client()
        ws.emit("join_lobby", {})
        received = ws.get_received()
    assert "signup_closed" not in [m["name"] for m in received]
    assert [e.name for e in game_manager.game.lobby.values()] == ["AdminUser"]


def test_join_lobby_admits_players_once_signups_open():
    with patch.dict(game_manager.settings, {"signup_open": True}):
        ws = player_ws_client("Alice")
        ws.emit("join_lobby", {})
        received = ws.get_received()
    assert "signup_closed" not in [m["name"] for m in received]
    assert [e.name for e in game_manager.game.lobby.values()] == ["Alice"]


def test_closing_signups_does_not_evict_an_active_participant():
    """A player already in a running game keeps playing."""
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid-alice", "discord-Alice")
    start_game(g)
    with patch.dict(game_manager.settings, {"signup_open": False}):
        ws = player_ws_client("Alice")
        ws.emit("join_game", {})
        received = ws.get_received()
    names = [m["name"] for m in received]
    assert "game_state" in names
    assert "signup_closed" not in names
