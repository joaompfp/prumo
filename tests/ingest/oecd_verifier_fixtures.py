"""Recorded real OECD csvfilewithlabels SDMX-CSV payloads (tests/ingest/fixtures/oecd/verify/,
fetched 2026-11-12 by Task 15 discovery from f3nix, sha256-pinned by MANIFEST.json and
byte-identical to docs/superpowers/handoff/evidence/task-15-oecd/discovery/ items 2,4,6,8,10,12
whose discovery manifest sha256 is pinned there), plus the verifier-channel Http double and the
independence-guard entrypoint.

Fixture set keys of the VERIFIER channel (labelled CSV), by registry native_code:
    OECD.SDD.STES,DSD_STES@DF_CLI/PRT.M.BCICP.IX._Z.AA.IX._Z.H     -> cli-csv.csv      (13 rows)
    OECD.SDD.STES,DSD_STES@DF_BTS/PRT.M.EM.PB.C.Y._Z.FT.N          -> bts-employment-csv.csv
    OECD.SDD.STES,DSD_STES@DF_BTS/PRT.M.OB.PB.C.Y._Z.C.N           -> bts-order_books-csv.csv
    OECD.SDD.STES,DSD_STES@DF_BTS/PRT.M.PR.PB.C.Y._Z.T.N           -> bts-production-csv.csv
    OECD.SDD.STES,DSD_STES@DF_BTS/PRT.M.SP.PB.C.Y._Z.FT.N          -> bts-selling_prices-csv.csv
    OECD.SDD.TPS,DSD_LFS@DF_IALFS_UNE_M/PRT.UNE_LF_M.PT_LF_SUB._Z.Y._T.Y_GE15._Z.M
                                                                   -> unemp-csv.csv  (12 rows)

CsvFixtureHttp routes by native_code and serves bytes ONLY for request windows bounded by the
archived row extent [startPeriod..endPeriod]: the publisher answers a bounded window with exactly
the rows inside it, so filtering ROWS (never labels/values) reproduces publisher semantics. A
full-extent request is served byte-identical to the pinned original (self-check in the tests).
Mutations for fail-closed tests are explicit `override[file]` bytes built IN-TEST; the originals
on disk are never altered, and no mutated byte string is ever presented as the pinned original.
"""
import csv
import io
import json
import re
from functools import cache
from pathlib import Path
from urllib.parse import urlencode, urlsplit, urlunsplit

from ingest.http import HttpResult
from tests.ingest.oecd_fixtures import registry_specs

FIX = Path(__file__).resolve().parent / "fixtures" / "oecd" / "verify"
MANIFEST: dict = json.loads((FIX / "MANIFEST.json").read_text())
_BY_FILE: dict = {e["file"]: e for e in MANIFEST["files"]}

# native_code -> fixture file for the csvfilewithlabels verifier channel
CSV_BY_NATIVE_CODE = {
    "OECD.SDD.STES,DSD_STES@DF_CLI/PRT.M.BCICP.IX._Z.AA.IX._Z.H": "cli-csv.csv",
    "OECD.SDD.STES,DSD_STES@DF_BTS/PRT.M.EM.PB.C.Y._Z.FT.N": "bts-employment-csv.csv",
    "OECD.SDD.STES,DSD_STES@DF_BTS/PRT.M.OB.PB.C.Y._Z.C.N": "bts-order_books-csv.csv",
    "OECD.SDD.STES,DSD_STES@DF_BTS/PRT.M.PR.PB.C.Y._Z.T.N": "bts-production-csv.csv",
    "OECD.SDD.STES,DSD_STES@DF_BTS/PRT.M.SP.PB.C.Y._Z.FT.N": "bts-selling_prices-csv.csv",
    "OECD.SDD.TPS,DSD_LFS@DF_IALFS_UNE_M/PRT.UNE_LF_M.PT_LF_SUB._Z.Y._T.Y_GE15._Z.M":
        "unemp-csv.csv",
}

_PERIOD = re.compile(r"[0-9]{4}-(0[1-9]|1[0-2])")


def body(name: str) -> bytes:
    return (FIX / name).read_bytes()


def entry(name: str) -> dict:
    return _BY_FILE[name]


@cache
def csv_values(name: str) -> dict[str, str]:
    """Test-only extractor: {period: exact OBS_VALUE token} of an archived original, located by
    header NAME (never column position) - expectations are re-derived from the pinned bytes, not
    hardcoded in tests."""
    rows = list(csv.reader(io.StringIO(body(name).decode("utf-8"), newline="")))
    hdr, data = rows[0], rows[1:]
    ip, iv = hdr.index("TIME_PERIOD"), hdr.index("OBS_VALUE")
    return {r[ip]: r[iv] for r in data if r}


@cache
def extent(name: str) -> tuple[str, str]:
    """(min, max) row period of an archived original body."""
    periods = sorted(csv_values(name))
    return periods[0], periods[-1]


