"""Zero-dependency web demo (standard-library HTTP server + one HTML page).

  python -m triage.train          # once
  python demo/server.py           # then open http://localhost:8000

Endpoints: GET /  |  POST /api/triage {text, t_urgent?, t_cat?}  |  POST /api/feedback {text, prediction, verdict, comment}
Feedback is appended to demo/feedback_log.jsonl so people who try the demo can leave structured feedback.
"""
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from triage.cli import load_model, triage_text  # noqa: E402

HERE = Path(__file__).resolve().parent
MODEL, META = load_model()
FEEDBACK = HERE / "feedback_log.jsonl"


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            html = (HERE / "index.html").read_bytes()
            self._send(200, html, "text/html; charset=utf-8")
        elif self.path == "/api/meta":
            self._send(200, {k: META[k] for k in ("t_urgent", "t_cat", "regime", "n_train", "classes", "trained_at")})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._send(400, {"error": "bad json"})
        if self.path == "/api/triage":
            text = str(body.get("text", "")).strip()
            if not text:
                return self._send(400, {"error": "empty text"})
            t0 = time.perf_counter()
            tu = body.get("t_urgent")
            tc = body.get("t_cat")
            res = triage_text(MODEL, text[:2000], t_urgent=None if tu is None else float(tu), t_cat=None if tc is None else float(tc))
            res["explain"] = MODEL.explain(text[:2000])
            res["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
            self._send(200, res)
        elif self.path == "/api/feedback":
            rec = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), **{k: body.get(k) for k in ("text", "prediction", "verdict", "comment")}}
            with open(FEEDBACK, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")
            self._send(200, {"ok": True})
        else:
            self._send(404, {"error": "not found"})

    def log_message(self, fmt, *args):  # keep console quiet
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"Incident triage demo on http://localhost:{port}  (model trained {META['trained_at']}, regime={META['regime']})")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
