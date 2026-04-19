"""Tests for WebSocket event handlers in ws_handler.py."""
from gevent import monkey
monkey.patch_all()

import time
import pytest
from unittest.mock import patch, MagicMock
from app import app, socketio
from room_manager import rooms, get_or_create_room, get_participant
import ws_handler


@pytest.fixture(autouse=True)
def clear_rooms():
    rooms.clear()
    yield
    rooms.clear()


def join_room_as(room_code, name, role="participant"):
    """Helper: connect a test client and join a room, return (client, token)."""
    client = socketio.test_client(app)
    with patch("ws_handler.gevent.spawn"):
        client.emit("join", {"room_code": room_code, "name": name, "role": role})
    received = client.get_received()
    token = None
    for msg in received:
        if msg["name"] == "token_assigned":
            token = msg["args"][0]["token"]
    return client, token


# --- multi-client sync ---

def test_two_clients_both_receive_room_state_with_both_participants():
    clientA, tokenA = join_room_as("TEST", "Alice")
    # Join B without using the helper so we can capture its initial messages
    clientB = socketio.test_client(app)
    with patch("ws_handler.gevent.spawn"):
        clientB.emit("join", {"room_code": "TEST", "name": "Bob", "role": "participant"})
    recvB = clientB.get_received()
    recvA = clientA.get_received()  # picks up room_state broadcast from Bob's join
    tokenB = next(m["args"][0]["token"] for m in recvB if m["name"] == "token_assigned")
    stateA = next(m for m in reversed(recvA) if m["name"] == "room_state")
    stateB = next(m for m in reversed(recvB) if m["name"] == "room_state")
    assert tokenA in stateA["args"][0]["participants"]
    assert tokenB in stateA["args"][0]["participants"]
    assert tokenA in stateB["args"][0]["participants"]
    assert tokenB in stateB["args"][0]["participants"]


def test_code_update_from_a_reaches_b_as_participant_update():
    clientA, _ = join_room_as("TEST", "Alice")
    clientB, _ = join_room_as("TEST", "Bob", role="presenter")
    clientA.get_received()
    clientB.get_received()
    clientA.emit("code_update", {"html": "<h1>hello</h1>", "css": "h1{}"})
    recvB = clientB.get_received()
    updates = [m for m in recvB if m["name"] == "participant_update"]
    assert len(updates) == 1
    assert updates[0]["args"][0]["html"] == "<h1>hello</h1>"


def test_submit_reflected_in_room_state():
    clientA, tokenA = join_room_as("TEST", "Alice")
    clientB, _ = join_room_as("TEST", "Bob", role="presenter")
    clientA.get_received()
    clientB.get_received()
    clientA.emit("submit", {})
    recvB = clientB.get_received()
    state = next((m for m in recvB if m["name"] == "room_state"), None)
    assert state is not None
    assert state["args"][0]["participants"][tokenA]["submitted_at"] is not None


def test_reconnect_with_token_restores_state():
    clientA, tokenA = join_room_as("TEST", "Alice")
    room = rooms["TEST"]
    room.participants[tokenA].html = "<p>saved</p>"
    room.participants[tokenA].css = "p{}"
    # Simulate reconnect: new client with existing token
    clientA2 = socketio.test_client(app)
    with patch("ws_handler.gevent.spawn"):
        clientA2.emit("join", {"room_code": "TEST", "name": "Alice", "role": "participant", "token": tokenA})
    received = clientA2.get_received()
    state = next(m for m in received if m["name"] == "room_state")
    participant = state["args"][0]["participants"][tokenA]
    assert participant["html"] == "<p>saved</p>"
    assert participant["css"] == "p{}"


# --- handle_join edge cases ---

def test_handle_join_missing_room_code_is_noop():
    client = socketio.test_client(app)
    with patch("ws_handler.gevent.spawn") as mock_spawn:
        client.emit("join", {"name": "Alice"})
        mock_spawn.assert_not_called()
    assert len(rooms) == 0


# --- tab_out ---

