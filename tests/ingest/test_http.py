"""RequestsHttp against a local http.server thread (no external network)."""
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import requests

from ingest.http import USER_AGENT, HttpResult, RequestsHttp


class _Handler(BaseHTTPRequestHandler):
    # Scripted per-path behaviour; set by the fixture.
    script: dict = {}
    calls: list = []

    def log_message(self, *args):
        pass

    def do_GET(self):
        path = self.path.split("?")[0]
        type(self).calls.append((path, self.headers.get("User-Agent"), time.monotonic(), self.path))
        steps = type(self).script.get(path, [(200, b"ok")])
        step = steps.pop(0) if len(steps) > 1 else steps[0]
        status, body = step[0], step[1]
        if status == "sleep":
            time.sleep(body)
            status, body = 200, b"late"
        self.send_response(status)
        if 300 <= status < 400:
            self.send_header("Location", body.decode())
            body = b""
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except BrokenPipeError:  # client already timed out
            pass


@pytest.fixture
def server():
    _Handler.script = {}
    _Handler.calls = []
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    t = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", _Handler
    srv.shutdown()
    srv.server_close()


def test_success_returns_body_status_url_and_user_agent(server):
    base, h = server
    h.script["/a"] = [(200, b'{"x": 1}')]
    r = RequestsHttp(throttle_rps=100).get(base + "/a", params={"q": "1"})
    assert r == HttpResult(status=200, body=b'{"x": 1}', url=base + "/a?q=1")
    assert h.calls[0][1] == USER_AGENT == "prumo-ingest/1.0 (+https://cae.joao.date)"
    assert h.calls[0][3] == "/a?q=1"


def test_500_then_200_is_retried(server):
    base, h = server
    h.script["/b"] = [(500, b"boom"), (200, b"fine")]
    r = RequestsHttp(throttle_rps=100, backoff=0.01).get(base + "/b")
    assert (r.status, r.body) == (200, b"fine")
    assert len(h.calls) == 2


def test_persistent_5xx_returns_last_result_after_3_retries(server):
    base, h = server
    h.script["/c"] = [(503, b"down")]
    r = RequestsHttp(throttle_rps=100, backoff=0.0).get(base + "/c")
    assert r.status == 503
    assert len(h.calls) == 4  # 1 attempt + 3 retries


def test_4xx_is_not_retried(server):
    base, h = server
    h.script["/d"] = [(404, b"nope")]
    r = RequestsHttp(throttle_rps=100, backoff=0.0).get(base + "/d")
    assert r.status == 404
    assert len(h.calls) == 1


def test_throttle_spaces_calls(server):
    base, h = server
    http = RequestsHttp(throttle_rps=5)  # >= 0.2 s between calls
    for _ in range(3):
        http.get(base + "/e")
    gaps = [b[2] - a[2] for a, b in zip(h.calls, h.calls[1:])]
    assert all(g >= 0.18 for g in gaps), gaps


def test_timeout_raises_after_retries(server):
    base, h = server
    h.script["/slow"] = [("sleep", 0.5)]
    with pytest.raises(requests.Timeout):
        RequestsHttp(throttle_rps=100, timeout=0.1, backoff=0.0).get(base + "/slow")
    assert len(h.calls) == 4


def test_connection_error_raises(server):
    base, _ = server
    dead = "http://127.0.0.1:1/x"
    with pytest.raises(requests.ConnectionError):
        RequestsHttp(throttle_rps=100, backoff=0.0).get(dead)


def test_follows_http_redirect(server):
    base, h = server
    h.script["/r"] = [(302, b"/target")]
    h.script["/target"] = [(200, b"here")]
    r = RequestsHttp(throttle_rps=100).get(base + "/r")
    assert (r.status, r.body, r.url) == (200, b"here", base + "/target")


def test_refuses_redirect_to_non_http_scheme(server):
    base, h = server
    h.script["/evil"] = [(302, b"file:///etc/passwd")]
    with pytest.raises(ValueError, match="non-http"):
        RequestsHttp(throttle_rps=100).get(base + "/evil")
