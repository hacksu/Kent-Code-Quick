from gevent import monkey
monkey.patch_all()

import os
import sys
from urllib.parse import urlparse

from flask import Flask, jsonify, redirect, request, send_from_directory, session, Response
import requests as http_requests
from extensions import socketio
import game_manager
from game_manager import create_game, end_game

import ws_handler  # noqa: F401

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "build")

app = Flask(__name__)

SESSION_SECRET = os.environ.get("SESSION_SECRET")
if not SESSION_SECRET:
    raise RuntimeError("SESSION_SECRET environment variable must be set")
app.secret_key = SESSION_SECRET

socketio.init_app(app, async_mode="gevent", cors_allowed_origins="*")

@app.after_request
def no_cache_api(response):
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response

DISCORD_CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID", "")
DISCORD_CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET", "")
DISCORD_ADMIN_ROLE_ID = os.environ.get("DISCORD_ADMIN_ROLE_ID", "")
DISCORD_GUILD_ID = os.environ.get("DISCORD_GUILD_ID", "")

DOCS_ALLOWLIST = {"developer.mozilla.org", "www.w3schools.com"}


# --- Config ---

@app.route("/api/config")
def get_config():
    return jsonify({"devdocs_url": os.environ.get("DEVDOCS_URL", "http://localhost:9292")})


# --- Auth ---

@app.route("/api/auth/dev-login")
def dev_login():
    # Dev-only escape hatch. Fail closed: only available when NODE_ENV is set.
    if os.environ.get("NODE_ENV") != "development":
        return jsonify({"error": "forbidden"}), 403
    name = request.args.get("name", "TestPlayer")
    is_admin = request.args.get("admin", "0") == "1"
    session["discord_id"] = f"dev-{name}"
    session["discord_username"] = name
    session["is_admin"] = is_admin
    return redirect("/admin" if is_admin else "/lobby")


@app.route("/api/auth/exchange")
def auth_exchange():
    code = request.args.get("code")
    redirect_uri = request.args.get("redirect_uri")
    if not code or not redirect_uri:
        return jsonify({"error": "missing params"}), 400

    token_resp = http_requests.post(
        "https://discord.com/api/oauth2/token",
        data={
            "client_id": DISCORD_CLIENT_ID,
            "client_secret": DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if token_resp.status_code != 200:
        return jsonify({"error": "token exchange failed"}), 401

    access_token = token_resp.json()["access_token"]

    user_resp = http_requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if user_resp.status_code != 200:
        return jsonify({"error": "user fetch failed"}), 401

    user = user_resp.json()

    member_resp = http_requests.get(
        f"https://discord.com/api/users/@me/guilds/{DISCORD_GUILD_ID}/member",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    is_admin = False
    if member_resp.status_code == 200:
        member_roles = member_resp.json().get("roles", [])
        is_admin = DISCORD_ADMIN_ROLE_ID in member_roles

    session["discord_id"] = user["id"]
    session["discord_username"] = user["username"]
    session["is_admin"] = is_admin

    return jsonify({"is_admin": is_admin, "discord_username": user["username"]})


@app.route("/api/auth/me")
def auth_me():
    if "discord_id" not in session:
        return jsonify({"error": "not authenticated"}), 401
    return jsonify({
        "discord_id": session["discord_id"],
        "discord_username": session["discord_username"],
        "is_admin": session.get("is_admin", False),
    })


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return jsonify({"ok": True})


# --- Game API ---

@app.route("/api/game", methods=["GET"])
def get_game():
    g = game_manager.game
    if g is None:
        return jsonify({"status": "waiting", "lobby_count": 0, "duration_ms": 45 * 60 * 1000})
    return jsonify({"status": g.status, "lobby_count": len(g.lobby), "duration_ms": g.duration_ms})


@app.route("/api/game", methods=["POST"])
def create_game_route():
    if not session.get("is_admin"):
        return jsonify({"error": "forbidden"}), 403
    data = request.get_json() or {}
    duration_ms = data.get("duration_ms", 45 * 60 * 1000)
    g = create_game(duration_ms=duration_ms)
    return jsonify(g.to_dict()), 201


@app.route("/api/game/results", methods=["GET"])
def game_results():
    if not session.get("is_admin"):
        return jsonify({"error": "forbidden"}), 403
    g = game_manager.game
    if g is None:
        return jsonify({"error": "no game"}), 404
    return jsonify(g.to_dict())


# --- Docs proxy ---

@app.route("/api/docs")
def docs_proxy():
    url = request.args.get("url", "")
    parsed = urlparse(url)
    if parsed.hostname not in DOCS_ALLOWLIST:
        return jsonify({"error": "forbidden"}), 403
    resp = http_requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
    base_url = f"{parsed.scheme}://{parsed.netloc}/"
    intercept_script = f"""<script>
(function() {{
  try {{
    Object.defineProperty(window, 'top',    {{ get: function() {{ return window; }} }});
    Object.defineProperty(window, 'parent', {{ get: function() {{ return window; }} }});
    Object.defineProperty(window, 'self',   {{ get: function() {{ return window; }} }});
    Object.defineProperty(window, 'frameElement', {{ get: function() {{ return null; }} }});
  }} catch(e) {{}}
  var _origin = window.location.origin;
  function proxyUrl(href) {{
    if (!href || href.startsWith('#') || href.startsWith('javascript:')) return href;
    if (href.indexOf('/api/docs?url=') !== -1) return href;
    try {{
      var abs = new URL(href, '{base_url}').href;
      return _origin + '/api/docs?url=' + encodeURIComponent(abs);
    }} catch(e) {{ return href; }}
  }}
  window.addEventListener('click', function(e) {{
    var a = e.target.closest('a[href]');
    if (!a) return;
    var href = a.getAttribute('href');
    if (!href || href.startsWith('#') || href.startsWith('javascript:')) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    window.location.href = proxyUrl(href);
  }}, true);
  document.addEventListener('DOMContentLoaded', function() {{
    document.querySelectorAll('a[href]').forEach(function(a) {{
      var h = a.getAttribute('href');
      if (h && !h.startsWith('#') && !h.startsWith('javascript:') && h.indexOf('/api/docs?url=') === -1)
        a.setAttribute('href', proxyUrl(h));
    }});
  }});
}})();
</script>"""
    html = resp.text.replace("<head>", f'<head><base href="{base_url}">' + intercept_script, 1)
    response = Response(html, status=resp.status_code, content_type="text/html; charset=utf-8")
    response.headers.pop("X-Frame-Options", None)
    response.headers.pop("Content-Security-Policy", None)
    return response


# --- SPA fallback ---

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_spa(path: str):
    full = os.path.join(STATIC_DIR, path)
    if path and os.path.isfile(full):
        return send_from_directory(STATIC_DIR, path)
    return send_from_directory(STATIC_DIR, "index.html")


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5001)
