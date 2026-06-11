"""
LeetCode Automation Dashboard — Flask Server
Provides REST API + SSE streaming for the mobile web interface.
Run: python dashboard/server.py
Then open http://<your-pc-ip>:5050 on your phone.
"""

import json
import os
import sys
import re
import queue
import threading
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, Response, send_from_directory
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from functools import wraps

# ── Authentication ─────────────────────────────────────────────────────────
def check_auth(username, password):
    try:
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
        auth = cfg.get("dashboard_auth", {})
        valid_user = auth.get("username", "admin")
        valid_pass = auth.get("password", "password123")
        return username == valid_user and password == valid_pass
    except Exception:
        return username == 'admin' and password == 'password123'

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return Response(
                'Could not verify your access level for that URL.\n'
                'You have to login with proper credentials', 401,
                {'WWW-Authenticate': 'Basic realm="Login Required"'}
            )
        return f(*args, **kwargs)
    return decorated

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
CONFIG_PATH = BASE_DIR / "config.json"
LOG_PATH    = BASE_DIR / "logs" / "automation.log"
HISTORY_PATH= BASE_DIR / "logs" / "history.json"

app = Flask(__name__, static_folder="static")
CORS(app)

scheduler = BackgroundScheduler()
scheduler.start()
automation_job_id = "automation_job"

# ── State ──────────────────────────────────────────────────────────────────
automation_state = {
    "status": "idle",          # idle | running | completed | error
    "current_problem": None,
    "progress": 0,             # 0-5
    "total": 5,
    "last_run": None,
    "next_run": None,
    "results": [],
    "pid": None,
}

# SSE subscriber queues
sse_clients: list[queue.Queue] = []
sse_lock = threading.Lock()

# ── Config helpers ─────────────────────────────────────────────────────────

def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)

def save_config(cfg: dict):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)

# ── History helpers ────────────────────────────────────────────────────────

def load_history() -> list:
    if HISTORY_PATH.exists():
        try:
            with open(HISTORY_PATH) as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(entry: dict):
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    history = load_history()
    history.insert(0, entry)
    history = history[:30]  # Keep last 30 days
    with open(HISTORY_PATH, "w") as f:
        json.dump(history, f, indent=2)

# ── SSE helpers ────────────────────────────────────────────────────────────

def broadcast(event_type: str, data: dict):
    """Send an SSE event to all connected clients."""
    msg = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    with sse_lock:
        dead = []
        for q in sse_clients:
            try:
                q.put_nowait(msg)
            except queue.Full:
                dead.append(q)
        for q in dead:
            sse_clients.remove(q)

def broadcast_log(line: str):
    broadcast("log", {"line": line, "ts": datetime.now().strftime("%H:%M:%S")})

def broadcast_state():
    broadcast("state", automation_state)

# ── Log tail helper ────────────────────────────────────────────────────────

