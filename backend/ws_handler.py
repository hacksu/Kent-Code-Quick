from __future__ import annotations

from flask import request
from flask_socketio import emit

from extensions import socketio
from room_manager import rooms


@socketio.on("code_update")
def handle_code_update(data: dict) -> None:
    sid = request.sid
    for room_code, room in rooms.items():
        for participant in room.participants.values():
            if participant.sid == sid:
                if participant.submitted_at is not None:
                    return
                participant.html = data.get("html", participant.html)
                participant.css = data.get("css", participant.css)
                emit("participant_update", {
                    "id": participant.id,
                    "name": participant.name,
                    "html": participant.html,
                    "css": participant.css,
                }, to=room_code)
                return
