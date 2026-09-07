"""DevDocs is re-served from this origin so it needs no published port."""
from gevent import monkey
monkey.patch_all()

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from app import app, DEVDOCS_PREFIXES, DEVDOCS_FILES


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def fake_upstream(body=b"<html>docs</html>", status=200, headers=None):
    return SimpleNamespace(
        status_code=status,
        raw=SimpleNamespace(headers=headers or {"Content-Type": "text/html"}),
        iter_content=lambda chunk_size=1: iter([body]),
        text=body.decode(),
    )


@pytest.mark.parametrize("path", [f"/{p}/" for p in DEVDOCS_PREFIXES])
def test_every_docs_prefix_reaches_devdocs(client, path):
    with patch("app.http_requests.get", return_value=fake_upstream()) as get:
        resp = client.get(path)
    assert resp.status_code == 200
    assert get.call_args[0][0] == f"http://devdocs:9292{path}"


@pytest.mark.parametrize("name", DEVDOCS_FILES)
def test_docs_files_reach_devdocs(client, name):
    with patch("app.http_requests.get", return_value=fake_upstream()) as get:
        client.get(f"/{name}")
    assert get.call_args[0][0] == f"http://devdocs:9292/{name}"


def test_nested_docs_paths_pass_through_untouched(client):
    with patch("app.http_requests.get", return_value=fake_upstream()) as get:
        client.get("/html/element/div")
    assert get.call_args[0][0] == "http://devdocs:9292/html/element/div"


def test_query_strings_are_forwarded(client):
    with patch("app.http_requests.get", return_value=fake_upstream()) as get:
        client.get("/docs/docs.json?123")
    assert get.call_args.kwargs["params"] is not None


def test_body_is_streamed_back_to_the_browser(client):
    with patch("app.http_requests.get", return_value=fake_upstream(b"console.log(1)")):
        resp = client.get("/assets/application.js")
    assert resp.data == b"console.log(1)"


def test_embedding_hostile_headers_are_dropped(client):
    upstream = fake_upstream(headers={
        "Content-Type": "text/html",
        "X-Frame-Options": "DENY",
        "Content-Security-Policy": "frame-ancestors 'none'",
        "Content-Encoding": "gzip",
        "Content-Length": "999",
    })
    with patch("app.http_requests.get", return_value=upstream):
        resp = client.get("/html/")
    assert "X-Frame-Options" not in resp.headers
    assert "Content-Security-Policy" not in resp.headers
    assert resp.headers.get("Content-Encoding") is None
    assert resp.headers["Content-Type"] == "text/html"


def test_devdocs_being_down_is_reported_not_crashed(client):
    import requests as real_requests
    with patch("app.http_requests.get", side_effect=real_requests.ConnectionError()):
        resp = client.get("/html/")
    assert resp.status_code == 502
    assert resp.get_json()["error"]


@pytest.mark.parametrize("path", ["/", "/admin", "/play", "/watch", "/lobby"])
def test_app_routes_still_reach_the_spa(client, path):
    with patch("app.http_requests.get") as get:
        client.get(path)
    get.assert_not_called()


def test_api_routes_are_not_proxied(client):
    with patch("app.http_requests.get") as get:
        resp = client.get("/api/config")
    get.assert_not_called()
    assert resp.status_code == 200


def test_docs_panel_opens_on_the_full_devdocs_root(client):
    """Every docset, not just one -- /html/ would boot single-doc mode."""
    with patch("app.http_requests.get", return_value=fake_upstream()) as get:
        client.get("/devdocs/")
    assert get.call_args[0][0] == "http://devdocs:9292/"


def test_root_path_is_normalised_for_the_devdocs_router(client):
    body = b"<html><head><title>DevDocs</title></head><body></body></html>"
    resp_stub = SimpleNamespace(status_code=200, text=body.decode(), raw=SimpleNamespace(headers={}))
    with patch("app.http_requests.get", return_value=resp_stub):
        resp = client.get("/devdocs/")
    assert b"history.replaceState(null, '', '/');" in resp.data
    assert resp.data.index(b"replaceState") < resp.data.index(b"</head>")


def test_config_sends_the_panel_to_the_devdocs_root(client):
    with patch.dict("os.environ", {"DEVDOCS_URL": ""}):
        resp = client.get("/api/config")
    assert resp.get_json()["devdocs_url"] == "/devdocs"
