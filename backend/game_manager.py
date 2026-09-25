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
    paused: bool = False
    paused_at: Optional[float] = None
    pause_duration_ms: float = 0.0
    lobby: dict = field(default_factory=dict)   # token -> LobbyEntry
    participants: dict = field(default_factory=dict)  # token -> Participant

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "duration_ms": self.duration_ms,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "allow_internal_clipboard": self.allow_internal_clipboard,
            "paused": self.paused,
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

# discord_id -> {name, html, css, js, tab_out_count, copy_attempt_count}.
# Staged by restore_from_export() and consumed by start_game() so a restore
# survives a "New Game"/reset that replaces `game` entirely -- participants
# are recreated fresh from the lobby on every start_game() call, so this is
# the only thing that carries restored code across that boundary.
pending_restore: dict = {}


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
        restore = pending_restore.get(entry.discord_id) if entry.discord_id else None
        g.participants[token] = Participant(
            id=str(uuid.uuid4()),
            name=entry.name,
            sid=entry.sid,
            discord_id=entry.discord_id,
            html=restore["html"] if restore else "",
            css=restore["css"] if restore else "",
            js=restore["js"] if restore else "",
            tab_out_count=restore["tab_out_count"] if restore else 0,
            copy_attempt_count=restore["copy_attempt_count"] if restore else 0,
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


def compute_elapsed_ms(g: GameState) -> float:
    if g.started_at is None:
        return 0.0
    end = g.paused_at if (g.paused and g.paused_at is not None) else time.time()
    return (end - g.started_at) * 1000 - g.pause_duration_ms


def pause_game(g: GameState) -> None:
    if g.status != "active" or g.paused:
        return
    g.paused = True
    g.paused_at = time.time()


def resume_game(g: GameState) -> None:
    if g.status != "active" or not g.paused:
        return
    if g.paused_at is not None:
        g.pause_duration_ms += (time.time() - g.paused_at) * 1000
    g.paused = False
    g.paused_at = None


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


def is_finished(p: Participant) -> bool:
    """A project counts as finished once it has been snapshotted.

    Snapshots happen for everyone at once when the admin ends the event --
    nothing is finished before then.
    """
    return p.submitted_at is not None


def final_code(p: Participant) -> Tuple[str, str, str]:
    """The snapshotted code if there is one, else what is in the editor now."""
    return (
        p.final_html if p.final_html is not None else p.html,
        p.final_css if p.final_css is not None else p.css,
        p.final_js if p.final_js is not None else p.js,
    )


def export_entries(g: GameState) -> List[Tuple[str, Participant]]:
    """(token, participant) pairs to export, ordered by display name."""
    return sorted(g.participants.items(), key=lambda kv: (kv[1].name.lower(), kv[0]))


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


def _export_manifest(g: GameState, entries: List[Tuple[str, Participant]]) -> dict:
    return {
        "exported_at": _iso(time.time()),
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


def _export_index(g: GameState, entries: List[Tuple[str, Participant]]) -> str:
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
        f"<p>{len(entries)} project(s). "
        f"Event {html_escape(g.status)}; started {html_escape(_local_time(g.started_at))}, "
        f"ended {html_escape(_local_time(g.ended_at))}.</p>\n"
        "<table>\n<thead><tr><th>Name</th><th>Finished</th><th>Submitted</th>"
        "<th>Tab-outs</th><th>Copy attempts</th></tr></thead>\n"
        f"<tbody>\n{rows}\n</tbody>\n</table>\n"
        "</body>\n</html>\n"
    )


def build_export_archive(g: GameState) -> Tuple[bytes, str, int]:
    """Zip every project into one downloadable archive.

    Returns the zip bytes, a suggested filename, and how many projects
    went in (zero means there was nothing to export).
    """
    entries = export_entries(g)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    root = f"kcq-projects-{stamp}"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        # GitHub Pages runs Jekyll by default, which can choke on stray
        # {{ }} / {% %} in a participant's JS or CSS. This disables it.
        archive.writestr(".nojekyll", "")
        for token, p in entries:
            html_src, css, js = final_code(p)
            archive.writestr(
                f"{root}/projects/{_export_project_filename(token, p)}",
                _build_document(p.name, html_src, css, js),
            )
        archive.writestr(f"{root}/index.html", _export_index(g, entries))
        archive.writestr(
            f"{root}/manifest.json",
            json.dumps(_export_manifest(g, entries), indent=2),
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


_DOC_HEAD_RE = re.compile(r"<style>(.*?)</style>\n</head>\n<body>\n", re.DOTALL)


def _parse_document(doc: str) -> Tuple[str, str, str]:
    """Reverse `_build_document`: pull html/css/js back out of an exported project file."""
    m = _DOC_HEAD_RE.search(doc)
    if not m:
        raise ValueError("unrecognized project document format")
    css = m.group(1)
    rest = doc[m.end():]
    html, sep, tail = rest.rpartition("\n<script>")
    if not sep:
        raise ValueError("unrecognized project document format")
    safe_js, sep2, _ = tail.rpartition("</script>\n</body>\n</html>")
    if not sep2:
        raise ValueError("unrecognized project document format")
    js = safe_js.replace("<\\/script>", "</script>")
    return html, css, js


def _epoch(iso: Optional[str]) -> Optional[float]:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso).timestamp()
    except ValueError:
        return None


def restore_from_export(zip_bytes: bytes) -> dict:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        manifest_name = next(
            (n for n in archive.namelist() if n.endswith("manifest.json")), None
        )
        if manifest_name is None:
            raise ValueError("no manifest.json found in archive")
        manifest = json.loads(archive.read(manifest_name).decode("utf-8"))
        root = manifest_name.rsplit("/", 1)[0] if "/" in manifest_name else ""

        g = get_or_create_game()
        results = []
        for entry in manifest.get("projects", []):
            token = entry.get("token")
            name = entry.get("name", "participant")
            if not token:
                results.append({"name": name, "token": token, "restored": False, "error": "missing token"})
                continue
            file_rel = entry.get("file", "")
            file_path = f"{root}/{file_rel}" if root else file_rel
            try:
                doc = archive.read(file_path).decode("utf-8")
                html, css, js = _parse_document(doc)
            except (KeyError, ValueError) as exc:
                results.append({"name": name, "token": token, "restored": False, "error": str(exc)})
                continue

            discord_id = entry.get("discord_id", "")
            tab_out_count = entry.get("tab_out_count", 0)
            copy_attempt_count = entry.get("copy_attempt_count", 0)

            existing = g.participants.get(token)
            if existing is not None:
                existing.html, existing.css, existing.js = html, css, js
            else:
                g.participants[token] = Participant(
                    id=entry.get("id") or str(uuid.uuid4()),
                    name=name,
                    sid="",
                    discord_id=discord_id,
                    html=html,
                    css=css,
                    js=js,
                    tab_out_count=tab_out_count,
                    copy_attempt_count=copy_attempt_count,
                )

            # Stage by discord_id too, so this restore also applies the next
            # time start_game() runs -- e.g. if the admin has to create a
            # fresh game rather than reuse this one.
            if discord_id:
                pending_restore[discord_id] = {
                    "name": name,
                    "html": html,
                    "css": css,
                    "js": js,
                    "tab_out_count": tab_out_count,
                    "copy_attempt_count": copy_attempt_count,
                }

            results.append({"name": name, "token": token, "restored": True, "error": None})

        if g.started_at is None and manifest.get("started_at"):
            g.status = manifest.get("status", g.status)
            g.duration_ms = manifest.get("duration_ms", g.duration_ms)
            g.started_at = _epoch(manifest.get("started_at"))
            g.ended_at = _epoch(manifest.get("ended_at"))
            if g.status == "active" and g.ended_at is None:
                g.paused = True
                g.paused_at = time.time()
                g.pause_duration_ms = 0.0

        save_state_snapshot(g)
        save_pending_restore()
    return {"participant_count": len(g.participants), "results": results}


def _pending_restore_path() -> str:
    return os.path.join(os.environ.get("RESULTS_DIR", "results"), "pending_restore.json")


def save_pending_restore() -> Optional[str]:
    path = _pending_restore_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(pending_restore, f)
    os.replace(tmp, path)
    return path


def load_pending_restore() -> dict:
    global pending_restore
    try:
        with open(_pending_restore_path(), encoding="utf-8") as f:
            loaded = json.load(f)
    except (OSError, ValueError):
        return pending_restore
    if isinstance(loaded, dict):
        pending_restore = loaded
    return pending_restore


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
        "paused": g.paused,
        "paused_at": g.paused_at,
        "pause_duration_ms": g.pause_duration_ms,
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
        paused=payload.get("paused", False),
        paused_at=payload.get("paused_at"),
        pause_duration_ms=payload.get("pause_duration_ms", 0.0),
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
