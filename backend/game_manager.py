from __future__ import annotations

import json
import os
import secrets
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, Tuple

BACKUP_FILE = "game_backup.json"
BACKUP_INTERVAL = 30

_PENALTY_SCHEDULE = [5, 25, 60, 120, 240, 480, 960]


@dataclass
class LobbyEntry:
    name: str
    sid: str

    def to_dict(self) -> dict:
        return {"name": self.name}


@dataclass
class Participant:
    id: str
    name: str
    sid: str
    html: str = ""
    css: str = ""
    js: str = ""
    penalty_ms: int = 0
    tab_out_count: int = 0
    copy_attempt_count: int = 0
    submitted_at: Optional[float] = None
    final_html: Optional[str] = None
    final_css: Optional[str] = None
    final_js: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "html": self.html,
            "css": self.css,
            "js": self.js,
            "penalty_ms": self.penalty_ms,
            "tab_out_count": self.tab_out_count,
            "copy_attempt_count": self.copy_attempt_count,
            "submitted_at": self.submitted_at,
            "final_html": self.final_html,
            "final_css": self.final_css,
            "final_js": self.final_js,
        }


@dataclass
class GameState:
    status: str = "waiting"  # "waiting" | "active" | "ended"
    duration_ms: int = 45 * 60 * 1000
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    lobby: dict = field(default_factory=dict)   # token -> LobbyEntry
    participants: dict = field(default_factory=dict)  # token -> Participant

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "duration_ms": self.duration_ms,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "lobby_count": len(self.lobby),
            "participants": {t: p.to_dict() for t, p in self.participants.items()},
        }


game: Optional[GameState] = None


def get_or_create_game() -> GameState:
    global game
    if game is None:
        game = GameState()
    return game


def create_game(duration_ms: int = 45 * 60 * 1000) -> GameState:
    global game
    game = GameState(duration_ms=duration_ms)
    return game


def reset_game(duration_ms: int = 45 * 60 * 1000) -> GameState:
    """Replace the current game with a fresh waiting game, preserving nothing."""
    global game
    game = GameState(duration_ms=duration_ms)
    return game


def add_to_lobby(g: GameState, token: Optional[str], name: str, sid: str) -> Tuple[str, LobbyEntry]:
    if token and token in g.lobby:
        entry = g.lobby[token]
        entry.sid = sid
        return token, entry
    new_token = secrets.token_urlsafe(8)
    entry = LobbyEntry(name=name, sid=sid)
    g.lobby[new_token] = entry
    return new_token, entry


def start_game(g: GameState) -> None:
    for token, entry in g.lobby.items():
        g.participants[token] = Participant(
            id=str(uuid.uuid4()),
            name=entry.name,
            sid=entry.sid,
        )
    g.lobby.clear()
    g.status = "active"
    g.started_at = time.time()


def end_game(g: GameState) -> None:
    auto_snapshot_all(g)
    g.status = "ended"
    g.ended_at = time.time()


def get_participant_by_sid(sid: str) -> Optional[Tuple[str, Participant]]:
    if game is None:
        return None
    for token, p in game.participants.items():
        if p.sid == sid:
            return token, p
    return None


def apply_penalty(sid: str) -> Optional[dict]:
    result = get_participant_by_sid(sid)
    if not result:
        return None
    _, participant = result
    idx = min(participant.tab_out_count, len(_PENALTY_SCHEDULE) - 1)
    participant.penalty_ms += _PENALTY_SCHEDULE[idx] * 1000
    participant.tab_out_count += 1
    return {"penalty_ms": participant.penalty_ms, "tab_out_count": participant.tab_out_count}


def record_copy_attempt(sid: str) -> Optional[dict]:
    result = get_participant_by_sid(sid)
    if not result:
        return None
    _, participant = result
    participant.copy_attempt_count += 1
    return {"copy_attempt_count": participant.copy_attempt_count}


def auto_snapshot_all(g: GameState) -> None:
    for participant in g.participants.values():
        if participant.submitted_at is None:
            participant.final_html = participant.html
            participant.final_css = participant.css
            participant.final_js = participant.js
            participant.submitted_at = time.time()


def snapshot_participant(sid: str) -> None:
    result = get_participant_by_sid(sid)
    if not result:
        return
    _, participant = result
    participant.final_html = participant.html
    participant.final_css = participant.css
    participant.final_js = participant.js
    participant.submitted_at = time.time()


def _backup_loop() -> None:
    while True:
        time.sleep(BACKUP_INTERVAL)
        if game is None:
            continue
        data = game.to_dict()
        dir_ = os.path.dirname(os.path.abspath(BACKUP_FILE)) or "."
        with tempfile.NamedTemporaryFile("w", dir=dir_, delete=False, suffix=".tmp") as f:
            json.dump(data, f)
            tmp_path = f.name
        os.replace(tmp_path, BACKUP_FILE)


_backup_thread = threading.Thread(target=_backup_loop, daemon=True, name="game-backup")
_backup_thread.start()
