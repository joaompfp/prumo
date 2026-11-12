"""Recorded real OECD SDMX-JSON data 2.0 payloads (tests/ingest/fixtures/oecd/, fetched
2026-11-12 by Task 15 discovery from f3nix; every file <= 200 KB, sha256-pinned by
MANIFEST.json and byte-identical to docs/superpowers/handoff/evidence/task-15-oecd/discovery/
items 1,3,5,7,9,11 whose discovery manifest sha256 is pinned there), plus an Http double that
serves the collector channel by native_code.

Fixture set keys of the source channel (routed by WHAT the adapter asks for — the registry
native_code '<agency>,<dataflow>/<key>' — not literal URL string):
    OECD.SDD.STES,DSD_STES@DF_CLI/PRT.M.BCICP.IX._Z.AA.IX._Z.H     -> cli-json.json      (13 obs)
    OECD.SDD.STES,DSD_STES@DF_BTS/PRT.M.EM.PB.C.Y._Z.FT.N          -> bts-employment-json.json
    OECD.SDD.STES,DSD_STES@DF_BTS/PRT.M.OB.PB.C.Y._Z.C.N           -> bts-order_books-json.json
    OECD.SDD.STES,DSD_STES@DF_BTS/PRT.M.PR.PB.C.Y._Z.T.N           -> bts-production-json.json
    OECD.SDD.STES,DSD_STES@DF_BTS/PRT.M.SP.PB.C.Y._Z.FT.N          -> bts-selling_prices-json.json
    OECD.SDD.TPS,DSD_LFS@DF_IALFS_UNE_M/PRT.UNE_LF_M.PT_LF_SUB._Z.Y._T.Y_GE15._Z.M
                                                                   -> unemp-json.json (12 obs)
All six payloads are bounded 2025-10 onwards (77 observations total), every TIME_PERIOD values
array is UNSORTED, and values embed trailing-zero tokens (e.g. '-6.0', '12.0', '6.0') that the
CSV verifier channel (Task 15 Part B) formats as '-6', '12', '6'.
"""
import json
from functools import cache
from pathlib import Path
from urllib.parse import urlencode, urlsplit, urlunsplit

import yaml

from ingest.http import HttpResult
from ingest.models import SeriesSpec, SourceSpec

ROOT = Path(__file__).resolve().parents[2]
FIX = Path(__file__).resolve().parent / "fixtures" / "oecd"
MANIFEST: dict = json.loads((FIX / "MANIFEST.json").read_text())
_BY_FILE: dict = {e["file"]: e for e in MANIFEST["files"]}

_Loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)

# native_code -> fixture file for the SDMX-JSON collector channel
JSON_BY_NATIVE_CODE = {
    "OECD.SDD.STES,DSD_STES@DF_CLI/PRT.M.BCICP.IX._Z.AA.IX._Z.H": "cli-json.json",
    "OECD.SDD.STES,DSD_STES@DF_BTS/PRT.M.EM.PB.C.Y._Z.FT.N": "bts-employment-json.json",
    "OECD.SDD.STES,DSD_STES@DF_BTS/PRT.M.OB.PB.C.Y._Z.C.N": "bts-order_books-json.json",
    "OECD.SDD.STES,DSD_STES@DF_BTS/PRT.M.PR.PB.C.Y._Z.T.N": "bts-production-json.json",
    "OECD.SDD.STES,DSD_STES@DF_BTS/PRT.M.SP.PB.C.Y._Z.FT.N": "bts-selling_prices-json.json",
    "OECD.SDD.TPS,DSD_LFS@DF_IALFS_UNE_M/PRT.UNE_LF_M.PT_LF_SUB._Z.Y._T.Y_GE15._Z.M":
        "unemp-json.json",
}

ALL_SIX = ["oecd.cli.PT", "oecd.employment.PT", "oecd.order_books.PT", "oecd.production.PT",
           "oecd.selling_prices.PT", "oecd.unemp_m.PT"]


@cache
def registry_specs() -> dict[str, SeriesSpec]:
    """The real oecd series of registry/core.yaml, keyed by id."""
    doc = yaml.load((ROOT / "registry" / "core.yaml").read_text(), Loader=_Loader)
    src = SourceSpec(name="oecd", **doc["sources"]["oecd"])
    return {row["id"]: SeriesSpec(source=src, **{k: v for k, v in row.items() if k != "source"})
            for row in doc["series"] if row["source"] == "oecd"}


def specs_of(ids: list[str]) -> list[SeriesSpec]:
    return [registry_specs()[i] for i in ids]


def body(name: str) -> bytes:
    return (FIX / name).read_bytes()


class FixtureHttp:
    """Serves the recorded collector bodies; routing keys on the registry native_code of the
    requested URL path, so the adapter's exact base URL is its own choice but a missing/extra/
    wrong request fails the test. Records every call as (native_code, params, headers) so tests
    can assert request count, the SDMX-JSON Accept header and the window params. The returned
    final URL is the request URL plus the adapter's encoded params — what a real client produces
    — and for the recorded 2025-10 window that exactly equals the manifest's archived URL."""

    def __init__(self, status: dict[str, int] | None = None,
                 override: dict[str, bytes] | None = None):
        self.calls: list[tuple] = []
        self.status = status or {}
        self.override = override or {}

    def get(self, url, params=None, headers=None, timeout=None):
        parts = urlsplit(url)
        seg = parts.path.split("/")
        # /public/rest/data/<agency>,<dataflow>/<key>
        if len(seg) != 6 or seg[1:4] != ["public", "rest", "data"]:
            raise AssertionError(f"not an oecd data URL: {url}")
        nc = f"{seg[4]}/{seg[5]}"
        if nc not in JSON_BY_NATIVE_CODE:
            raise AssertionError(f"no recorded oecd response for {nc} ({url} {params})")
        p = dict(params or {})
        self.calls.append((nc, p, dict(headers or {})))
        file = JSON_BY_NATIVE_CODE[nc]
        final = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(p), ""))
        return HttpResult(status=int(self.status.get(nc, _BY_FILE[file]["status"])),
                          body=self.override.get(file, body(file)),
                          url=final)