def tail_log(n: int = 100) -> list[str]:
    if not LOG_PATH.exists():
        return []
    with open(LOG_PATH, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    return [l.rstrip() for l in lines[-n:]]

# ── Automation runner (in thread) ──────────────────────────────────────────

def _run_automation_thread():
    """Run main.py as subprocess and stream its output."""
    automation_state["status"] = "running"
    automation_state["progress"] = 0
    automation_state["results"] = []
    automation_state["current_problem"] = None
    broadcast_state()

    python = sys.executable
    proc = subprocess.Popen(
        [python, str(BASE_DIR / "main.py"), "--once"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        cwd=str(BASE_DIR),
    )
    automation_state["pid"] = proc.pid

    problem_re = re.compile(r"Problem (\d+)/(\d+): (.+)")
    accepted_re = re.compile(r"ACCEPTED")
    failed_re   = re.compile(r"(Wrong Answer|Runtime Error|Time Limit|FAILED|SKIPPED)")
    result_re   = re.compile(r"(ACCEPTED|Wrong Answer|Runtime Error|Time Limit|FAILED|SKIPPED)")

    current = {}
    for line in proc.stdout:
        line = line.rstrip()
        if not line:
            continue

        broadcast_log(line)

        # Parse progress
        m = problem_re.search(line)
        if m:
            idx, total, title = int(m.group(1)), int(m.group(2)), m.group(3)
            automation_state["progress"] = idx - 1
            automation_state["total"] = total
            automation_state["current_problem"] = title
            current = {"idx": idx, "title": title}
            broadcast_state()

        if accepted_re.search(line) and current:
            runtime_m = re.search(r"Runtime: (.+?) \|", line)
            memory_m  = re.search(r"Memory: (.+)", line)
            current["status"] = "ACCEPTED"
            current["runtime"] = runtime_m.group(1) if runtime_m else "N/A"
            current["memory"]  = memory_m.group(1) if memory_m else "N/A"
            
            # Check if this is an update to an already failed attempt
            updated = False
            for r in automation_state["results"]:
                if r["idx"] == current["idx"]:
                    r.update(current)
                    updated = True
                    break
            
            if not updated:
                automation_state["results"].append(dict(current))
                
            automation_state["progress"] = current["idx"]
            current = {}
            broadcast_state()

        elif failed_re.search(line) and current:
            fm = result_re.search(line)
            current["status"] = fm.group(1) if fm else "FAILED"
            
            updated = False
            for r in automation_state["results"]:
                if r["idx"] == current["idx"]:
                    r.update(current)
                    updated = True
                    break
                    
            if not updated:
                automation_state["results"].append(dict(current))
                
            automation_state["progress"] = current["idx"]
            # Don't clear current immediately so we can catch "Alternative solution ACCEPTED!"
            broadcast_state()

        elif "Alternative solution ACCEPTED!" in line:
            # We already have it in results as FAILED, update it
            for r in automation_state["results"]:
                if current and r["idx"] == current["idx"]:
                    r["status"] = "ACCEPTED"
                    break
            if current:
                current["status"] = "ACCEPTED"
                current = {}
            broadcast_state()

    proc.wait()
    automation_state["pid"] = None

    if proc.returncode == 0:
        automation_state["status"] = "completed"
    else:
        automation_state["status"] = "error"

    automation_state["last_run"] = datetime.now().isoformat()
    automation_state["current_problem"] = None

    # Update next_run
    cfg = load_config()
    run_time = cfg["automation"]["run_time"]
    h, m_part = map(int, run_time.split(":"))
    now = datetime.now()
    next_dt = now.replace(hour=h, minute=m_part, second=0, microsecond=0)
    if next_dt <= now:
        next_dt += timedelta(days=1)
    automation_state["next_run"] = next_dt.isoformat()

    # Save to history
    accepted = sum(1 for r in automation_state["results"] if "ACCEPTED" in r.get("status", ""))
    save_history({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M"),
        "total": automation_state["total"],
        "accepted": accepted,
        "results": automation_state["results"],
    })

    broadcast_state()

# ── API Routes ─────────────────────────────────────────────────────────────

@app.route("/api/status")
@requires_auth
def api_status():
    cfg = load_config()
    return jsonify({
        **automation_state,
        "schedule": {
            "run_time": cfg["automation"]["run_time"],
            "problems_per_day": cfg["automation"]["problems_per_day"],
            "difficulty_mix": cfg["automation"]["difficulty_mix"],
        }
    })


@app.route("/api/run-now", methods=["POST"])
@requires_auth
def api_run_now():
    if automation_state["status"] == "running":
        return jsonify({"error": "Already running"}), 409
    t = threading.Thread(target=_run_automation_thread, daemon=True)
    t.start()
    return jsonify({"ok": True, "message": "Automation started"})


@app.route("/api/stop", methods=["POST"])
@requires_auth
def api_stop():
    pid = automation_state.get("pid")
    if pid:
        try:
            import signal
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass
    automation_state["status"] = "idle"
    automation_state["pid"] = None
    broadcast_state()
    return jsonify({"ok": True})


@app.route("/api/schedule", methods=["GET", "POST"])
@requires_auth
def api_schedule():
    cfg = load_config()
    if request.method == "POST":
        body = request.json or {}
        if "run_time" in body:
            cfg["automation"]["run_time"] = body["run_time"]
        if "problems_per_day" in body:
            cfg["automation"]["problems_per_day"] = int(body["problems_per_day"])
        if "difficulty_mix" in body:
            cfg["automation"]["difficulty_mix"] = body["difficulty_mix"]
        save_config(cfg)

        # Recompute next_run
        run_time = cfg["automation"]["run_time"]
        h, m_part = map(int, run_time.split(":"))
        now = datetime.now()
        next_dt = now.replace(hour=h, minute=m_part, second=0, microsecond=0)
        if next_dt <= now:
            next_dt += timedelta(days=1)
        automation_state["next_run"] = next_dt.isoformat()
        broadcast_state()

        # Update APScheduler
        try:
            scheduler.reschedule_job(automation_job_id, trigger=CronTrigger(hour=h, minute=m_part))
        except Exception as e:
            print(f"Failed to reschedule job: {e}")

        return jsonify({"ok": True, "config": cfg["automation"]})

    return jsonify(cfg["automation"])


@app.route("/api/history")
@requires_auth
def api_history():
    return jsonify(load_history())


@app.route("/api/logs")
@requires_auth
def api_logs():
    n = int(request.args.get("n", 100))
    return jsonify({"lines": tail_log(n)})


@app.route("/api/config", methods=["GET", "POST"])
@requires_auth
def api_config():
    cfg = load_config()
    if request.method == "POST":
        body = request.json or {}
        # Only allow safe fields to be updated
        if "leetcode" in body:
            for k in ("username",):  # don't expose password changes via API
                if k in body["leetcode"]:
                    cfg["leetcode"][k] = body["leetcode"][k]
        if "email" in body:
            for k in ("receiver_email",):
                if k in body["email"]:
                    cfg["email"][k] = body["email"][k]
        save_config(cfg)
        return jsonify({"ok": True})
    # Mask sensitive fields
    safe = json.loads(json.dumps(cfg))
    safe["leetcode"]["password"] = "••••••••"
    safe["email"]["sender_password"] = "••••••••"
    return jsonify(safe)


@app.route("/api/register-task", methods=["POST"])
@requires_auth
def api_register_task():
    """Register automation as a Windows Scheduled Task."""
    try:
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "setup_scheduler.py")],
            capture_output=True, text=True, cwd=str(BASE_DIR)
        )
        if result.returncode == 0:
            return jsonify({"ok": True, "output": result.stdout})
        else:
            return jsonify({"ok": False, "error": result.stderr or result.stdout}), 500
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/stream")
@requires_auth
def api_stream():
    """Server-Sent Events endpoint for real-time updates."""
    q: queue.Queue = queue.Queue(maxsize=200)
    with sse_lock:
        sse_clients.append(q)

    def generate():
        # Send current state immediately
        yield f"event: state\ndata: {json.dumps(automation_state)}\n\n"
        try:
            while True:
                try:
                    msg = q.get(timeout=25)
                    yield msg
                except queue.Empty:
                    yield ": ping\n\n"  # keep-alive
        except GeneratorExit:
            with sse_lock:
                if q in sse_clients:
                    sse_clients.remove(q)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


