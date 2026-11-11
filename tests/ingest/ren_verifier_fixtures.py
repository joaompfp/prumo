"""Recorded real REN portal CSV-export payloads (tests/ingest/fixtures/ren/verify/, fetched
2026-11-11 from the live datahub.ren.pt export service; byte-identical copies of the Task 12
discovery archive) and an Http double that serves them by request, like
tests/ingest/bportugal_verifier_fixtures.py."""
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from ingest.http import HttpResult

VFIX = Path(__file__).resolve().parent / "fixtures" / "ren"
VMANIFEST: dict = json.loads((VFIX / "MANIFEST.json").read_text())["verify_sets"]


def vbody(file: str) -> bytes:
    return (VFIX / file).read_bytes()


def _route(url: str, params: dict | None) -> tuple[str, frozenset]:
    parts = urlsplit(url)
    q = {k: tuple(v) for k, v in parse_qs(parts.query).items()}
    for k, v in (params or {}).items():
        q[k] = (v,)
    return parts.path, frozenset(q.items())


class VerifyFixtureHttp:
    """Serves the recorded CSV exports; a request must match a recorded URL exactly (path +
    query). `override` maps a set name to replacement bytes (tampering tests)."""

    def __init__(self, override: dict[str, bytes] | None = None):
        self.override = override or {}
        self.calls: list[str] = []
        self.routes = {_route(m["url"], None): name for name, m in VMANIFEST.items()}

    def get(self, url, params=None, headers=None, timeout=None):
        name = self.routes.get(_route(url, params))
        if name is None:
            raise AssertionError(f"no recorded ren verifier response for {url} {params}")
        self.calls.append(name)
        m = VMANIFEST[name]
        return HttpResult(status=m["status"], body=self.override.get(name, vbody(m["file"])),
                          url=m["url"])