def test_tab_out_no_penalty_if_not_in_room():
    # Client connected but never joined — apply_penalty returns {} → early return
    client = socketio.test_client(app)
    client.emit("tab_out", {})
    received = client.get_received()
    assert not any(m["name"] == "penalty" for m in received)


def test_tab_out_emits_penalty():
    client, _ = join_room_as("TEST", "Alice")
    client.emit("tab_out", {})
    received = client.get_received()
    penalty_events = [m for m in received if m["name"] == "penalty"]
    assert len(penalty_events) == 1
    assert penalty_events[0]["args"][0]["tab_out_count"] == 1
    assert penalty_events[0]["args"][0]["penalty_ms"] > 0


def test_tab_out_penalty_escalates():
    client, _ = join_room_as("TEST", "Alice")
    client.emit("tab_out", {})
    client.get_received()
    client.emit("tab_out", {})
    received = client.get_received()
    penalty_events = [m for m in received if m["name"] == "penalty"]
    assert penalty_events[0]["args"][0]["tab_out_count"] == 2


def test_tab_out_penalty_accumulates():
    client, _ = join_room_as("TEST", "Alice")
    client.emit("tab_out", {})
    first = client.get_received()
    client.emit("tab_out", {})
    second = client.get_received()
    first_ms = [m for m in first if m["name"] == "penalty"][0]["args"][0]["penalty_ms"]
    second_ms = [m for m in second if m["name"] == "penalty"][0]["args"][0]["penalty_ms"]
    assert second_ms > first_ms


# --- submit ---

def test_submit_emits_submitted_and_room_state():
    client, _ = join_room_as("TEST", "Alice")
    client.emit("submit", {})
    received = client.get_received()
    names = [m["name"] for m in received]
    assert "submitted" in names
    assert "room_state" in names


def test_submit_snapshots_participant():
    client, token = join_room_as("TEST", "Alice")
    room = rooms["TEST"]
    p = room.participants[token]
    p.html = "<p>done</p>"
    p.css = "p{}"
    client.emit("submit", {})
    assert p.submitted_at is not None
    assert p.final_html == "<p>done</p>"
    assert p.final_css == "p{}"


def test_submit_second_time_is_noop():
    client, token = join_room_as("TEST", "Alice")
    client.emit("submit", {})
    client.get_received()
    room = rooms["TEST"]
    first_submitted_at = room.participants[token].submitted_at
    client.emit("submit", {})
    received = client.get_received()
    submitted_events = [m for m in received if m["name"] == "submitted"]
    assert len(submitted_events) == 0
    assert room.participants[token].submitted_at == first_submitted_at


# --- code_update ---

def test_code_update_updates_html_and_css():
    client, token = join_room_as("TEST", "Alice")
    client.emit("code_update", {"html": "<h1>hi</h1>", "css": "h1{}"})
    room = rooms["TEST"]
    p = room.participants[token]
    assert p.html == "<h1>hi</h1>"
    assert p.css == "h1{}"


def test_code_update_emits_participant_update():
    client, _ = join_room_as("TEST", "Alice")
    client.emit("code_update", {"html": "<b>bold</b>", "css": ""})
    received = client.get_received()
    updates = [m for m in received if m["name"] == "participant_update"]
    assert len(updates) == 1
    assert updates[0]["args"][0]["html"] == "<b>bold</b>"


def test_code_update_noop_if_submitted():
    client, token = join_room_as("TEST", "Alice")
    client.emit("submit", {})
    client.get_received()
    client.emit("code_update", {"html": "<p>after submit</p>", "css": ""})
    room = rooms["TEST"]
    assert room.participants[token].html != "<p>after submit</p>"


# --- end_event ---

def test_end_event_admin_ends_room():
    client, _ = join_room_as("TEST", "Admin", role="admin")
    client.emit("end_event", {})
    received = client.get_received()
    end_events = [m for m in received if m["name"] == "event_end"]
    assert len(end_events) == 1
    assert rooms["TEST"].ended_at is not None


