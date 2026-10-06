import json
import re
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import evidence_db as db
import pipeline

HOST, PORT = "127.0.0.1", 8000
ALLOWED_HOSTS = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}
WEB = Path(__file__).parent / "web"
INDEX = WEB / "index.html"
STATIC = {"/logo.png": "logo.png", "/favicon.png": "favicon.png"}

STATE = {"state": "idle", "stage": 0, "titles": [], "result": None,
         "error": None, "question": ""}
LOCK = threading.Lock()


def _log(msg):
    """Turn the pipeline's log lines into a stage number for the page."""
    with LOCK:
        if msg.startswith("[1/4]"):
            STATE["stage"] = 1
        elif msg.startswith("[2/4]"):
            STATE["stage"] = 2
        elif msg.startswith("[3/4]"):
            STATE["stage"] = 3
        elif msg.startswith("        - "):
            STATE["titles"].append(msg.strip()[2:])


def _build_result(out):
    if not out["ok"]:
        reason = out["note"] or "The draft did not pass its citation check, so it was not shown."
        return {"ok": False, "reason": reason}

    body = out["report"].split("\n\n## References")[0]
    ids = []
    for n in re.findall(r"\[(\d+)\]", body):
        if int(n) not in ids:
            ids.append(int(n))

    sources = []
    for sid in ids:
        src = db.get_source(sid)
        if src:
            sources.append({"id": sid, "title": src["title"], "url": src["url"]})

    claims = db.get_claims()
    counts = {s: sum(1 for c in claims if c["status"] == s)
              for s in ("supported", "partial", "unsupported")}
    return {"ok": True, "body": body, "sources": sources, "claims": counts}


def _work(question):
    try:
        out = pipeline.run(question, log=_log)
        result = _build_result(out)
        with LOCK:
            STATE.update(state="done", stage=4, result=result)
    except Exception as e:  # shown to the user in plain words by the page
        with LOCK:
            STATE.update(state="error", error=f"{type(e).__name__}: {e}"[:300])


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        ct = ctype if ctype.startswith("image/") else ctype + "; charset=utf-8"
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _host_ok(self):
        # blocks other websites from driving this local server through your browser
        return self.headers.get("Host") in ALLOWED_HOSTS

    def do_GET(self):
        if not self._host_ok():
            return self._send(403, {"error": "forbidden"})
        if self.path == "/":
            return self._send(200, INDEX.read_bytes(), "text/html")
        if self.path in STATIC:  # fixed list of files, nothing else can be requested
            return self._send(200, (WEB / STATIC[self.path]).read_bytes(), "image/png")
        if self.path == "/api/status":
            with LOCK:
                snapshot = dict(STATE)
            return self._send(200, snapshot)
        self._send(404, {"error": "not found"})

    def do_POST(self):
        if not self._host_ok():
            return self._send(403, {"error": "forbidden"})
        if self.path != "/api/ask":
            return self._send(404, {"error": "not found"})
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self._send(415, {"error": "Expected JSON."})
        length = int(self.headers.get("Content-Length", 0))
        if length > 4096:
            return self._send(413, {"error": "That request is too large."})
        try:
            question = str(json.loads(self.rfile.read(length)).get("question", "")).strip()
        except (ValueError, AttributeError):
            return self._send(400, {"error": "The request could not be read."})
        if not 5 <= len(question) <= 500:
            return self._send(400, {"error": "Write a question between 5 and 500 characters."})
        with LOCK:
            if STATE["state"] == "running":
                return self._send(409, {"error": "A question is already being researched."})
            STATE.update(state="running", stage=0, titles=[], result=None,
                         error=None, question=question)
        threading.Thread(target=_work, args=(question,), daemon=True).start()
        self._send(202, {"ok": True})

    def log_message(self, *args):
        pass  # keep the terminal quiet


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"Synthesis is running at {url} (press Ctrl+C to stop)")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")