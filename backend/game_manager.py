from __future__ import annotations

import io
import json
import os
import re
import secrets
import time
import uuid
import zipfile
from datetime import datetime, timezone
from dataclasses import asdict, dataclass, field
from html import escape as html_escape
from typing import List, Optional, Tuple

DEFAULT_DURATION_MS = 100 * 60 * 1000


@dataclass
class LobbyEntry:
    name: str
    sid: str
    discord_id: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name}


@dataclass
class Participant:
    id: str
    name: str
    sid: str
    discord_id: str = ""
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
    duration_ms: int = DEFAULT_DURATION_MS
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
            "lobby_names": [entry.name for entry in self.lobby.values()],
            "participants": {t: p.to_dict() for t, p in self.participants.items()},
        }

    def to_player_dict(self, token: Optional[str]) -> dict:
        state = self.to_dict()
        own = self.participants.get(token) if token else None
        state["participants"] = {token: own.to_dict()} if own is not None else {}
        return state


game: Optional[GameState] = None


def get_or_create_game() -> GameState:
    global game
    if game is None:
        game = GameState()
    return game


def create_game(duration_ms: int = DEFAULT_DURATION_MS) -> GameState:
    global game
    game = GameState(duration_ms=duration_ms)
    clear_state_snapshot()
    return game


def reset_game(duration_ms: int = DEFAULT_DURATION_MS) -> GameState:
    global game
    game = GameState(duration_ms=duration_ms)
    clear_state_snapshot()
    return game


def add_to_lobby(
    g: GameState,
    token: Optional[str],
    name: str,
    sid: str,
    discord_id: str = "",
) -> Tuple[str, LobbyEntry]:
    if token and token in g.lobby:
        entry = g.lobby[token]
        entry.sid = sid
        entry.name = name
        return token, entry
    if discord_id:
        for existing_token, entry in g.lobby.items():
            if entry.discord_id == discord_id:
                entry.sid = sid
                entry.name = name
                return existing_token, entry
    new_token = secrets.token_urlsafe(8)
    entry = LobbyEntry(name=name, sid=sid, discord_id=discord_id)
    g.lobby[new_token] = entry
    return new_token, entry


def find_participant_token_by_discord_id(g: GameState, discord_id: str) -> Optional[str]:
    if not discord_id:
        return None
    for token, p in g.participants.items():
        if p.discord_id == discord_id:
            return token
    return None


