from __future__ import annotations

import os
import re
import secrets
import time
import uuid
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Tuple


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
    allow_internal_clipboard: bool = True  # copy/paste round-tripped within a participant's own editor
    lobby: dict = field(default_factory=dict)   # token -> LobbyEntry
    participants: dict = field(default_factory=dict)  # token -> Participant

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "duration_ms": self.duration_ms,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "allow_internal_clipboard": self.allow_internal_clipboard,
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
    try:
        save_results(g)
    except OSError as exc:
        print(f"[results] failed to save built documents: {exc}")


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
    if participant.submitted_at is not None:
        return None
    participant.tab_out_count += 1
    return {"tab_out_count": participant.tab_out_count}


def record_copy_attempt(sid: str) -> Optional[dict]:
    result = get_participant_by_sid(sid)
    if not result:
        return None
    _, participant = result
    if participant.submitted_at is not None:
        return None
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


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")
    return cleaned or "participant"


def _build_document(name: str, html: str, css: str, js: str) -> str:
    """Compose a single standalone, runnable HTML document from a
    participant's html/css/js -- the same pieces the live preview renders."""
    safe_js = js.replace("</script>", "<\\/script>")
    return (
        "<!DOCTYPE html>\n<html>\n<head>\n<meta charset=\"utf-8\">\n"
        f"<title>{name}</title>\n"
        f"<style>{css}</style>\n"
        "</head>\n<body>\n"
        f"{html}\n"
        f"<script>{safe_js}</script>\n"
        "</body>\n</html>\n"
    )


def save_results(g: GameState) -> Optional[str]:
    """Write each participant's final built document (html+css+js) to disk.

    Called once when the event ends. Each event gets its own timestamped
    directory so successive rounds don't overwrite each other. Returns the
    output directory, or None if there were no participants to save.
    """
    if not g.participants:
        return None
    results_dir = os.environ.get("RESULTS_DIR", "results")
    out_dir = os.path.join(results_dir, f"event-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    os.makedirs(out_dir, exist_ok=True)
    for token, p in g.participants.items():
        html = p.final_html if p.final_html is not None else p.html
        css = p.final_css if p.final_css is not None else p.css
        js = p.final_js if p.final_js is not None else p.js
        doc = _build_document(p.name, html, css, js)
        fname = f"{_safe_filename(p.name)}-{token}.html"
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8") as f:
            f.write(doc)
    return out_dir
