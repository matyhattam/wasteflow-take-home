"""A minimal sensor agent.

Samples a value on a fixed interval and exposes it over HTTP:

    GET /health   -> 200, "ok"
    GET /metrics  -> 200, Prometheus text format with the latest reading

Deliberately small and dependency-free (standard library only). Configuration
is read from the environment. How you package, test, build, and deploy this is
up to you.
"""

import os
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SENSOR_ID = os.environ.get("SENSOR_ID", "unknown")
POLL_INTERVAL_SECONDS = float(os.environ.get("POLL_INTERVAL_SECONDS", "5"))
PORT = int(os.environ.get("PORT", "8000"))

# Latest reading, updated in the background and read by the /metrics handler.
_state = {"reading": 0.0, "samples": 0}
_lock = threading.Lock()


def read_sensor():
    """Stand-in for real hardware: returns a fresh reading (0-100)."""
    return random.uniform(0.0, 100.0)


def sample_loop(interval=POLL_INTERVAL_SECONDS):
    while True:
        value = read_sensor()
        with _lock:
            _state["reading"] = value
            _state["samples"] += 1
        time.sleep(interval)


def render_metrics():
    with _lock:
        reading, samples = _state["reading"], _state["samples"]
    return (
        "# HELP sensor_reading Latest sensor reading.\n"
        "# TYPE sensor_reading gauge\n"
        f'sensor_reading{{sensor_id="{SENSOR_ID}"}} {reading}\n'
        "# HELP sensor_samples_total Total samples taken since start.\n"
        "# TYPE sensor_samples_total counter\n"
        f'sensor_samples_total{{sensor_id="{SENSOR_ID}"}} {samples}\n'
    )


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self._respond(200, "text/plain", "ok\n")
        elif self.path == "/metrics":
            self._respond(200, "text/plain; version=0.0.4", render_metrics())
        else:
            self._respond(404, "text/plain", "not found\n")

    def _respond(self, status, content_type, body):
        payload = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass  # keep test/CI output quiet


def main():
    threading.Thread(target=sample_loop, daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"sensor-agent (id={SENSOR_ID}) listening on 0.0.0.0:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
