from gevent import monkey
monkey.patch_all()

from flask import Flask
from flask_socketio import SocketIO

import ws_handler  # noqa: F401 — registers event handlers

app = Flask(__name__)
socketio = SocketIO(app, async_mode="gevent", cors_allowed_origins="*")

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
