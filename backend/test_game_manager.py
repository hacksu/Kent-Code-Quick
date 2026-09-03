"""Unit tests for game_manager."""
from gevent import monkey
monkey.patch_all()

import time
import pytest
import game_manager
from game_manager import (
    GameState, Participant, LobbyEntry,
    create_game, get_or_create_game, add_to_lobby,
    start_game, end_game, apply_penalty, record_copy_attempt,
    snapshot_participant, auto_snapshot_all, get_participant_by_sid,
    _PENALTY_SCHEDULE,
)


@pytest.fixture(autouse=True)
def reset_game():
    game_manager.game = None
    yield
    game_manager.game = None


def test_get_or_create_game_creates_on_first_call():
    g = get_or_create_game()
    assert g.status == "waiting"
    assert g.participants == {}
    assert g.lobby == {}


def test_get_or_create_game_returns_same_instance():
    g1 = get_or_create_game()
    g2 = get_or_create_game()
    assert g1 is g2


def test_create_game_resets_state():
    g1 = create_game(duration_ms=60_000)
    g2 = create_game(duration_ms=120_000)
    assert g1 is not g2
    assert g2.duration_ms == 120_000


def test_add_to_lobby_new_entry():
    g = create_game()
    token, entry = add_to_lobby(g, None, "Alice", "sid1")
    assert token in g.lobby
    assert g.lobby[token].name == "Alice"
    assert g.lobby[token].sid == "sid1"


def test_add_to_lobby_rehydrates_existing_token():
    g = create_game()
    token, _ = add_to_lobby(g, None, "Alice", "sid1")
    token2, entry2 = add_to_lobby(g, token, "Alice", "sid2")
    assert token == token2
    assert entry2.sid == "sid2"
    assert len(g.lobby) == 1


def test_start_game_moves_lobby_to_participants():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1")
    add_to_lobby(g, None, "Bob", "sid2")
    start_game(g)
    assert g.status == "active"
    assert g.started_at is not None
    assert len(g.participants) == 2
    assert len(g.lobby) == 0
    names = {p.name for p in g.participants.values()}
    assert names == {"Alice", "Bob"}


def test_end_game_snapshots_all_and_sets_status():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1")
    start_game(g)
    p = list(g.participants.values())[0]
    p.html = "<h1>hi</h1>"
    p.css = "h1 { color: red; }"
    end_game(g)
    assert g.status == "ended"
    assert g.ended_at is not None
    assert p.submitted_at is not None
    assert p.final_html == "<h1>hi</h1>"


def test_apply_penalty_increments_correctly():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1")
    start_game(g)
    result = apply_penalty("sid1")
    assert result is not None
    assert result["penalty_ms"] == _PENALTY_SCHEDULE[0] * 1000
    assert result["tab_out_count"] == 1
    result2 = apply_penalty("sid1")
    assert result2["penalty_ms"] == (_PENALTY_SCHEDULE[0] + _PENALTY_SCHEDULE[1]) * 1000
    assert result2["tab_out_count"] == 2


def test_apply_penalty_unknown_sid_returns_none():
    create_game()
    result = apply_penalty("unknown-sid")
    assert result is None


def test_record_copy_attempt():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1")
    start_game(g)
    result = record_copy_attempt("sid1")
    assert result == {"copy_attempt_count": 1}


def test_snapshot_participant():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1")
    start_game(g)
    p = list(g.participants.values())[0]
    p.html = "<p>hello</p>"
    snapshot_participant("sid1")
    assert p.final_html == "<p>hello</p>"
    assert p.submitted_at is not None


def test_auto_snapshot_all_skips_already_submitted():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1")
    add_to_lobby(g, None, "Bob", "sid2")
    start_game(g)
    participants = list(g.participants.values())
    participants[0].html = "<p>alice</p>"
    snapshot_participant(participants[0].sid)
    first_submitted_at = participants[0].submitted_at
    auto_snapshot_all(g)
    assert participants[0].submitted_at == first_submitted_at


def test_to_dict_structure():
    g = create_game(duration_ms=30_000)
    add_to_lobby(g, None, "Alice", "sid1")
    d = g.to_dict()
    assert d["status"] == "waiting"
    assert d["duration_ms"] == 30_000
    assert d["allow_internal_clipboard"] is True
    assert d["lobby_count"] == 1
    assert d["participants"] == {}
