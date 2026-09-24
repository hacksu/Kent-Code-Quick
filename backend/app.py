from gevent import monkey
monkey.patch_all()

import os
import sys
from urllib.parse import urlparse

from flask import Flask, jsonify, redirect, request, send_from_directory, session, Response
import requests as http_requests
from extensions import socketio
import game_manager
from game_manager import DEFAULT_DURATION_MS, create_game

import ws_handler  # noqa: F401

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "build")

app = Flask(__name__)

SESSION_SECRET = os.environ.get("SESSION_SECRET")
if not SESSION_SECRET:
    raise RuntimeError("SESSION_SECRET environment variable must be set")
app.secret_key = SESSION_SECRET

IS_DEV = os.environ.get("NODE_ENV") == "development"

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1",
)

_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]
socketio.init_app(
    app,
    async_mode="gevent",
    cors_allowed_origins=_origins or None,
)

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

DEVDOCS_UPSTREAM = os.environ.get("DEVDOCS_UPSTREAM", "http://devdocs:9292").rstrip("/")
DEVDOCS_DEFAULT_PATH = "/devdocs"

DEVDOCS_PREFIXES = ("assets", "docs", "images", "html", "css", "javascript", "dom")
DEVDOCS_FILES = ("manifest.json", "opensearch.xml")

_DEVDOCS_SKIP_HEADERS = {
    "content-encoding",
    "content-length",
    "transfer-encoding",
    "connection",
    "keep-alive",
    "x-frame-options",
    "content-security-policy",
}


# --- Config ---

@app.route("/api/config")
def get_config():
    url = os.environ.get("DEVDOCS_URL") or DEVDOCS_DEFAULT_PATH
    return jsonify({
        "devdocs_url": url.rstrip("/"),
        "discord_client_id": DISCORD_CLIENT_ID,
        "signup_open": game_manager.get_settings()["signup_open"],
    })


@app.route("/api/settings", methods=["GET"])
def get_settings_route():
    if not session.get("is_admin"):
        return jsonify({"error": "forbidden"}), 403
    return jsonify(game_manager.get_settings())


@app.route("/api/settings", methods=["POST"])
def update_settings_route():
    if not session.get("is_admin"):
        return jsonify({"error": "forbidden"}), 403
    data = request.get_json(silent=True) or {}
    if "signup_open" not in data:
        return jsonify({"error": "missing signup_open"}), 400
    return jsonify(game_manager.set_signup_open(data["signup_open"]))


# --- Auth ---

@app.route("/api/auth/dev-login")
def dev_login():
    # Dev-only escape hatch. Fail closed: only available when NODE_ENV is set.
    if not IS_DEV:
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

    return jsonify({
        "is_admin": is_admin,
        "discord_username": user["username"],
        "signup_open": game_manager.get_settings()["signup_open"],
    })


@app.route("/api/auth/me")
def auth_me():
    if "discord_id" not in session:
        return jsonify({"error": "not authenticated"}), 401
    return jsonify({
        "discord_id": session["discord_id"],
        "discord_username": session["discord_username"],
        "is_admin": session.get("is_admin", False),
        "signup_open": game_manager.get_settings()["signup_open"],
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
        return jsonify({"status": "waiting", "lobby_count": 0, "duration_ms": DEFAULT_DURATION_MS})
    return jsonify({"status": g.status, "lobby_count": len(g.lobby), "duration_ms": g.duration_ms})


@app.route("/api/game", methods=["POST"])
def create_game_route():
    if not session.get("is_admin"):
        return jsonify({"error": "forbidden"}), 403
    data = request.get_json() or {}
    duration_ms = data.get("duration_ms", DEFAULT_DURATION_MS)
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


@app.route("/api/game/export", methods=["GET"])
def export_projects():
    if not session.get("is_admin"):
        return jsonify({"error": "forbidden"}), 403
    g = game_manager.game
    if g is None:
        return jsonify({"error": "no game"}), 404

    payload, filename, count = game_manager.build_export_archive(g)
    if count == 0:
        return jsonify({"error": "no projects to export"}), 404

    return Response(
        payload,
        mimetype="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(payload)),
        },
    )


@app.route("/api/game/restore", methods=["POST"])
def restore_projects():
    if not session.get("is_admin"):
        return jsonify({"error": "forbidden"}), 403
    upload = request.files.get("file")
    if upload is None:
        return jsonify({"error": "no file uploaded"}), 400
    try:
        report = game_manager.restore_from_export(upload.read())
    except (ValueError, KeyError) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(report)


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


# --- DevDocs proxy ---

def devdocs_proxy(**_kwargs):
    """Stream a DevDocs response through this origin.

    `request.path` already matches DevDocs' own URL space, so it is passed
    through untouched -- the docs UI keeps working with its absolute /assets
    and /docs links and its root-based client router.
    """
    try:
        upstream = http_requests.get(
            f"{DEVDOCS_UPSTREAM}{request.path}",
            params=request.args,
            stream=True,
            timeout=30,
        )
    except http_requests.RequestException:
        return jsonify({"error": "documentation is unavailable"}), 502

    headers = [
        (name, value)
        for name, value in upstream.raw.headers.items()
        if name.lower() not in _DEVDOCS_SKIP_HEADERS
    ]
    return Response(
        upstream.iter_content(chunk_size=64 * 1024),
        status=upstream.status_code,
        headers=headers,
    )


@app.route("/devdocs")
@app.route("/devdocs/")
def devdocs_root():
    try:
        upstream = http_requests.get(f"{DEVDOCS_UPSTREAM}/", timeout=30)
    except http_requests.RequestException:
        return jsonify({"error": "documentation is unavailable"}), 502
    html = upstream.text.replace(
        "</head>",
        "<script>history.replaceState(null, '', '/');</script></head>",
        1,
    )
    return Response(html, status=upstream.status_code, content_type="text/html; charset=utf-8")


for _prefix in DEVDOCS_PREFIXES:
    app.add_url_rule(f"/{_prefix}/", f"devdocs_{_prefix}", devdocs_proxy)
    app.add_url_rule(f"/{_prefix}/<path:path>", f"devdocs_{_prefix}_sub", devdocs_proxy)
for _name in DEVDOCS_FILES:
    app.add_url_rule(f"/{_name}", f"devdocs_file_{_name.replace('.', '_')}", devdocs_proxy)


# --- SPA fallback ---

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_spa(path: str):
    full = os.path.join(STATIC_DIR, path)
    if path and os.path.isfile(full):
        return send_from_directory(STATIC_DIR, path)
    return send_from_directory(STATIC_DIR, "index.html")


if __name__ == "__main__":
    game_manager.load_settings()
    restored = game_manager.load_state_snapshot()
    if restored is not None:
        print(
            f"[recovery] restored {restored.status} game with "
            f"{len(restored.participants)} participant(s), {len(restored.lobby)} in lobby"
        )
        ws_handler.resume_timer_if_active()
    socketio.run(app, host="0.0.0.0", port=5001)
