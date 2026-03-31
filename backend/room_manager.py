from dataclasses import dataclass, field
from typing import Optional


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
