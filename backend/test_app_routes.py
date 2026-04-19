"""Tests for Flask HTTP routes in app.py."""
from gevent import monkey
monkey.patch_all()

import runpy
import pytest
from unittest.mock import patch, MagicMock
from app import app
from room_manager import rooms, get_or_create_room, get_participant


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def clear_rooms():
    rooms.clear()
    yield
    rooms.clear()


# --- /api/docs ---

def test_docs_proxy_forbidden_hostname(client):
    resp = client.get("/api/docs?url=https://evil.com/page")
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "forbidden"


def test_docs_proxy_no_url_is_forbidden(client):
    resp = client.get("/api/docs")
    assert resp.status_code == 403


def test_docs_proxy_allowed_mdn(client):
    mock_resp = MagicMock()
    mock_resp.content = b"<html>docs</html>"
    mock_resp.status_code = 200
    with patch("app.http_requests.get", return_value=mock_resp) as mock_get:
        resp = client.get("/api/docs?url=https://developer.mozilla.org/en-US/docs/Web/HTML")
        assert resp.status_code == 200
        assert b"docs" in resp.data
        mock_get.assert_called_once()


def test_docs_proxy_allowed_w3schools(client):
    mock_resp = MagicMock()
    mock_resp.content = b"<html>w3</html>"
    mock_resp.status_code = 200
    with patch("app.http_requests.get", return_value=mock_resp):
        resp = client.get("/api/docs?url=https://www.w3schools.com/html/")
        assert resp.status_code == 200


# --- /api/room/<code>/results ---

def test_room_results_wrong_secret(client):
    resp = client.get("/api/room/TEST/results?secret=wrong")
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "forbidden"


def test_room_results_room_not_found(client):
    resp = client.get("/api/room/MISSING/results?secret=test-secret")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "not found"


def test_room_results_success(client):
    room = get_or_create_room("TEST")
    get_participant(room, None, "Alice", "sid1")
    resp = client.get("/api/room/TEST/results?secret=test-secret")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["code"] == "TEST"
    assert len(data["participants"]) == 1


# --- SPA fallback ---

def test_main_guard_runs_socketio():
    with patch("app.socketio.run") as mock_run:
        runpy.run_path("app.py", run_name="__main__")
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        assert call_kwargs[1].get("host") == "0.0.0.0"
        assert call_kwargs[1].get("port") == 5001


def _call_serve_spa(path):
    """Call serve_spa directly, bypassing Flask's static file handler."""
    from app import serve_spa
    with app.test_request_context(f"/{path}"):
        return serve_spa(path)


def test_serve_spa_unknown_path_returns_index(client):
    sentinel = MagicMock()
    with patch("app.send_from_directory", return_value=sentinel) as mock_send:
        _call_serve_spa("some/unknown/path")
        args = mock_send.call_args[0]
        assert args[1] == "index.html"


def test_serve_spa_root_returns_index(client):
    sentinel = MagicMock()
    with patch("app.send_from_directory", return_value=sentinel) as mock_send:
        _call_serve_spa("")
        args = mock_send.call_args[0]
        assert args[1] == "index.html"


def test_serve_spa_existing_static_file(client):
    sentinel = MagicMock()
    with patch("os.path.isfile", return_value=True), \
         patch("app.send_from_directory", return_value=sentinel) as mock_send:
        _call_serve_spa("assets/main.js")
        args = mock_send.call_args[0]
        assert args[1] == "assets/main.js"
