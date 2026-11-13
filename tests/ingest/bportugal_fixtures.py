"""Recorded real BPstat (Banco de Portugal) payloads (tests/ingest/fixtures/bportugal/,
fetched 2026-11-11 with the production RequestsHttp, <=1 req/s, explicit 50 s timeout;
MANIFEST.json records each set's request URL, series, sha256 and provenance) and an Http double
that serves them by URL, like tests/ingest/ine_fixtures.py."""
import json
from functools import cache
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import yaml

from ingest.http import HttpResult
from ingest.models import SeriesSpec, SourceSpec

ROOT = Path(__file__).resolve().parents[2]
FIX = Path(__file__).resolve().parent / "fixtures" / "bportugal"
MANIFEST: dict = json.loads((FIX / "MANIFEST.json").read_text())
SETS = ("euribor", "yields", "credit", "deposits", "eurusd")

_Loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


@cache
def registry_specs() -> dict[str, SeriesSpec]:
    """The real bportugal series of registry/core.yaml, keyed by id."""
    doc = yaml.load((ROOT / "registry" / "core.yaml").read_text(), Loader=_Loader)
    src = SourceSpec(name="bportugal", **doc["sources"]["bportugal"])
    return {row["id"]: SeriesSpec(source=src, **{k: v for k, v in row.items() if k != "source"})
            for row in doc["series"] if row["source"] == "bportugal"}


_SERIES_SET = {  # native bpstat series id -> the fixture set that carries it
    int(sid): name
    for name, m in MANIFEST["sets"].items() for sid in m["series_ids"]}


def set_of(native_id: int) -> str:
    return _SERIES_SET[native_id]


def specs_of(*sets: str) -> list[SeriesSpec]:
    """Real registry specs of the series carried by the given fixture sets, id-sorted."""
    reg = registry_specs()
    out = []
    for name in sets:
        ids = set(MANIFEST["sets"][name]["series_ids"])
        out += [spec for key, spec in reg.items()
                if (spec.native_code or "").split(":")[0] in ids]
    return sorted(out, key=lambda s: s.id)


def all_specs() -> list[SeriesSpec]:
    return specs_of(*SETS)


def body(name: str) -> bytes:
    return (FIX / name).read_bytes()


def _route(url: str, params: dict | None) -> tuple[str, frozenset]:
    parts = urlsplit(url)
    q = {k: tuple(v) for k, v in parse_qs(parts.query).items()}
    for k, v in (params or {}).items():
        q[k] = (v,)
    return parts.path, frozenset(q.items())


class FixtureHttp:
    """Serves the recorded bodies; a request must match a recorded URL exactly (path + query
    set), so a change in what the adapter asks for fails the test. `override` maps a set name
    to replacement bytes (tampering tests)."""

    def __init__(self, override: dict[str, bytes] | None = None):
        self.override = override or {}
        self.calls: list[str] = []
        self.timeouts: list[float | None] = []
        self.routes = {_route(m["url"], None): name for name, m in MANIFEST["sets"].items()}

    def get(self, url, params=None, headers=None, timeout=None):
        name = self.routes.get(_route(url, params))
        if name is None:
            raise AssertionError(f"no recorded bportugal response for {url} {params}")
        self.calls.append(name)
        self.timeouts.append(timeout)
        m = MANIFEST["sets"][name]
        return HttpResult(status=200, body=self.override.get(name, body(m["file"])), url=m["url"])
