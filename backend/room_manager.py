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

BACKUP_FILE = "room_backup.json"
BACKUP_INTERVAL = 30  # seconds


@dataclass
class Participant:
    id: str
    name: str
    sid: str
    html: str = ""
    css: str = ""
    penalty_ms: int = 0
    tab_out_count: int = 0
    submitted_at: Optional[float] = None
    final_html: Optional[str] = None
    final_css: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "sid": self.sid,
            "html": self.html,
            "css": self.css,
            "penalty_ms": self.penalty_ms,
            "tab_out_count": self.tab_out_count,
            "submitted_at": self.submitted_at,
            "final_html": self.final_html,
            "final_css": self.final_css,
        }


@dataclass
class RoomState:
    code: str
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    duration_ms: int = 45 * 60 * 1000
    participants: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ms": self.duration_ms,
            "participants": {token: p.to_dict() for token, p in self.participants.items()},
        }


rooms: dict[str, RoomState] = {}


def get_or_create_room(code: str) -> RoomState:
    if code not in rooms:
        rooms[code] = RoomState(code=code)
    return rooms[code]


def get_participant(room: RoomState, token: Optional[str], name: str, sid: str) -> Tuple[str, Participant]:
    if token and token in room.participants:
        participant = room.participants[token]
        participant.sid = sid
        return token, participant
    new_token = secrets.token_urlsafe(8)
    participant = Participant(id=str(uuid.uuid4()), name=name, sid=sid)
    room.participants[new_token] = participant
    return new_token, participant


_PENALTY_SCHEDULE = [5, 25, 60, 120, 240, 480, 960]


def apply_penalty(sid: str) -> dict:
    for room in rooms.values():
        for participant in room.participants.values():
            if participant.sid == sid:
                idx = min(participant.tab_out_count, len(_PENALTY_SCHEDULE) - 1)
                participant.penalty_ms += _PENALTY_SCHEDULE[idx] * 1000
                participant.tab_out_count += 1
                return {
                    "penalty_ms": participant.penalty_ms,
                    "tab_out_count": participant.tab_out_count,
                }
    return {}


def snapshot_participant(sid: str) -> None:
    for room in rooms.values():
        for participant in room.participants.values():
            if participant.sid == sid:
                participant.final_html = participant.html
                participant.final_css = participant.css
                participant.submitted_at = time.time()
                return


def _backup_loop() -> None:
    while True:
        time.sleep(BACKUP_INTERVAL)
        data = {code: room.to_dict() for code, room in rooms.items()}
        dir_ = os.path.dirname(os.path.abspath(BACKUP_FILE)) or "."
        with tempfile.NamedTemporaryFile("w", dir=dir_, delete=False, suffix=".tmp") as f:
            json.dump(data, f)
            tmp_path = f.name
        os.replace(tmp_path, BACKUP_FILE)


_backup_thread = threading.Thread(target=_backup_loop, daemon=True, name="room-backup")
_backup_thread.start()
