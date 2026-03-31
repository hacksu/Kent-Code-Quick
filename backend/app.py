from gevent import monkey
monkey.patch_all()

import os
from flask import Flask, send_from_directory
from extensions import socketio

import ws_handler  # noqa: F401 — registers event handlers

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "build")

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")
socketio.init_app(app, async_mode="gevent", cors_allowed_origins="*")


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_spa(path: str):
    full = os.path.join(STATIC_DIR, path)
    if path and os.path.isfile(full):
        return send_from_directory(STATIC_DIR, path)
    return send_from_directory(STATIC_DIR, "index.html")


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
