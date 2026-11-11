"""Recorded real Eurostat payloads (tests/ingest/fixtures/eurostat, fetched 2026-11-11 from the
live APIs with RequestsHttp; MANIFEST.json lists each set's series and the exact request URLs)
and an Http double that serves them by URL.

Deliberately imports nothing from the collector side (no ingest.sources.*, no ingest.registry,
which pulls in ingest.db): the verifier's subprocess independence test uses it too.
"""
import json
from functools import cache
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import yaml

from ingest.http import HttpResult
from ingest.models import SeriesSpec, SourceSpec

ROOT = Path(__file__).resolve().parents[2]
FIX = Path(__file__).resolve().parent / "fixtures" / "eurostat"
MANIFEST: dict = json.loads((FIX / "MANIFEST.json").read_text())


@cache
def registry_specs() -> dict[str, SeriesSpec]:
    """The real Eurostat series of registry/core.yaml, keyed by id (built without
    ingest.registry so the independence subprocess loads no DB code)."""
    doc = yaml.load((ROOT / "registry" / "core.yaml").read_text(), Loader=_Loader)
    src = SourceSpec(name="eurostat", **doc["sources"]["eurostat"])
    return {row["id"]: SeriesSpec(source=src, **{k: v for k, v in row.items() if k != "source"})
            for row in doc["series"] if row["source"] == "eurostat"}


_Loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


def specs_of(*sets: str) -> list[SeriesSpec]:
    reg = registry_specs()
    return [reg[sid] for name in sets for sid in MANIFEST[name]["series"]]


def body(name: str) -> bytes:
    return (FIX / name).read_bytes()


class FixtureHttp:
    """Serves the recorded bodies. A request must match a recorded URL exactly (path and query
    parameters), so a change in what the adapter/verifier asks for fails the test.
    `override` maps a recorded URL to replacement bytes (tampering tests)."""

    def __init__(self, override: dict[str, bytes] | None = None):
        self.override = override or {}
        self.calls: list[str] = []
        self.routes: dict[tuple[str, frozenset], tuple[str, str]] = {}
        for name, m in MANIFEST.items():
            for url, suffix in ((m["json_url"], ".json"), (m["tsv_url"], ".tsv")):
                self.routes[_route(url, None)] = (url, name + suffix)

    def get(self, url, params=None, headers=None):
        key = _route(url, params)
        if key not in self.routes:
            raise AssertionError(f"no recorded response for {url} {params}")
        recorded, fname = self.routes[key]
        self.calls.append(recorded)
        return HttpResult(status=200, body=self.override.get(recorded, body(fname)), url=recorded)


def _route(url: str, params: dict | None) -> tuple[str, frozenset]:
    parts = urlsplit(url)
    q = {k: tuple(v) for k, v in parse_qs(parts.query).items()}
    for k, v in (params or {}).items():
        q[k] = tuple(v) if isinstance(v, list) else (v,)
    return parts.path, frozenset(q.items())
