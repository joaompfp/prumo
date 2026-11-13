"""Recorded real FRED payloads (tests/ingest/fixtures/fred/, fetched 2026-11-12, byte-identical
copies of the controller's Task-14 preflight originals, sha256-pinned by MANIFEST.json; api_key
redacted from every recorded url/params - the credential is not publisher data), plus an Http
double that serves the recorded bodies by endpoint and series_id.

Fixture set keys of the source channel:
    /fred/series             + series_id <CODE> -> meta-<CODE>.json  (series metadata)
    /fred/series/observations + series_id <CODE> -> obs-<CODE>.json   (full history, 561 cells:
                                                                        417 values + 144 '.'
                                                                        missing pre-1992)

Test-only helpers (NEVER production code): `table_values` extracts the DATE/VALUE rows of the
server-rendered data-table-<CODE>.html so source tests can cross-check API tokens against the
independent channel; `SENTINEL_KEY` is a fake credential that must never appear in archived
artifacts.
"""
import json
from functools import cache
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import yaml

from ingest.http import HttpResult
from ingest.models import SeriesSpec, SourceSpec

ROOT = Path(__file__).resolve().parents[2]
FIX = Path(__file__).resolve().parent / "fixtures" / "fred"
MANIFEST: dict = json.loads((FIX / "MANIFEST.json").read_text())
_BY_FILE: dict = {e["file"]: e for e in MANIFEST["files"]}

_Loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)

# A test-only fake credential. It is deliberately ugly so a leak is easy to spot; it is never
# a real key and never reads one.
SENTINEL_KEY = "test-only-SENTINEL-api-key-0000"

# code -> registry id is asserted from the live registry, not duplicated here.


@cache
def registry_specs() -> dict[str, SeriesSpec]:
    """The real fred series of registry/core.yaml, keyed by id."""
    doc = yaml.load((ROOT / "registry" / "core.yaml").read_text(), Loader=_Loader)
    src = SourceSpec(name="fred", **doc["sources"]["fred"])
    return {row["id"]: SeriesSpec(source=src, **{k: v for k, v in row.items() if k != "source"})
            for row in doc["series"] if row["source"] == "fred"}


def active_specs() -> list[SeriesSpec]:
    return [registry_specs()[sid] for sid in sorted(registry_specs())
            if registry_specs()[sid].active]


def inactive_specs() -> list[SeriesSpec]:
    return [registry_specs()[sid] for sid in sorted(registry_specs())
            if not registry_specs()[sid].active]


def body(name: str) -> bytes:
    return (FIX / name).read_bytes()


def entry(name: str) -> dict:
    return _BY_FILE[name]


def _public_params(params: dict | None) -> frozenset:
    p = dict(params or {})
    assert p.pop("api_key", None), f"FRED request must carry an api_key on the wire: {params}"
    return frozenset(p.items())


class FixtureHttp:
    """Serves the recorded source-channel bodies by (endpoint, series_id). Every wire request
    MUST carry a non-empty `api_key` param (FRED query auth); the recorded final URL and the
    manifest params are key-free, so any request/response secret drift fails the test. An
    `override[<file>]` replaces a body (tamper tests, always labeled in-test)."""

    def __init__(self, override: dict[str, bytes] | None = None,
                 status: dict[tuple, int] | None = None):
        self.calls: list[tuple[str, str]] = []
        self.override = override or {}
        self.status = status or {}

    def get(self, url, params=None, headers=None, timeout=None):
        public = _public_params(params)
        p = dict(public)
        path = urlsplit(url).path
        if path == "/fred/series":
            kind = "meta"
        elif path == "/fred/series/observations":
            kind = "obs"
        else:
            raise AssertionError(f"not a fred API URL: {url}")
        code = p.get("series_id")
        if not isinstance(code, str):
            raise AssertionError(f"fred request without series_id: {url} {params}")
        if kind == "obs" and p.get("limit") != "100000":
            raise AssertionError(f"fred observations request without limit=100000: {params}")
        if p.get("file_type") != "json":
            raise AssertionError(f"fred request without file_type=json: {params}")
        extra = set(p) - ({"series_id", "file_type"} if kind == "meta"
                          else {"series_id", "file_type", "limit", "offset"})
        if extra:
            raise AssertionError(f"fred request with unreviewed params {sorted(extra)}: {params}")
        file = f"{kind}-{code}.json"
        if file not in _BY_FILE:
            raise AssertionError(f"no recorded fred response for {kind} {code}")
        self.calls.append((kind, code))
        e = _BY_FILE[file]
        status = self.status.get((kind, code))
        return HttpResult(status=int(e["status"]) if status is None else status,
                          body=self.override.get(file, body(file)), url=e["url"])


class _TableParser(HTMLParser):
    """Extracts (DATE, VALUE) rows of the <table id="data-table-observations"> body of the
    recorded server-rendered data page. Test-only: the Part-B verifier owns its own parser."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows: list[tuple[str, str]] = []
        self._in_table = False
        self._depth = 0
        self._cell: list[str] | None = None
        self._row: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            if a.get("id") == "data-table-observations":
                self._in_table, self._depth = True, 1
            elif self._in_table:
                self._depth += 1
        elif self._in_table:
            if tag == "tr":
                self._row = []
            elif tag in ("th", "td"):
                self._cell = []

    def handle_endtag(self, tag):
        if not self._in_table:
            return
        if tag == "table":
            self._depth -= 1
            if self._depth <= 0:
                self._in_table = False
        elif tag in ("th", "td") and self._cell is not None:
            self._row.append("".join(self._cell).strip())
            self._cell = None
        elif tag == "tr" and len(self._row) == 2:
            self.rows.append((self._row[0], self._row[1]))

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def table_values(code: str) -> dict[str, str]:
    """DATE -> exact VALUE token of the recorded data-table HTML (full precision, incl. the
    publisher's trailing-zero padding; compare with Decimal, never float)."""
    p = _TableParser()
    p.feed(body(f"table-{code}.html").decode("utf-8"))
    rows = [(d, v) for d, v in p.rows if len(d) == 10]
    if len(rows) != len(set(d for d, _ in rows)):
        raise AssertionError(f"duplicate dates in recorded table-{code}.html")
    return dict(rows)
