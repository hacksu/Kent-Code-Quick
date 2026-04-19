# Coding Event Platform — Implementation Plan

## Stack

- **SvelteKit** (`adapter-static` — compiled to a plain SPA)
- **Flask** + **flask-socketio** + **gevent** — serves static build, handles WebSockets and REST API
- **CodeMirror 6** — editor with paste/copy disabled
- **In-memory state** — no database needed for a single event

### Why this split

SvelteKit is built as a static SPA (`adapter-static`), then Flask serves the output files alongside the WebSocket and API handlers. Single server, single process, simple ops. The trade-off is losing SvelteKit SSR (`+page.server.ts`), which this app doesn't meaningfully need.

---

## Project Structure

```
project/
  frontend/                     # SvelteKit project
    src/
      lib/
        components/
          Editor.svelte          # CodeMirror 6 wrapper
          Preview.svelte         # sandboxed iframe (local only, no WS round-trip)
          Timer.svelte
          ParticipantCard.svelte # mini preview + name for presenter grid
        stores/
          room.svelte.ts         # runes-based reactive store
      routes/
        +page.svelte             # landing: enter room code
        room/[code]/
          +page.svelte           # participant IDE view
        presenter/[code]/
          +page.svelte           # presenter: grid of live previews + timer
        admin/[code]/
          +page.svelte           # flip through projects + code, end event
    svelte.config.js             # adapter-static
  backend/
    app.py                       # Flask entry point
    room_manager.py              # in-memory state: rooms, participants, timers
    ws_handler.py                # flask-socketio event handlers
    requirements.txt
```

---

## Flask Server

```python
# backend/app.py
from flask import Flask, send_from_directory
from flask_socketio import SocketIO
import os

app = Flask(__name__, static_folder="../frontend/build")
socketio = SocketIO(app, async_mode="gevent", cors_allowed_origins="*")

# Serve SvelteKit static build
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_svelte(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")

# Import WS event handlers (registers @socketio.on decorators)
import ws_handler  # noqa: F401

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
```

```
# backend/requirements.txt
flask
flask-socketio
gevent
gevent-websocket
```

---

## WebSocket Events

Flask-SocketIO uses named events rather than a single message type. Client uses the `socket.io` JS client.

**Client → Server:**

| Event | Payload |
|---|---|
| `join` | `{ roomCode, name, role, token }` |
| `code_update` | `{ html, css }` |
| `tab_out` | `{ penalty }` |
| `submit` | _(none)_ |
| `end_event` | _(none, admin only)_ |

**Server → Client:**

| Event | Payload |
|---|---|
| `room_state` | `{ participants: [...] }` |
| `participant_update` | `{ id, name, html, css }` |
| `penalty` | `{ seconds, totalPenalty }` |
| `timer_tick` | `{ elapsed, ended }` |
| `event_end` | _(none)_ |

```python
# backend/ws_handler.py
from flask import request
from flask_socketio import socketio, join_room, emit
from room_manager import get_or_create_room, get_participant, apply_penalty, snapshot_participant

@socketio.on("join")
def on_join(data):
    room = get_or_create_room(data["roomCode"])
    participant = get_participant(room, token=data.get("token"), name=data["name"])
    join_room(data["roomCode"])
    emit("room_state", room.to_dict(), to=data["roomCode"])

@socketio.on("code_update")
def on_code_update(data):
    # update participant state, broadcast to presenter
    ...

@socketio.on("tab_out")
def on_tab_out(data):
    penalty = apply_penalty(request.sid, data["penalty"])
    emit("penalty", penalty, to=request.sid)
    # broadcast updated timer to presenter view

@socketio.on("submit")
def on_submit():
    snapshot_participant(request.sid)
    emit("submitted", {}, to=request.sid)
```

---

## Room State (`room_manager.py`)

```python
from dataclasses import dataclass, field
from typing import Optional
import time, json, threading

@dataclass
class Participant:
    id: str                        # stable token from localStorage
    name: str
    sid: str                       # current socket session id
    html: str = ""
    css: str = ""
    penalty_ms: int = 0
    tab_out_count: int = 0
    submitted_at: Optional[float] = None
    final_html: Optional[str] = None   # snapshot on submit or timer end
    final_css: Optional[str] = None

@dataclass
class RoomState:
    code: str
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    duration_ms: int = 45 * 60 * 1000
    participants: dict = field(default_factory=dict)  # token -> Participant

rooms: dict[str, RoomState] = {}
```

**Penalty direction:** penalties add to `elapsed` display time. Higher elapsed = worse if scoring by time-to-finish. Make this explicit in comments.

**Crash resilience:** run a background thread that writes room state to a JSON file every 30 seconds. Cheap insurance for a 45-minute event.

```python
def _backup_loop():
    while True:
        time.sleep(30)
        with open("room_backup.json", "w") as f:
            json.dump({code: room.to_dict() for code, room in rooms.items()}, f)

threading.Thread(target=_backup_loop, daemon=True).start()
```

---

## Participant Reconnection

On first join, the server generates a short token and sends it back. The client stores it in `localStorage` and sends it on every subsequent connection.

```python
@socketio.on("join")
def on_join(data):
    token = data.get("token")
    if token and token in room.participants:
        # rejoin: restore existing participant, update sid
        participant = room.participants[token]
        participant.sid = request.sid
    else:
        # new participant: generate token
        token = secrets.token_urlsafe(8)
        participant = Participant(id=token, name=data["name"], sid=request.sid)
        room.participants[token] = participant
        emit("token_assigned", {"token": token}, to=request.sid)
```

