"""Recorded real BPstat portal-API payloads (tests/ingest/fixtures/bportugal/verify/, fetched
2026-11-11 from the live bpstat.bportugal.pt internal API with RequestsHttp, <=1 req/s;
MANIFEST.json lists every case: series, month window, expected current token as cross-checked
live against the collector's JSON-stat payload at recording time, provenance and sha256) and an
Http double that serves them by request (path + query), like tests/ingest/ine_verifier_fixtures.py.
"""
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from ingest.http import HttpResult

VFIX = Path(__file__).resolve().parent / "fixtures" / "bportugal" / "verify"
VMANIFEST: dict = json.loads((VFIX / "MANIFEST.json").read_text())


def vbody(file: str) -> bytes:
    return (VFIX / file).read_bytes()


def _route(url: str, params: dict | None) -> tuple[str, frozenset]:
    parts = urlsplit(url)
    q = {k: tuple(v) for k, v in parse_qs(parts.query).items()}
    for k, v in (params or {}).items():
        q[k] = (v,)
    return parts.path, frozenset(q.items())


class VerifyFixtureHttp:
    """Serves the recorded verifier-channel bodies. A series-metadata GET routes by its
    series_ids/view_full params; an observations GET routes by its exact month window —
    an unrecorded request fails the test. `override` maps a case key to replacement bytes
    (tampering tests)."""

    def __init__(self, override: dict[str, bytes] | None = None):
        self.override = override or {}
        self.calls: list[tuple[str, str]] = []  # ("meta", sid) | ("obs", key)
        self.routes = {}
        for sid, m in VMANIFEST["meta"].items():
            self.routes[_route(m["url"], None)] = ("meta", sid)
        for key, m in VMANIFEST["cases"].items():
            self.routes[_route(m["url"], None)] = ("obs", key)

    def get(self, url, params=None, headers=None, timeout=None):
        routed = self.routes.get(_route(url, params))
        if routed is None:
            raise AssertionError(f"no recorded verifier response for {url} {params}")
        kind, key = routed
        self.calls.append((kind, key))
        m = VMANIFEST["meta" if kind == "meta" else "cases"][key]
        return HttpResult(status=200, body=self.override.get(key, vbody(m["file"])), url=m["url"])