def _windowed(name: str, start: str, end: str) -> bytes:
    """The archived original restricted to [start..end] by dropping whole ROWS on the TIME_PERIOD
    cell (publisher window semantics); header, row order and every kept byte are original. Full
    extent returns the pinned bytes unchanged. Reviewed bodies are unquoted; anything else fails
    the test build rather than silently mis-slicing a quoted field."""
    raw = body(name)
    lo, hi = extent(name)
    if not (_PERIOD.fullmatch(start) and _PERIOD.fullmatch(end)) or not (lo <= start <= end <= hi):
        raise AssertionError(f"request window {start}..{end} not bounded by the archived "
                             f"extent {lo}..{hi} of {name}")
    text = raw.decode("utf-8")
    if '"' in text:
        raise AssertionError(f"{name}: the window filter only supports the reviewed unquoted "
                             "publisher bodies")
    lines = text.split("\r\n")
    if lines and lines[-1] == "":
        lines.pop()
    header, data = lines[0], lines[1:]
    ix = header.split(",").index("TIME_PERIOD")
    kept = [ln for ln in data if start <= ln.split(",")[ix] <= end]
    if (start, end) == (lo, hi) and len(kept) != len(data):
        raise AssertionError(f"{name}: full-extent request dropped rows (row periods outside "
                             f"the archived extent?)")
    return ("\r\n".join([header, *kept]) + "\r\n").encode("utf-8")


class CsvFixtureHttp:
    """Serves the recorded csvfilewithlabels bodies keyed by the requested URL's native_code.
    Params must be exactly the reviewed request shape (format=csvfilewithlabels,
    dimensionAtObservation=AllDimensions, canonical startPeriod/endPeriod bounded by the archived
    extent); anything else fails the test. `override[file]` serves in-test mutation bytes,
    `status[nc]` forces an HTTP status. `calls` records (native_code, params, headers)."""

    def __init__(self, override: dict[str, bytes] | None = None,
                 status: dict[str, int] | None = None):
        self.calls: list[tuple] = []
        self.override = override or {}
        self.status = status or {}

    def get(self, url, params=None, headers=None, timeout=None):
        parts = urlsplit(url)
        seg = parts.path.split("/")
        if len(seg) != 6 or seg[1:4] != ["public", "rest", "data"]:
            raise AssertionError(f"not an oecd data URL: {url}")
        nc = f"{seg[4]}/{seg[5]}"
        if nc not in CSV_BY_NATIVE_CODE:
            raise AssertionError(f"no recorded oecd verifier response for {nc} ({url} {params})")
        p = dict(params or {})
        self.calls.append((nc, dict(p), dict(headers or {})))
        fixed = {k: p.pop(k, None) for k in ("format", "dimensionAtObservation")}
        if fixed != {"format": "csvfilewithlabels", "dimensionAtObservation": "AllDimensions"}:
            raise AssertionError(f"not the reviewed csvfilewithlabels request shape: {params}")
        if set(p) != {"startPeriod", "endPeriod"}:
            raise AssertionError(f"the verifier requests an explicit bounded window: {params}")
        file = CSV_BY_NATIVE_CODE[nc]
        served = self.override.get(file) or _windowed(file, p["startPeriod"], p["endPeriod"])
        final = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(params or {}), ""))
        return HttpResult(status=int(self.status.get(nc, entry(file)["status"])),
                          body=served, url=final)


def run():
    """Independence-guard entrypoint (subprocess with ingest.sources.* and ingest.flags blocked):
    the real OecdVerifier over the recorded CSV bodies; every expected token is re-derived from
    the archived bytes via the test extractor. Imports nothing collector-side."""
    from ingest.verifiers import BlindItem
    from ingest.verifiers.oecd import OecdVerifier

    pins = [("oecd.cli.PT", "2026-05"), ("oecd.employment.PT", "2025-12"),
            ("oecd.order_books.PT", "2026-08"), ("oecd.production.PT", "2026-01"),
            ("oecd.selling_prices.PT", "2026-10"), ("oecd.unemp_m.PT", "2026-03")]
    specs = registry_specs()
    items = []
    for sid, period in pins:
        lo, hi = extent(CSV_BY_NATIVE_CODE[specs[sid].native_code])
        items += [BlindItem(sid, lo, specs[sid]), BlindItem(sid, period, specs[sid]),
                  BlindItem(sid, hi, specs[sid])]  # lo..hi -> full-extent request per series
    http = CsvFixtureHttp()
    results = OecdVerifier().check(items, http)
    assert len(http.calls) == 6  # one bounded CSV request per distinct series
    for item, r in zip(items, results):
        assert (r.series_id, r.period) == (item.series_id, item.period)
        assert r.observed_text == csv_values(CSV_BY_NATIVE_CODE[item.spec.native_code])[item.period]
        assert r.observed_unit == item.spec.unit and r.observed_decimal == "."
        assert r.observed_flag == "normal" and r.evidence and r.evidence_url
