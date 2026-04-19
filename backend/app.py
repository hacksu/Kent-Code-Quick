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

app = Flask(__name__)
socketio.init_app(app, async_mode="gevent", cors_allowed_origins="*")


ADMIN_SECRET = os.environ.get("ADMIN_SECRET")
if not ADMIN_SECRET:
    raise RuntimeError("ADMIN_SECRET environment variable must be set")
DOCS_ALLOWLIST = {"developer.mozilla.org", "www.w3schools.com"}


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