# ── Serve the frontend ─────────────────────────────────────────────────────

@app.route("/")
@requires_auth
def index():
    return send_from_directory(Path(__file__).parent, "index.html")


@app.route("/<path:path>")
@requires_auth
def static_files(path):
    return send_from_directory(Path(__file__).parent, path)


# ── Boot ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import socket
    import os
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Compute initial next_run
    try:
        cfg = load_config()
        run_time = cfg["automation"]["run_time"]
        h, m_part = map(int, run_time.split(":"))
        now = datetime.now()
        next_dt = now.replace(hour=h, minute=m_part, second=0, microsecond=0)
        if next_dt <= now:
            next_dt += timedelta(days=1)
        automation_state["next_run"] = next_dt.isoformat()

        # Schedule the job in APScheduler
        scheduler.add_job(
            func=lambda: threading.Thread(target=_run_automation_thread, daemon=True).start() if automation_state["status"] != "running" else None,
            trigger=CronTrigger(hour=h, minute=m_part),
            id=automation_job_id,
            replace_existing=True
        )
    except Exception as e:
        print(f"Error setting up schedule: {e}")

    # Print access info
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "localhost"

    sep = "=" * 55
    print("\n" + sep)
    print("  [*] LeetCode Automation Dashboard")
    print(sep)
    print(f"  Local:   http://localhost:5050")
    print(f"  Phone:   http://{local_ip}:5050")
    print("  (Make sure your phone is on the same WiFi)")
    print(sep + "\n")

    app.run(host="0.0.0.0", port=5050, debug=False, threaded=True)

