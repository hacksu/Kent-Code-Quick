from __future__ import annotations

import time

import gevent
from flask import request, session
from flask_socketio import emit, join_room

from extensions import socketio
from game_manager import (
    add_to_lobby,
    apply_penalty,
    end_game,
    get_or_create_game,
    get_participant_by_sid,
    record_copy_attempt,
    reset_game,
    snapshot_participant,
    start_game,
)
import game_manager

LOBBY_ROOM = "lobby"
GAME_ROOM = "game"


def _run_timer() -> None:
    g = game_manager.game
    if g is None or g.started_at is None:
        return
    while g.ended_at is None:
        gevent.sleep(1)
        elapsed = (time.time() - g.started_at) * 1000
        socketio.emit("timer_tick", {"elapsed": elapsed, "ended": False}, to=GAME_ROOM)


def _fire_event_end() -> None:
    g = game_manager.game
    if g is None:
        return
    end_game(g)
    socketio.emit("event_end", g.to_dict(), to=GAME_ROOM)


@socketio.on("join_lobby")
def handle_join_lobby(data: dict) -> None:
    g = get_or_create_game()
    if g.status != "waiting":
        emit("game_locked")
        return

    token, _ = add_to_lobby(g, data.get("token"), data.get("name", "Anonymous"), request.sid)

    if data.get("token") != token:
        emit("token_assigned", {"token": token})

    join_room(LOBBY_ROOM)
    socketio.emit("lobby_update", {"lobby_count": len(g.lobby)}, to=LOBBY_ROOM)


@socketio.on("join_game")
def handle_join_game(data: dict) -> None:
    g = game_manager.game
    if g is None or g.status == "ended":
        emit("game_locked")
        return
    token = data.get("token")
    if not token or token not in g.participants:
        emit("game_locked")
        return
    participant = g.participants[token]
    participant.sid = request.sid
    join_room(GAME_ROOM)
    emit("game_state", g.to_dict())


@socketio.on("watch_game")
def handle_watch_game(data: dict) -> None:
    if not session.get("is_admin"):
        return
    join_room(GAME_ROOM)
    join_room(LOBBY_ROOM)
    g = get_or_create_game()
    emit("game_state", g.to_dict())


@socketio.on("start_game")
def handle_start_game(data: dict) -> None:
    if not session.get("is_admin"):
        return
    g = get_or_create_game()
    if g.status != "waiting":
        return
    if "duration_ms" in data:
        g.duration_ms = int(data["duration_ms"])
    lobby_entries = list(g.lobby.items())
    start_game(g)
    gevent.spawn(_run_timer)
    for token, _ in lobby_entries:
        if token in g.participants:
            participant = g.participants[token]
            socketio.emit("game_start", {"token": token}, to=participant.sid)
    socketio.emit("game_state", g.to_dict(), to=GAME_ROOM)


@socketio.on("end_event")
def handle_end_event(data: dict) -> None:
    if not session.get("is_admin"):
        return
    g = game_manager.game
    if g is None or g.status != "active":
        return
    end_game(g)
    socketio.emit("event_end", g.to_dict(), to=GAME_ROOM)


@socketio.on("reset_game")
def handle_reset_game(data: dict) -> None:
    if not session.get("is_admin"):
        return
    reset_game()
    socketio.emit("game_reset", {})


@socketio.on("tab_out")
def handle_tab_out(data: dict) -> None:
    result = apply_penalty(request.sid)
    if not result:
        return
    emit("penalty", {"type": "tab_out", "count": result["tab_out_count"], "penalty_ms": result["penalty_ms"]})
    pair = get_participant_by_sid(request.sid)
    if pair:
        token, participant = pair
        socketio.emit(
            "participant_update",
            {
                "token": token,
                "penalty_ms": participant.penalty_ms,
                "tab_out_count": participant.tab_out_count,
            },
            to=GAME_ROOM,
        )


@socketio.on("copy_attempt")
def handle_copy_attempt(data: dict) -> None:
    result = record_copy_attempt(request.sid)
    if not result:
        return
    emit("penalty", {"type": "copy", "count": result["copy_attempt_count"], "penalty_ms": result["penalty_ms"]})
    pair = get_participant_by_sid(request.sid)
    if pair:
        token, participant = pair
        socketio.emit(
            "participant_update",
            {
                "token": token,
                "copy_attempt_count": participant.copy_attempt_count,
                "penalty_ms": participant.penalty_ms,
            },
            to=GAME_ROOM,
        )


@socketio.on("submit")
def handle_submit(data: dict) -> None:
    pair = get_participant_by_sid(request.sid)
    if not pair:
        return
    token, participant = pair
    if participant.submitted_at is not None:
        return
    snapshot_participant(request.sid)
    emit("submitted")
    g = game_manager.game
    if g:
        socketio.emit(
            "participant_update",
            {"token": token, **participant.to_dict()},
            to=GAME_ROOM,
        )


@socketio.on("code_update")
def handle_code_update(data: dict) -> None:
    pair = get_participant_by_sid(request.sid)
    if not pair:
        return
    token, participant = pair
    if participant.submitted_at is not None:
        return
    participant.html = data.get("html", participant.html)
    participant.css = data.get("css", participant.css)
    participant.js = data.get("js", participant.js)
    socketio.emit(
        "participant_update",
        {
            "token": token,
            "id": participant.id,
            "name": participant.name,
            "html": participant.html,
            "css": participant.css,
            "js": participant.js,
        },
        to=GAME_ROOM,
    )
