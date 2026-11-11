"""Recorded real INE payloads (tests/ingest/fixtures/ine, fetched 2026-11-11 from the live
pindica.jsp API with RequestsHttp; MANIFEST.json lists each set's series, the exact request URL
and the file) and an Http double that serves them by URL."""
import json
from functools import cache
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import yaml

from ingest.http import HttpResult
from ingest.models import SeriesSpec, SourceSpec

ROOT = Path(__file__).resolve().parents[2]
FIX = Path(__file__).resolve().parent / "fixtures" / "ine"
MANIFEST: dict = json.loads((FIX / "MANIFEST.json").read_text())

_Loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


@cache
def registry_specs() -> dict[str, SeriesSpec]:
    """The real INE series of registry/core.yaml, keyed by id."""
    doc = yaml.load((ROOT / "registry" / "core.yaml").read_text(), Loader=_Loader)
    src = SourceSpec(name="ine", **doc["sources"]["ine"])
    return {row["id"]: SeriesSpec(source=src, **{k: v for k, v in row.items() if k != "source"})
            for row in doc["series"] if row["source"] == "ine"}


def specs_of(*sets: str) -> list[SeriesSpec]:
    reg = registry_specs()
    return [reg[sid] for name in sets for sid in MANIFEST[name]["series"]]


def body(name: str) -> bytes:
    return (FIX / name).read_bytes()


def _route(url: str, params: dict | None) -> tuple[str, frozenset]:
    parts = urlsplit(url)
    q = {k: tuple(v) for k, v in parse_qs(parts.query).items()}
    for k, v in (params or {}).items():
        q[k] = (v,)
    return parts.path, frozenset(q.items())


class FixtureHttp:
    """Serves the recorded bodies; a request must match a recorded URL exactly (path + query),
    so a change in what the adapter asks for fails the test. `override` maps a set name to
    replacement bytes (tampering tests)."""

    def __init__(self, override: dict[str, bytes] | None = None):
        self.override = override or {}
        self.calls: list[str] = []
        self.routes = {_route(m["url"], None): name for name, m in MANIFEST.items()}

    def get(self, url, params=None, headers=None):
        name = self.routes.get(_route(url, params))
        if name is None:
            raise AssertionError(f"no recorded INE response for {url} {params}")
        self.calls.append(name)
        m = MANIFEST[name]
        return HttpResult(status=200, body=self.override.get(name, body(m["file"])), url=m["url"])
