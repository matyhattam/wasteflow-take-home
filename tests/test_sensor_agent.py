"""Starter tests. Feel free to extend, restructure, or replace these."""

import threading
import urllib.request
from http.server import ThreadingHTTPServer

from sensor_agent import agent


def _start_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), agent.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _get(server, path):
    port = server.server_address[1]
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}") as r:
        return r.status, r.read().decode()


def test_health_ok():
    server = _start_server()
    try:
        status, body = _get(server, "/health")
        assert status == 200
        assert body == "ok\n"
    finally:
        server.shutdown()


def test_metrics_exposes_reading():
    server = _start_server()
    try:
        status, body = _get(server, "/metrics")
        assert status == 200
        assert "sensor_reading" in body
        assert "sensor_samples_total" in body
    finally:
        server.shutdown()


def test_read_sensor_in_range():
    for _ in range(100):
        assert 0.0 <= agent.read_sensor() <= 100.0