def start_game(g: GameState) -> None:
    for token, entry in g.lobby.items():
        g.participants[token] = Participant(
            id=str(uuid.uuid4()),
            name=entry.name,
            sid=entry.sid,
            discord_id=entry.discord_id,
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
    try:
        save_state_snapshot(g)
    except OSError as exc:
        print(f"[results] failed to save state snapshot: {exc}")


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


EXPORT_SCOPE_FINISHED = "finished"
EXPORT_SCOPE_ALL = "all"
EXPORT_SCOPES = (EXPORT_SCOPE_FINISHED, EXPORT_SCOPE_ALL)


def is_finished(p: Participant) -> bool:
    """A project counts as finished once it has been snapshotted.

    Snapshots happen when a participant submits, and for everyone still
    working when the admin ends the event -- so after an event every
    project is finished.
    """
    return p.submitted_at is not None


def final_code(p: Participant) -> Tuple[str, str, str]:
    """The snapshotted code if there is one, else what is in the editor now."""
    return (
        p.final_html if p.final_html is not None else p.html,
        p.final_css if p.final_css is not None else p.css,
        p.final_js if p.final_js is not None else p.js,
    )


def export_entries(g: GameState, scope: str = EXPORT_SCOPE_FINISHED) -> List[Tuple[str, Participant]]:
    """(token, participant) pairs to export, ordered by display name."""
    entries = sorted(g.participants.items(), key=lambda kv: (kv[1].name.lower(), kv[0]))
    if scope == EXPORT_SCOPE_ALL:
        return entries
    return [(token, p) for token, p in entries if is_finished(p)]


def _iso(ts: Optional[float]) -> Optional[str]:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


def _local_time(ts: Optional[float]) -> str:
    if ts is None:
        return "--"
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def _export_project_filename(token: str, p: Participant) -> str:
    return f"{_safe_filename(p.name)}-{token}.html"


def _export_manifest(g: GameState, entries: List[Tuple[str, Participant]], scope: str) -> dict:
    return {
        "exported_at": _iso(time.time()),
        "scope": scope,
        "status": g.status,
        "duration_ms": g.duration_ms,
        "started_at": _iso(g.started_at),
        "ended_at": _iso(g.ended_at),
        "participant_count": len(g.participants),
        "exported_count": len(entries),
        "projects": [
            {
                "token": token,
                "id": p.id,
                "name": p.name,
                "discord_id": p.discord_id,
                "file": f"projects/{_export_project_filename(token, p)}",
                "finished": is_finished(p),
                "submitted_at": _iso(p.submitted_at),
                "tab_out_count": p.tab_out_count,
                "copy_attempt_count": p.copy_attempt_count,
            }
            for token, p in entries
        ],
    }


def _export_index(g: GameState, entries: List[Tuple[str, Participant]], scope: str) -> str:
    """A tiny contact sheet so the zip can be browsed without a server."""
    rows = "\n".join(
        "<tr>"
        f'<td><a href="projects/{html_escape(_export_project_filename(token, p))}">{html_escape(p.name)}</a></td>'
        f"<td>{'yes' if is_finished(p) else 'no'}</td>"
        f"<td>{html_escape(_local_time(p.submitted_at))}</td>"
        f"<td>{p.tab_out_count}</td>"
        f"<td>{p.copy_attempt_count}</td>"
        "</tr>"
        for token, p in entries
    )
    return (
        "<!DOCTYPE html>\n<html>\n<head>\n<meta charset=\"utf-8\">\n"
        "<title>Kent Code Quick -- projects</title>\n"
        "<style>"
        "body{font:14px/1.5 system-ui,sans-serif;margin:2rem;color:#222}"
        "table{border-collapse:collapse}"
        "th,td{border-bottom:1px solid #ddd;padding:.4rem .8rem;text-align:left}"
        "th{font-size:12px;text-transform:uppercase;color:#666}"
        "</style>\n</head>\n<body>\n"
        "<h1>Kent Code Quick</h1>\n"
        f"<p>{len(entries)} project(s), scope <strong>{html_escape(scope)}</strong>. "
        f"Event {html_escape(g.status)}; started {html_escape(_local_time(g.started_at))}, "
        f"ended {html_escape(_local_time(g.ended_at))}.</p>\n"
        "<table>\n<thead><tr><th>Name</th><th>Finished</th><th>Submitted</th>"
        "<th>Tab-outs</th><th>Copy attempts</th></tr></thead>\n"
        f"<tbody>\n{rows}\n</tbody>\n</table>\n"
        "</body>\n</html>\n"
    )


def build_export_archive(
    g: GameState, scope: str = EXPORT_SCOPE_FINISHED
) -> Tuple[bytes, str, int]:
    """Zip every in-scope project into one downloadable archive.

    Returns the zip bytes, a suggested filename, and how many projects
    went in (zero means there was nothing to export).
    """
    if scope not in EXPORT_SCOPES:
        raise ValueError(f"unknown export scope: {scope}")
    entries = export_entries(g, scope)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    root = f"kcq-projects-{stamp}"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        for token, p in entries:
            html_src, css, js = final_code(p)
            archive.writestr(
                f"{root}/projects/{_export_project_filename(token, p)}",
                _build_document(p.name, html_src, css, js),
            )
        archive.writestr(f"{root}/index.html", _export_index(g, entries, scope))
        archive.writestr(
            f"{root}/manifest.json",
            json.dumps(_export_manifest(g, entries, scope), indent=2),
        )
    return buf.getvalue(), f"{root}.zip", len(entries)


def save_results(g: GameState) -> Optional[str]:
    if not g.participants:
        return None
    results_dir = os.environ.get("RESULTS_DIR", "results")
    out_dir = os.path.join(results_dir, f"event-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    os.makedirs(out_dir, exist_ok=True)
    for token, p in g.participants.items():
        html, css, js = final_code(p)
        doc = _build_document(p.name, html, css, js)
        fname = _export_project_filename(token, p)
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8") as f:
            f.write(doc)
    return out_dir


def _state_path() -> str:
    return os.path.join(os.environ.get("RESULTS_DIR", "results"), "state.json")


def save_state_snapshot(g: Optional[GameState] = None) -> Optional[str]:
    g = g if g is not None else game
    if g is None:
        return None
    payload = {
        "status": g.status,
        "duration_ms": g.duration_ms,
        "started_at": g.started_at,
        "ended_at": g.ended_at,
        "allow_internal_clipboard": g.allow_internal_clipboard,
        "lobby": {t: asdict(e) for t, e in g.lobby.items()},
        "participants": {t: asdict(p) for t, p in g.participants.items()},
    }
    path = _state_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    os.replace(tmp, path)
    return path


def load_state_snapshot() -> Optional[GameState]:
    global game
    path = _state_path()
    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, ValueError):
        return None

    restored = GameState(
        status=payload.get("status", "waiting"),
        duration_ms=payload.get("duration_ms", DEFAULT_DURATION_MS),
        started_at=payload.get("started_at"),
        ended_at=payload.get("ended_at"),
        allow_internal_clipboard=payload.get("allow_internal_clipboard", True),
    )
    for token, entry in (payload.get("lobby") or {}).items():
        entry = dict(entry)
        entry["sid"] = ""
        restored.lobby[token] = LobbyEntry(**entry)
    for token, participant in (payload.get("participants") or {}).items():
        participant = dict(participant)
        participant["sid"] = ""
        restored.participants[token] = Participant(**participant)

    game = restored
    return restored


def clear_state_snapshot() -> None:
    try:
        os.remove(_state_path())
    except OSError:
        pass


DEFAULT_SETTINGS = {"signup_open": False}
settings: dict = dict(DEFAULT_SETTINGS)


def _settings_path() -> str:
    return os.path.join(os.environ.get("RESULTS_DIR", "results"), "settings.json")


def get_settings() -> dict:
    return dict(settings)


def save_settings() -> str:
    path = _settings_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(settings, f)
    os.replace(tmp, path)
    return path


def load_settings() -> dict:
    global settings
    try:
        with open(_settings_path(), encoding="utf-8") as f:
            stored = json.load(f)
    except (OSError, ValueError):
        return get_settings()
    if isinstance(stored, dict):
        settings = {k: stored.get(k, v) for k, v in DEFAULT_SETTINGS.items()}
    return get_settings()


def set_signup_open(value: bool) -> dict:
    settings["signup_open"] = bool(value)
    try:
        save_settings()
    except OSError as exc:
        print(f"[settings] failed to persist settings: {exc}")
    return get_settings()
