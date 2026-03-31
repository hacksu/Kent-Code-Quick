from gevent import monkey
monkey.patch_all()

from flask import Flask
from extensions import socketio

import ws_handler  # noqa: F401 — registers event handlers

app = Flask(__name__)
socketio.init_app(app, async_mode="gevent", cors_allowed_origins="*")

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
