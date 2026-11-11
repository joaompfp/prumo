"""Recorded real World Bank API v2 payloads (tests/ingest/fixtures/worldbank/, fetched
2026-11-11; every file <= 200 KB, sha256-pinned by MANIFEST.json — the six intake pins
re-verified by the controller, the 19-indicator metadata sweep, the country metadata used to
derive publisher ISO3 codes, and three genuine publisher bulk CSV ZIP exports for the
independent verifier channel), plus an Http double that serves the JSON channel by
(indicator, geography-set, page).

Fixture set keys of the source channel (routed by WHAT the adapter asks for, not literal URL
string):
    ("NY.GDP.MKTP.CD", {"PT","ES","DE"}, page 1)  -> r5-multicountry-json.json  (198 rows)
    ("SP.POP.TOTL",    {"EU","GR","AT"}, page 1)  -> multi-eugrat-pop.json      (198 rows)
"""
import json
from functools import cache
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import yaml

from ingest.http import HttpResult
from ingest.models import SeriesSpec, SourceSpec

ROOT = Path(__file__).resolve().parents[2]
FIX = Path(__file__).resolve().parent / "fixtures" / "worldbank"
MANIFEST: dict = json.loads((FIX / "MANIFEST.json").read_text())
_BY_FILE: dict = {e["file"]: e for e in MANIFEST["files"]}

_Loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)

# (indicator, frozenset(registry geographies), page) -> fixture file for the source channel
JSON_SETS = {
    ("NY.GDP.MKTP.CD", frozenset({"PT", "ES", "DE"}), 1): "r5-multicountry-json.json",
    ("SP.POP.TOTL", frozenset({"EU", "GR", "AT"}), 1): "multi-eugrat-pop.json",
}

GDP_PTDES = ["worldbank.gdp_usd.PT", "worldbank.gdp_usd.ES", "worldbank.gdp_usd.DE"]
POP_EUGRAT = ["worldbank.population.EU", "worldbank.population.GR", "worldbank.population.AT"]


@cache
def registry_specs() -> dict[str, SeriesSpec]:
    """The real worldbank series of registry/core.yaml, keyed by id."""
    doc = yaml.load((ROOT / "registry" / "core.yaml").read_text(), Loader=_Loader)
    src = SourceSpec(name="worldbank", **doc["sources"]["worldbank"])
    return {row["id"]: SeriesSpec(source=src, **{k: v for k, v in row.items() if k != "source"})
            for row in doc["series"] if row["source"] == "worldbank"}


def specs_of(ids: list[str]) -> list[SeriesSpec]:
    return [registry_specs()[i] for i in ids]


def body(name: str) -> bytes:
    return (FIX / name).read_bytes()


def _final_url(e: dict) -> str:
    return e["url"]


class FixtureHttp:
    """Serves the recorded source-channel bodies; routing keys on (indicator code, the SET of
    registry geographies in the /country/<a;b;c>/ path segment, page), so the adapter's exact
    geography join order and base URL are its own choice but a missing/extra/wrong request
    fails the test. `page` comes from the query (absent = page 1)."""

    def __init__(self, override: dict[str, bytes] | None = None,
                 status: dict[tuple, int] | None = None):
        self.calls: list[tuple] = []
        self.override = override or {}
        self.status = status or {}

    def get(self, url, params=None, headers=None, timeout=None):
        parts = urlsplit(url)
        seg = parts.path.split("/")
        # /v2/country/<geos>/indicator/<code>
        if len(seg) != 6 or seg[1] != "v2" or seg[2] != "country" or seg[4] != "indicator":
            raise AssertionError(f"not a worldbank data URL: {url}")
        geos = frozenset(seg[3].split(";"))
        code = seg[5]
        q = parse_qs(parts.query)
        p = dict(params or {})
        page = int(p.get("page") or (q.get("page", ["1"])[0]))
        key = (code, geos, page)
        if key not in JSON_SETS:
            raise AssertionError(f"no recorded worldbank response for {key} ({url} {params})")
        self.calls.append(key)
        e = _BY_FILE[JSON_SETS[key]]
        return HttpResult(status=int(self.status.get(key, e["status"])),
                          body=self.override.get(JSON_SETS[key], body(e["file"])),
                          url=e["url"])
