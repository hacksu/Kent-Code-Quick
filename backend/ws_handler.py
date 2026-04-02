from __future__ import annotations

from flask import request
from flask_socketio import emit, join_room

from extensions import socketio
from room_manager import apply_penalty, get_or_create_room, get_participant, rooms


@socketio.on("join")
def handle_join(data: dict) -> None:
    room_code = data.get("room_code")
    if not room_code:
        return

    room = get_or_create_room(room_code)
    token, participant = get_participant(
        room,
        data.get("token"),
        data.get("name", "Anonymous"),
        request.sid,
    )

    if data.get("token") != token:
        emit("token_assigned", {"token": token})

    join_room(room_code)
    emit("room_state", room.to_dict(), to=room_code)


@socketio.on("tab_out")
def handle_tab_out(data: dict) -> None:
    result = apply_penalty(request.sid)
    if not result:
        return
    emit("penalty", {
        "penalty_ms": result["penalty_ms"],
        "tab_out_count": result["tab_out_count"],
    })


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
