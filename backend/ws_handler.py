from __future__ import annotations

import time

import gevent
from flask import request
from flask_socketio import emit, join_room

from extensions import socketio
from room_manager import apply_penalty, auto_snapshot_all, get_or_create_room, get_participant, rooms, snapshot_participant


def run_timer(room_code: str) -> None:
    room = rooms.get(room_code)
    if room is None or room.started_at is None:
        return
    while room.ended_at is None:
        gevent.sleep(1)
        elapsed = (time.time() - room.started_at) * 1000
        socketio.emit("timer_tick", {"elapsed": elapsed, "ended": False}, to=room_code)
        if elapsed >= room.duration_ms:
            fire_event_end(room_code)
            return
    socketio.emit("timer_tick", {"elapsed": (time.time() - room.started_at) * 1000, "ended": True}, to=room_code)


def fire_event_end(room_code: str) -> None:
    """Called by run_timer when elapsed >= duration_ms."""
    room = rooms.get(room_code)
    if room is None:
        return
    auto_snapshot_all(room)
    socketio.emit("event_end", room.to_dict(), to=room_code)


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
        data.get("role", "participant"),
    )

    if data.get("token") != token:
        emit("token_assigned", {"token": token})

    if room.started_at is None:
        room.started_at = time.time()
        gevent.spawn(run_timer, room_code)

    join_room(room_code)
    emit("room_state", room.to_dict(), to=room_code)


@socketio.on("end_event")
def handle_end_event(data: dict) -> None:
    sid = request.sid
    for room_code, room in rooms.items():
        for participant in room.participants.values():
            if participant.sid == sid:
                if participant.role != "admin":
                    return
                room.ended_at = time.time()
                auto_snapshot_all(room)
                socketio.emit("event_end", room.to_dict(), to=room_code)
                return


@socketio.on("tab_out")
def handle_tab_out(data: dict) -> None:
    result = apply_penalty(request.sid)
    if not result:
        return
    emit("penalty", {
        "penalty_ms": result["penalty_ms"],
        "tab_out_count": result["tab_out_count"],
    })


@socketio.on("submit")
def handle_submit(data: dict) -> None:
    sid = request.sid
    for room_code, room in rooms.items():
        for participant in room.participants.values():
            if participant.sid == sid:
                if participant.submitted_at is not None:
                    return
                snapshot_participant(sid)
                emit("submitted")
                emit("room_state", room.to_dict(), to=room_code)
                return


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
