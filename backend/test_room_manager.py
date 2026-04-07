"""Unit tests for room_manager functions."""
from gevent import monkey
monkey.patch_all()

import json
import os
import time
import pytest
from unittest.mock import patch
from room_manager import (
    RoomState,
    Participant,
    get_or_create_room,
    get_participant,
    apply_penalty,
    auto_snapshot_all,
    snapshot_participant,
    rooms,
    _PENALTY_SCHEDULE,
    _backup_loop,
)


@pytest.fixture(autouse=True)
def clear_rooms():
    rooms.clear()
    yield
    rooms.clear()


# --- get_or_create_room ---

def test_get_or_create_room_creates_new():
    room = get_or_create_room("ABC")
    assert "ABC" in rooms
    assert room.code == "ABC"


def test_get_or_create_room_returns_existing():
    room1 = get_or_create_room("ABC")
    room2 = get_or_create_room("ABC")
    assert room1 is room2


# --- get_participant ---

def test_get_participant_creates_new():
    room = get_or_create_room("ABC")
    token, p = get_participant(room, None, "Alice", "sid1")
    assert token in room.participants
    assert p.name == "Alice"
    assert p.sid == "sid1"
    assert p.role == "participant"


def test_get_participant_reconnect_updates_sid():
    room = get_or_create_room("ABC")
    token, p = get_participant(room, None, "Alice", "sid1")
    token2, p2 = get_participant(room, token, "Alice", "sid2")
    assert token2 == token
    assert p2 is p
    assert p.sid == "sid2"


def test_get_participant_invalid_token_creates_new():
    room = get_or_create_room("ABC")
    token, p = get_participant(room, "not-a-real-token", "Bob", "sid1")
    assert p.name == "Bob"
    assert len(room.participants) == 1


def test_get_participant_role_stored():
    room = get_or_create_room("ABC")
    _, p = get_participant(room, None, "Admin", "sid1", role="admin")
    assert p.role == "admin"


# --- apply_penalty ---

def test_apply_penalty_first_offense():
    room = get_or_create_room("ABC")
    get_participant(room, None, "Alice", "sid1")
    result = apply_penalty("sid1")
    assert result["tab_out_count"] == 1
    assert result["penalty_ms"] == _PENALTY_SCHEDULE[0] * 1000


def test_apply_penalty_escalates():
    room = get_or_create_room("ABC")
    get_participant(room, None, "Alice", "sid1")
    for i in range(4):
        apply_penalty("sid1")
    result = apply_penalty("sid1")
    assert result["tab_out_count"] == 5
    expected = sum(_PENALTY_SCHEDULE[min(i, len(_PENALTY_SCHEDULE) - 1)] for i in range(5)) * 1000
    assert result["penalty_ms"] == expected


def test_apply_penalty_caps_at_schedule_max():
    room = get_or_create_room("ABC")
    get_participant(room, None, "Alice", "sid1")
    # exhaust the schedule
    for _ in range(len(_PENALTY_SCHEDULE) + 2):
        apply_penalty("sid1")
    result = apply_penalty("sid1")
    assert result["penalty_ms"] > 0


def test_apply_penalty_unknown_sid_returns_empty():
    result = apply_penalty("ghost-sid")
    assert result == {}


# --- auto_snapshot_all ---

def test_auto_snapshot_all_snapshots_unsubmitted():
    room = get_or_create_room("ABC")
    _, p = get_participant(room, None, "Alice", "sid1")
    p.html = "<p>hello</p>"
    p.css = "p { color: red; }"
    auto_snapshot_all(room)
    assert p.final_html == "<p>hello</p>"
    assert p.final_css == "p { color: red; }"
    assert p.submitted_at is not None


def test_auto_snapshot_all_skips_already_submitted():
    room = get_or_create_room("ABC")
    _, p = get_participant(room, None, "Alice", "sid1")
    p.html = "<p>original</p>"
    p.submitted_at = 1000.0
    p.final_html = "<p>original</p>"
    auto_snapshot_all(room)
    # submitted_at should not change
    assert p.submitted_at == 1000.0


def test_auto_snapshot_all_multiple_participants():
    room = get_or_create_room("ABC")
    _, p1 = get_participant(room, None, "Alice", "sid1")
    _, p2 = get_participant(room, None, "Bob", "sid2")
    p1.html = "<p>a</p>"
    p2.html = "<p>b</p>"
    auto_snapshot_all(room)
    assert p1.submitted_at is not None
    assert p2.submitted_at is not None


# --- snapshot_participant ---

def test_snapshot_participant_by_sid():
    room = get_or_create_room("ABC")
    _, p = get_participant(room, None, "Alice", "sid1")
    p.html = "<p>hello</p>"
    p.css = "body {}"
    snapshot_participant("sid1")
    assert p.final_html == "<p>hello</p>"
    assert p.final_css == "body {}"
    assert p.submitted_at is not None


def test_snapshot_participant_unknown_sid_no_error():
    snapshot_participant("unknown-sid")  # should not raise


def test_snapshot_participant_only_targets_correct_sid():
    room = get_or_create_room("ABC")
    _, p1 = get_participant(room, None, "Alice", "sid1")
    _, p2 = get_participant(room, None, "Bob", "sid2")
    p1.html = "<p>a</p>"
    p2.html = "<p>b</p>"
    snapshot_participant("sid1")
    assert p1.submitted_at is not None
    assert p2.submitted_at is None


# --- to_dict ---

def test_participant_to_dict_keys():
    p = Participant(id="1", name="Alice", sid="s1")
    d = p.to_dict()
    assert set(d.keys()) == {"id", "name", "sid", "html", "css", "penalty_ms",
                              "tab_out_count", "submitted_at", "final_html", "final_css", "role"}


def test_room_state_to_dict_includes_participants():
    room = get_or_create_room("ABC")
    get_participant(room, None, "Alice", "sid1")
    d = room.to_dict()
    assert d["code"] == "ABC"
    assert len(d["participants"]) == 1


# --- _backup_loop ---

def test_backup_loop_writes_rooms_to_file(tmp_path):
    room = get_or_create_room("ABC")
    get_participant(room, None, "Alice", "sid1")

    backup_file = tmp_path / "room_backup.json"

    calls = {"count": 0}
    def fake_sleep(n):
        calls["count"] += 1
        if calls["count"] > 1:
            raise StopIteration

    with patch("room_manager.time.sleep", side_effect=fake_sleep), \
         patch("room_manager.BACKUP_FILE", str(backup_file)):
        try:
            _backup_loop()
        except StopIteration:
            pass

    assert backup_file.exists()
    data = json.loads(backup_file.read_text())
    assert "ABC" in data
