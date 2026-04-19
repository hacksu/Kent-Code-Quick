from gevent import monkey
monkey.patch_all()

import os
from flask import Flask, jsonify, request, send_from_directory, Response
from urllib.parse import urlparse
import requests as http_requests
from extensions import socketio
from room_manager import rooms

import ws_handler  # noqa: F401 — registers event handlers

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "build")

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")
socketio.init_app(app, async_mode="gevent", cors_allowed_origins="*")


ADMIN_SECRET = os.environ.get("ADMIN_SECRET")
if not ADMIN_SECRET:
    raise RuntimeError("ADMIN_SECRET environment variable must be set")
DOCS_ALLOWLIST = {"developer.mozilla.org", "www.w3schools.com"}


@app.route("/api/docs")
def docs_proxy():
    url = request.args.get("url", "")
    hostname = urlparse(url).hostname
    if hostname not in DOCS_ALLOWLIST:
        return jsonify({"error": "forbidden"}), 403
    resp = http_requests.get(url, timeout=10)
    return Response(resp.content, status=resp.status_code, content_type="text/html")


@app.route("/api/room/<code>/results")
def room_results(code: str):
    if request.args.get("secret") != ADMIN_SECRET:
        return jsonify({"error": "forbidden"}), 403
    if code not in rooms:
        return jsonify({"error": "not found"}), 404
    return jsonify(rooms[code].to_dict()), 200


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_spa(path: str):
    full = os.path.join(STATIC_DIR, path)
    if path and os.path.isfile(full):
        return send_from_directory(STATIC_DIR, path)
    return send_from_directory(STATIC_DIR, "index.html")


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5001)