```ts
// room.svelte.ts — on connect
const token = localStorage.getItem("eventToken") ?? undefined;
socket.emit("join", { roomCode, name, role, token });

socket.on("token_assigned", ({ token }) => {
  localStorage.setItem("eventToken", token);
});
```

---

## Timer

A background thread in Flask ticks every second and broadcasts `timer_tick` to the room via `socketio.emit`. Server is authoritative — clients only render what they receive.

```python
def run_timer(room_code: str):
    room = rooms[room_code]
    while True:
        gevent.sleep(1)
        if room.ended_at:
            break
        elapsed = (time.time() - room.started_at) * 1000  # ms
        ended = elapsed >= room.duration_ms
        socketio.emit("timer_tick", {"elapsed": elapsed, "ended": ended}, to=room_code)
        if ended:
            _auto_snapshot_all(room)
            break
```

When `elapsed > duration_ms`, client displays red negative countdown. Admin sends `end_event` which sets `ended_at` and freezes all editors early.

---

## Participant IDE View

### Layout

```
┌──────────────────────────────────────────────────────────┐
│  [penalty banner if active]          [timer - top right]  │
├───────────────────────┬──────────────────────────────────┤
│  [HTML tab] [CSS tab] │                                  │
│                       │        LIVE PREVIEW              │
│   CODE EDITOR         │        (iframe sandbox)          │
│   (CodeMirror 6)      │                                  │
│                       │                                  │
├───────────────────────┴──────────────────────────────────┤
│  [DOCS panel - toggleable]          [SUBMIT button]       │
└──────────────────────────────────────────────────────────┘
```

### Copy/Paste Blocking

Block at two levels:

```ts
// 1. CodeMirror extension
const noPasteCopyExtension = EditorView.domEventHandlers({
  paste: (e) => { e.preventDefault(); return true; },
  copy:  (e) => { e.preventDefault(); return true; },
  cut:   (e) => { e.preventDefault(); return true; },
});

// 2. Document-level capture (catches paste when editor lacks focus)
document.addEventListener("paste", (e) => e.preventDefault(), true);
document.addEventListener("copy",  (e) => e.preventDefault(), true);
```

### Tab-Out Penalty

```ts
const penalties = [5, 25, 60, 120, 240, 480, 960]; // seconds, escalating
let penaltyStep = 0;

document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    const penalty = penalties[Math.min(penaltyStep, penalties.length - 1)];
    penaltyStep++;
    socket.emit("tab_out", { penalty });
  }
});
```

### Live Preview

Preview updates **locally only** — no WS round-trip for the participant's own preview. `code_update` events are debounced (300ms) and emitted only for the presenter grid.

```svelte
<!-- Preview.svelte -->
<script lang="ts">
  let { html, css }: { html: string; css: string } = $props();

  // blob URL avoids layout thrashing on large srcdoc strings
  let previewUrl = $derived.by(() => {
    const doc = `<!DOCTYPE html><html><head><style>${css}</style></head><body>${html}</body></html>`;
    const blob = new Blob([doc], { type: "text/html" });
    return URL.createObjectURL(blob);
  });
</script>

<iframe sandbox="allow-scripts" src={previewUrl} title="preview" class="w-full h-full border-none" />
```

### Final Submission

Explicit **Submit** button emits `submit` to the server. Server snapshots `html`/`css` into `final_html`/`final_css` with a timestamp. Also auto-snapshots when the timer hits zero for anyone who hasn't submitted.

Prevents "I was mid-edit" disputes during judging.

---

## Presenter View

```
┌──────────────────────────────────────────────────┐
│              ⏱  12:34       [END EVENT - admin]  │
├──────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ preview  │  │ preview  │  │ preview  │       │
│  │  Alice   │  │   Bob    │  │  Carol   │  ...  │
│  └──────────┘  └──────────┘  └──────────┘       │
└──────────────────────────────────────────────────┘
```

**Performance:** throttle incoming `participant_update` events to 1–2/sec per card on the client. Lazy-load iframes that are off-screen. With 20+ live iframes re-rendering constantly, unthrottled updates will cause visible frame drops.

---

## Documentation Panel

**Recommended: Option A — static snapshots**

Download MDN/W3Schools pages at build time and serve from Flask as static files. No external network dependency during the event.

**Option B — allowlisted proxy** (fallback if static snapshots are too large):

```python
# backend/app.py
from urllib.parse import urlparse
import requests

ALLOWED_HOSTS = {"developer.mozilla.org", "www.w3schools.com"}

@app.route("/api/docs")
def docs_proxy():
    target = request.args.get("url", "")
    hostname = urlparse(target).hostname
    if hostname not in ALLOWED_HOSTS:
        return "Blocked", 403
    res = requests.get(target)
    return res.text, 200, {"Content-Type": "text/html"}
```

---

## Admin Review Mode (`/admin/[code]`)

- Participant list on the left
- Click a participant: read-only CodeMirror showing `final_html`/`final_css` + rendered preview side by side
- Show accumulated penalty time per participant
- Protected by a simple shared secret passed as a query param (fine for an in-person event)

```python
@app.route("/api/room/<code>/results")
def room_results(code):
    if request.args.get("secret") != os.environ.get("ADMIN_SECRET"):
        return "Forbidden", 403
    room = rooms.get(code)
    if not room:
        return "Not found", 404
    return jsonify(room.to_dict())
```

---

## Known Limitations

| Limitation | Mitigation |
|---|---|
| OS-level copy/paste can't be blocked | Penalty system + social pressure of projector visibility |
| New browser window bypasses Page Visibility | Same as above |
| Server crash loses all state | 30s JSON backup via background thread |
| Iframes are heavy at scale | Throttle + lazy-load on presenter view |
| No SvelteKit SSR | Not needed — all dynamic state comes from SocketIO |
