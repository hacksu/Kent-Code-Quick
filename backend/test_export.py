"""Tests for the admin project export (zip download of built projects)."""
from gevent import monkey
monkey.patch_all()

import io
import json
import zipfile

import pytest
from app import app
import game_manager
from game_manager import (
    add_to_lobby,
    build_export_archive,
    create_game,
    end_game,
    export_entries,
    final_code,
    is_finished,
    start_game,
)


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def reset_game():
    game_manager.game = None
    yield
    game_manager.game = None


def set_admin_session(client):
    with client.session_transaction() as sess:
        sess["is_admin"] = True
        sess["discord_id"] = "admin-id"
        sess["discord_username"] = "Admin"


def game_with(*names):
    """An active game with one participant per name, keyed by name."""
    g = create_game()
    for name in names:
        add_to_lobby(g, None, name, f"sid-{name}")
    start_game(g)
    return g, {p.name: p for p in g.participants.values()}


def open_zip(payload):
    return zipfile.ZipFile(io.BytesIO(payload))


def project_names(archive):
    return sorted(
        n.split("/", 2)[2] for n in archive.namelist() if "/projects/" in n
    )


# --- manager helpers ---

def test_final_code_prefers_the_snapshot():
    g, by_name = game_with("Alice")
    alice = by_name["Alice"]
    alice.html, alice.css, alice.js = "live", "live-css", "live-js"
    alice.final_html, alice.final_css, alice.final_js = "final", "final-css", "final-js"
    assert final_code(alice) == ("final", "final-css", "final-js")


def test_final_code_falls_back_to_live_editor_contents():
    g, by_name = game_with("Alice")
    alice = by_name["Alice"]
    alice.html, alice.css, alice.js = "live", "live-css", "live-js"
    assert final_code(alice) == ("live", "live-css", "live-js")


def test_is_finished_tracks_the_snapshot():
    g, by_name = game_with("Alice")
    alice = by_name["Alice"]
    assert not is_finished(alice)
    alice.submitted_at = 1.0
    assert is_finished(alice)


def test_export_entries_includes_finished_and_in_progress_projects():
    g, by_name = game_with("Alice", "Bob")
    by_name["Alice"].submitted_at = 1.0
    assert [p.name for _, p in export_entries(g)] == ["Alice", "Bob"]


def test_export_entries_sorted_by_name():
    g, _ = game_with("zoe", "Alice", "bob")
    names = [p.name for _, p in export_entries(g)]
    assert names == ["Alice", "bob", "zoe"]


def test_archive_holds_one_standalone_document_per_project():
    g, by_name = game_with("Alice")
    alice = by_name["Alice"]
    alice.final_html = "<h1>hi</h1>"
    alice.final_css = "h1{color:red}"
    alice.final_js = "console.log(1)"
    alice.submitted_at = 1.0

    payload, filename, count = build_export_archive(g)
    assert count == 1
    assert filename.startswith("kcq-projects-") and filename.endswith(".zip")

    archive = open_zip(payload)
    assert project_names(archive) == ["Alice-" + next(iter(g.participants)) + ".html"]
    doc = archive.read(
        [n for n in archive.namelist() if "/projects/" in n][0]
    ).decode()
    assert "<h1>hi</h1>" in doc
    assert "h1{color:red}" in doc
    assert "console.log(1)" in doc


def test_archive_carries_an_index_and_a_manifest():
    g, by_name = game_with("Alice")
    by_name["Alice"].submitted_at = 1.0
    by_name["Alice"].tab_out_count = 3

    payload, _, _ = build_export_archive(g)
    archive = open_zip(payload)
    names = archive.namelist()
    root = names[0].split("/", 1)[0]
    assert f"{root}/index.html" in names
    assert f"{root}/manifest.json" in names

    manifest = json.loads(archive.read(f"{root}/manifest.json"))
    assert manifest["exported_count"] == 1
    assert manifest["exported_count"] == 1
    assert manifest["participant_count"] == 1
    entry = manifest["projects"][0]
    assert entry["name"] == "Alice"
    assert entry["finished"] is True
    assert entry["tab_out_count"] == 3
    assert f"{root}/{entry['file']}" in names

    index = archive.read(f"{root}/index.html").decode()
    assert "Alice" in index


def test_index_escapes_participant_names():
    g, by_name = game_with("<script>evil</script>")
    by_name["<script>evil</script>"].submitted_at = 1.0
    payload, _, _ = build_export_archive(g)
    archive = open_zip(payload)
    root = archive.namelist()[0].split("/", 1)[0]
    index = archive.read(f"{root}/index.html").decode()
    assert "<script>evil</script>" not in index
    assert "&lt;script&gt;" in index


def test_ending_the_game_makes_every_project_exportable():
    g, by_name = game_with("Alice", "Bob")
    by_name["Alice"].html = "<p>a</p>"
    end_game(g)
    payload, _, count = build_export_archive(g)
    assert count == 2


# --- route ---

def test_export_requires_admin(client):
    game_with("Alice")
    resp = client.get("/api/game/export")
    assert resp.status_code == 403


def test_export_returns_404_when_no_game(client):
    set_admin_session(client)
    resp = client.get("/api/game/export")
    assert resp.status_code == 404


def test_export_returns_404_when_there_are_no_participants(client):
    set_admin_session(client)
    create_game()
    resp = client.get("/api/game/export")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "no projects to export"


def test_export_downloads_a_zip_of_every_project(client):
    set_admin_session(client)
    g, by_name = game_with("Alice", "Bob")
    by_name["Alice"].submitted_at = 1.0

    resp = client.get("/api/game/export")
    assert resp.status_code == 200
    assert resp.mimetype == "application/zip"
    assert "attachment; filename=" in resp.headers["Content-Disposition"]
    files = project_names(open_zip(resp.data))
    assert len(files) == 2