def test_end_event_non_admin_cannot_end_room():
    client, _ = join_room_as("TEST", "Alice", role="participant")
    client.emit("end_event", {})
    assert rooms["TEST"].ended_at is None


def test_end_event_snapshots_all_participants():
    client1, token1 = join_room_as("TEST", "Admin", role="admin")
    client2, token2 = join_room_as("TEST", "Alice", role="participant")
    room = rooms["TEST"]
    room.participants[token1].html = "<p>admin</p>"
    room.participants[token2].html = "<p>alice</p>"
    client1.emit("end_event", {})
    assert room.participants[token1].submitted_at is not None
    assert room.participants[token2].submitted_at is not None


# --- fire_event_end ---

def test_fire_event_end_emits_event_end():
    client, token = join_room_as("TEST", "Alice")
    room = rooms["TEST"]
    ws_handler.fire_event_end("TEST")
    received = client.get_received()
    end_events = [m for m in received if m["name"] == "event_end"]
    assert len(end_events) == 1


def test_fire_event_end_unknown_room_is_noop():
    ws_handler.fire_event_end("GHOST")  # should not raise


def test_fire_event_end_auto_snapshots():
    client, token = join_room_as("TEST", "Alice")
    room = rooms["TEST"]
    room.participants[token].html = "<p>final</p>"
    ws_handler.fire_event_end("TEST")
    assert room.participants[token].submitted_at is not None
    assert room.participants[token].final_html == "<p>final</p>"


def test_timer_expiry_captures_last_code_update():
    """final_html/css match the last code_update sent before timer fires."""
    client, token = join_room_as("TEST", "Alice")
    client.emit("code_update", {"html": "<h1>v1</h1>", "css": "h1{}"})
    client.emit("code_update", {"html": "<h1>v2</h1>", "css": "h1{color:red}"})
    client.get_received()
    ws_handler.fire_event_end("TEST")
    room = rooms["TEST"]
    p = room.participants[token]
    assert p.final_html == "<h1>v2</h1>"
    assert p.final_css == "h1{color:red}"


# --- run_timer ---

def test_run_timer_exits_early_if_no_started_at():
    room = get_or_create_room("TEST")
    # started_at is None by default — should return immediately
    with patch("ws_handler.gevent.sleep") as mock_sleep:
        ws_handler.run_timer("TEST")
        mock_sleep.assert_not_called()


def test_run_timer_exits_early_if_room_missing():
    with patch("ws_handler.gevent.sleep") as mock_sleep:
        ws_handler.run_timer("GHOST")
        mock_sleep.assert_not_called()


def test_run_timer_calls_fire_event_end_when_elapsed():
    room = get_or_create_room("TEST")
    room.started_at = time.time() - 1  # 1 second ago
    room.duration_ms = 0  # elapsed (~1000ms) will exceed this immediately

    with patch("ws_handler.gevent.sleep"), \
         patch("ws_handler.fire_event_end") as mock_end, \
         patch("ws_handler.socketio.emit"):
        ws_handler.run_timer("TEST")
        mock_end.assert_called_once_with("TEST")


def test_run_timer_emits_timer_tick():
    room = get_or_create_room("TEST")
    room.started_at = time.time() - 1
    room.duration_ms = 0

    emitted = []
    with patch("ws_handler.gevent.sleep"), \
         patch("ws_handler.fire_event_end"), \
         patch("ws_handler.socketio.emit", side_effect=lambda *a, **kw: emitted.append(a[0])):
        ws_handler.run_timer("TEST")

    assert "timer_tick" in emitted


def test_run_timer_exits_when_ended_at_set():
    room = get_or_create_room("TEST")
    room.started_at = time.time()
    room.ended_at = time.time()  # already ended before loop starts
    room.duration_ms = 45 * 60 * 1000

    with patch("ws_handler.gevent.sleep") as mock_sleep, \
         patch("ws_handler.socketio.emit"):
        ws_handler.run_timer("TEST")
        mock_sleep.assert_not_called()
