"""Recorded genuine E-REDES verifier-channel payloads (the /exports/csv of the same window the
collector fixtures cover + the metadata response for unit labels; tests/ingest/fixtures/eredes/,
2026-11-12, MANIFEST.json) and an Http double, like tests/ingest/ren_verifier_fixtures.py.
Nothing here imports the collector side.
"""
import base64
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from ingest.http import HttpResult

VFIX = Path(__file__).resolve().parent / "fixtures" / "eredes"
VMANIFEST: dict = json.loads((VFIX / "MANIFEST.json").read_text())["sets"]

VERIFIER_SETS = ("window_csv", "summer_window_csv", "metadata")


def vbody(name: str) -> bytes:
    return (VFIX / VMANIFEST[name]["file"]).read_bytes()


def decode_evidence(blob: bytes) -> list[dict]:
    """Offline (no HTTP) read of an item's versioned 'eredes-csv-evidence' v1 envelope: exact
    wire records (final URL, ACTUAL HTTP status, byte-recovered body) of the deciding CSV
    response and the unit metadata response, in that order."""
    doc = json.loads(blob)
    assert doc["schema"] == "eredes-csv-evidence" and doc["version"] == 1
    return [{"url": r["url"], "status": r["status"],
             "body": base64.b64decode(r["body_base64"], validate=True)}
            for r in doc["responses"]]


def _route(url: str, params: dict | None) -> tuple[str, frozenset]:
    parts = urlsplit(url)
    q = {k: tuple(v) for k, v in parse_qs(parts.query).items()}
    for k, v in (params or {}).items():
        q[k] = (str(v),)
    return parts.path, frozenset(q.items())


class VerifyFixtureHttp:
    """Serves the recorded CSV export + metadata by exact request; `override` maps a set name
    to replacement bytes (labelled synthetic tampering)."""

    def __init__(self, override: dict[str, bytes] | None = None):
        self.override = override or {}
        self.calls: list[str] = []
        self.routes = {_route(m["url"], m["params"]): name
                       for name, m in VMANIFEST.items() if name in VERIFIER_SETS}

    def get(self, url, params=None, headers=None, timeout=None):
        name = self.routes.get(_route(url, params))
        if name is None:
            raise AssertionError(f"no recorded eredes verifier response for {url} {params}")
        self.calls.append(name)
        m = VMANIFEST[name]
        return HttpResult(status=m["status"], body=self.override.get(name, vbody(name)),
                          url=m["url"])
