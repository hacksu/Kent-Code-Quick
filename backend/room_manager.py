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
