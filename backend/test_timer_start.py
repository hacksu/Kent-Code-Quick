"""Tests for issue #20: timer start trigger in handle_join."""
from unittest.mock import patch, MagicMock

from gevent import monkey
monkey.patch_all()

import time
import pytest
from app import app, socketio
from room_manager import rooms


@pytest.fixture(autouse=True)
def clear_rooms():
    rooms.clear()
    yield
    rooms.clear()


def test_timer_spawned_on_first_join():
    client = socketio.test_client(app)
    with patch("ws_handler.gevent.spawn") as mock_spawn:
        client.emit("join", {"room_code": "TEST", "name": "Alice", "role": "participant"})
        assert mock_spawn.call_count == 1
        args = mock_spawn.call_args[0]
        assert args[1] == "TEST"  # room_code passed to run_timer


def test_started_at_set_before_spawn():
    client = socketio.test_client(app)
    captured = {}

    def fake_spawn(fn, room_code):
        from room_manager import rooms
        captured["started_at"] = rooms[room_code].started_at

    with patch("ws_handler.gevent.spawn", side_effect=fake_spawn):
        client.emit("join", {"room_code": "TEST", "name": "Alice", "role": "participant"})

    assert captured.get("started_at") is not None
    assert captured["started_at"] <= time.time()


def test_second_join_does_not_spawn_second_timer():
    client1 = socketio.test_client(app)
    client2 = socketio.test_client(app)
    with patch("ws_handler.gevent.spawn") as mock_spawn:
        client1.emit("join", {"room_code": "TEST", "name": "Alice", "role": "participant"})
        client2.emit("join", {"room_code": "TEST", "name": "Bob", "role": "participant"})
        assert mock_spawn.call_count == 1


def test_reconnect_does_not_spawn_second_timer():
    client = socketio.test_client(app)
    with patch("ws_handler.gevent.spawn") as mock_spawn:
        client.emit("join", {"room_code": "TEST", "name": "Alice", "role": "participant"})
        # Simulate reconnect: re-emit join with same room (started_at already set)
        client.emit("join", {"room_code": "TEST", "name": "Alice", "role": "participant"})
        assert mock_spawn.call_count == 1
