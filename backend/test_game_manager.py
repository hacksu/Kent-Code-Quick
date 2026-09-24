"""Unit tests for game_manager."""
from gevent import monkey
monkey.patch_all()

import json
import time
import pytest
import game_manager
from game_manager import (
    GameState, Participant, LobbyEntry,
    create_game, get_or_create_game, add_to_lobby, reset_game as reset_game_state,
    start_game, end_game, apply_penalty, record_copy_attempt,
    auto_snapshot_all, get_participant_by_sid,
    find_participant_token_by_discord_id,
    save_state_snapshot, load_state_snapshot, clear_state_snapshot,
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
    assert result == {"tab_out_count": 1}
    result2 = apply_penalty("sid1")
    assert result2 == {"tab_out_count": 2}


def test_apply_penalty_unknown_sid_returns_none():
    create_game()
    result = apply_penalty("unknown-sid")
    assert result is None


def test_record_copy_attempt_noop_after_game_ends():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1")
    start_game(g)
    end_game(g)
    result = record_copy_attempt("sid1")
    assert result is None
    p = list(g.participants.values())[0]
    assert p.copy_attempt_count == 0


def test_apply_penalty_noop_after_game_ends():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1")
    start_game(g)
    end_game(g)
    result = apply_penalty("sid1")
    assert result is None


def test_record_copy_attempt():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1")
    start_game(g)
    result = record_copy_attempt("sid1")
    assert result == {"copy_attempt_count": 1}


def test_auto_snapshot_all_skips_already_finalized():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1")
    add_to_lobby(g, None, "Bob", "sid2")
    start_game(g)
    participants = list(g.participants.values())
    participants[0].html = "<p>alice</p>"
    participants[0].final_html = "<p>alice snapshot</p>"
    participants[0].submitted_at = time.time()
    first_submitted_at = participants[0].submitted_at
    auto_snapshot_all(g)
    assert participants[0].submitted_at == first_submitted_at
    assert participants[0].final_html == "<p>alice snapshot</p>"


def test_to_dict_structure():
    g = create_game(duration_ms=30_000)
    add_to_lobby(g, None, "Alice", "sid1")
    d = g.to_dict()
    assert d["status"] == "waiting"
    assert d["duration_ms"] == 30_000
    assert d["allow_internal_clipboard"] is True
    assert d["lobby_count"] == 1
    assert d["lobby_names"] == ["Alice"]
    assert d["participants"] == {}


# --- player-scoped state ---

def test_to_player_dict_hides_other_participants_work():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1", "discord-alice")
    add_to_lobby(g, None, "Bob", "sid2", "discord-bob")
    start_game(g)
    alice_token = next(t for t, p in g.participants.items() if p.name == "Alice")
    g.participants[alice_token].html = "<p>alice</p>"
    bob_token = next(t for t, p in g.participants.items() if p.name == "Bob")
    g.participants[bob_token].html = "<p>bob secret</p>"

    state = g.to_player_dict(alice_token)

    assert set(state["participants"]) == {alice_token}
    assert state["participants"][alice_token]["html"] == "<p>alice</p>"
    assert "bob secret" not in json.dumps(state)


def test_to_player_dict_with_unknown_token_exposes_nothing():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1", "discord-alice")
    start_game(g)
    assert g.to_player_dict("nope")["participants"] == {}
    assert g.to_player_dict(None)["participants"] == {}


# --- lobby seating by identity ---

def test_add_to_lobby_reuses_seat_for_same_discord_id():
    g = create_game()
    token1, _ = add_to_lobby(g, None, "Alice", "sid1", "discord-alice")
    # Same person, new browser session with no remembered token.
    token2, entry = add_to_lobby(g, None, "Alice", "sid2", "discord-alice")
    assert token1 == token2
    assert len(g.lobby) == 1
    assert entry.sid == "sid2"


def test_add_to_lobby_separates_distinct_discord_ids():
    g = create_game()
    token1, _ = add_to_lobby(g, None, "Alice", "sid1", "discord-alice")
    token2, _ = add_to_lobby(g, None, "Bob", "sid2", "discord-bob")
    assert token1 != token2
    assert len(g.lobby) == 2


def test_start_game_carries_discord_id_to_participant():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1", "discord-alice")
    start_game(g)
    assert next(iter(g.participants.values())).discord_id == "discord-alice"


def test_find_participant_token_by_discord_id():
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1", "discord-alice")
    start_game(g)
    token = next(iter(g.participants))
    assert find_participant_token_by_discord_id(g, "discord-alice") == token
    assert find_participant_token_by_discord_id(g, "discord-nobody") is None
    assert find_participant_token_by_discord_id(g, "") is None


# --- crash recovery ---

def test_snapshot_round_trip_preserves_participant_work(tmp_path, monkeypatch):
    monkeypatch.setenv("RESULTS_DIR", str(tmp_path))
    g = create_game(duration_ms=30_000)
    add_to_lobby(g, None, "Alice", "sid1", "discord-alice")
    start_game(g)
    token = next(iter(g.participants))
    g.participants[token].html = "<h1>work in progress</h1>"
    g.participants[token].tab_out_count = 3
    save_state_snapshot(g)

    game_manager.game = None  # simulate a restart
    restored = load_state_snapshot()

    assert restored is not None
    assert game_manager.game is restored
    assert restored.status == "active"
    assert restored.duration_ms == 30_000
    assert restored.participants[token].html == "<h1>work in progress</h1>"
    assert restored.participants[token].tab_out_count == 3
    assert restored.participants[token].discord_id == "discord-alice"
    # Socket ids do not survive a restart; clients rebind on reconnect.
    assert restored.participants[token].sid == ""


def test_snapshot_round_trip_preserves_lobby(tmp_path, monkeypatch):
    monkeypatch.setenv("RESULTS_DIR", str(tmp_path))
    g = create_game()
    token, _ = add_to_lobby(g, None, "Alice", "sid1", "discord-alice")
    save_state_snapshot(g)
    game_manager.game = None
    restored = load_state_snapshot()
    assert restored.lobby[token].name == "Alice"
    assert restored.lobby[token].discord_id == "discord-alice"


def test_load_state_snapshot_returns_none_without_a_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("RESULTS_DIR", str(tmp_path))
    assert load_state_snapshot() is None


def test_end_game_writes_a_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("RESULTS_DIR", str(tmp_path))
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1", "discord-alice")
    start_game(g)
    end_game(g)
    assert (tmp_path / "state.json").exists()


def test_reset_game_clears_the_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("RESULTS_DIR", str(tmp_path))
    g = create_game()
    add_to_lobby(g, None, "Alice", "sid1", "discord-alice")
    save_state_snapshot(g)
    assert (tmp_path / "state.json").exists()
    reset_game_state()
    assert not (tmp_path / "state.json").exists()
