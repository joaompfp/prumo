"""Recorded real REN DataHub payloads (tests/ingest/fixtures/ren/, fetched 2026-11-11 from the
live servicebus JSON API with a throttled polite client; byte-identical copies of the Task 12
discovery archive whose MANIFEST.json records every request URL, HTTP status and sha256), plus
an Http double that serves them by request, like tests/ingest/bportugal_fixtures.py."""
import json
from functools import cache
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import yaml

from ingest.http import HttpResult
from ingest.models import SeriesSpec, SourceSpec

ROOT = Path(__file__).resolve().parents[2]
FIX = Path(__file__).resolve().parent / "fixtures" / "ren"
MANIFEST: dict = json.loads((FIX / "MANIFEST.json").read_text())

_Loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


@cache
def registry_specs() -> dict[str, SeriesSpec]:
    """The real ren series of registry/core.yaml, keyed by id."""
    doc = yaml.load((ROOT / "registry" / "core.yaml").read_text(), Loader=_Loader)
    src = SourceSpec(name="ren", **doc["sources"]["ren"])
    return {row["id"]: SeriesSpec(source=src, **{k: v for k, v in row.items() if k != "source"})
            for row in doc["series"] if row["source"] == "ren"}


def all_specs() -> list[SeriesSpec]:
    return [registry_specs()[sid] for sid in sorted(registry_specs())]


def balance_specs() -> list[SeriesSpec]:
    return [s for s in all_specs()
            if (s.native_code or "").startswith("ElectricityConsumptionSupplyMonthly:")]


def body(name: str) -> bytes:
    return (FIX / name).read_bytes()


def response_of(set_name: str) -> tuple[str, dict, int, bytes]:
    """(url, params, status, body) of a recorded set of the source channel."""
    m = MANIFEST["sets"][set_name]
    return m["url"], m.get("params") or {}, m["status"], body(m["file"])


def _route(url: str, params: dict | None) -> tuple[str, frozenset]:
    parts = urlsplit(url)
    q = {k: tuple(v) for k, v in parse_qs(parts.query).items()}
    for k, v in (params or {}).items():
        q[k] = (v,)
    return parts.path, frozenset(q.items())


class FixtureHttp:
    """Serves the recorded source-channel bodies; a request must match a recorded URL exactly
    (path + query), so a change in what the adapter asks for fails the test."""

    def __init__(self):
        self.calls: list[str] = []
        routes = {}
        for name, m in MANIFEST["sets"].items():
            if m["status"] == 200:
                routes[_route(m["url"], None)] = name
        self.routes = routes

    def get(self, url, params=None, headers=None, timeout=None):
        name = self.routes.get(_route(url, params))
        if name is None:
            raise AssertionError(f"no recorded ren response for {url} {params}")
        self.calls.append(name)
        m = MANIFEST["sets"][name]
        return HttpResult(status=m["status"], body=body(m["file"]), url=m["url"])
