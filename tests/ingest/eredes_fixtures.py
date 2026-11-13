"""Recorded genuine E-REDES portal payloads (tests/ingest/fixtures/eredes/, fetched 2026-11-12
within the brief's bounded network budget - see MANIFEST.json) and an Http double that serves
them by exact request, like tests/ingest/ren_fixtures.py. Synthetic mutations in tests are
labelled synthetic; fixture bytes themselves are never altered.
"""
import json
from functools import cache
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import yaml

from ingest.http import HttpResult
from ingest.models import SeriesSpec, SourceSpec

ROOT = Path(__file__).resolve().parents[2]
FIX = Path(__file__).resolve().parent / "fixtures" / "eredes"
MANIFEST: dict = json.loads((FIX / "MANIFEST.json").read_text())

_Loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)

# The genuine window the fixtures cover: 2026-11-10 (UTC day, 96 quarter-hour records).
WINDOW = ("2026-11-10T00:00:00+00:00", "2026-11-11T00:00:00+00:00")
# The genuine WEST-summer window: 2026-04-01 (UTC day; the dia/mes/ano/date/time echo is LISBON
# LOCAL wall time = UTC+1, so the 23:45 UTC record carries date 2026-04-02 and time 00:45).
SUMMER_WINDOW = ("2026-04-01T00:00:00+00:00", "2026-04-02T00:00:00+00:00")


@cache
def registry_specs() -> dict[str, SeriesSpec]:
    """The real eredes series of registry/core.yaml, keyed by id."""
    doc = yaml.load((ROOT / "registry" / "core.yaml").read_text(), Loader=_Loader)
    src = SourceSpec(name="eredes", **doc["sources"]["eredes"])
    return {row["id"]: SeriesSpec(source=src, **{k: v for k, v in row.items() if k != "source"})
            for row in doc["series"] if row["source"] == "eredes"}


def all_specs() -> list[SeriesSpec]:
    return [registry_specs()[sid] for sid in sorted(registry_specs())]


def body(name: str) -> bytes:
    return (FIX / MANIFEST["sets"][name]["file"]).read_bytes()


def _route(url: str, params: dict | None) -> tuple[str, frozenset]:
    parts = urlsplit(url)
    q = {k: tuple(v) for k, v in parse_qs(parts.query).items()}
    for k, v in (params or {}).items():
        q[k] = (str(v),)
    return parts.path, frozenset(q.items())


def _norm(meta: dict) -> tuple[str, frozenset]:
    return _route(meta["url"], meta["params"])


class FixtureHttp:
    """Serves the recorded source-channel bodies; a request must match a recorded URL exactly
    (path + query params), so a change in what the adapter asks for fails the test.
    `override` maps a set name to replacement bytes (labelled synthetic tampering)."""

    def __init__(self, override: dict[str, bytes] | None = None):
        self.override = override or {}
        self.calls: list[str] = []
        self.routes = {_norm(m): name for name, m in MANIFEST["sets"].items()
                       if not name.endswith("_csv")}  # CSV sets belong to the verifier channel
        self.urls = {name: m["url"] for name, m in MANIFEST["sets"].items()}

    def get(self, url, params=None, headers=None, timeout=None):
        name = self.routes.get(_route(url, params))
        if name is None:
            raise AssertionError(f"no recorded eredes response for {url} {params}")
        self.calls.append(name)
        m = MANIFEST["sets"][name]
        return HttpResult(status=m["status"], body=self.override.get(name, body(name)),
                          url=m["url"])
