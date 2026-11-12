"""Independent verifier for FRED (Federal Reserve Bank of St. Louis), spec 6b:

    collector:  FRED JSON API on api.stlouisfed.org, api_key query auth
                (/fred/series + /fred/series/observations; values are JSON strings, '.' is
                the publisher's missing marker)
    verifier:   the server-rendered data-table page of the PUBLIC site, keyless:
                https://fred.stlouisfed.org/data/<native_code>   (text/html; Task 14
                preflight 2026-11-12 recorded all 12 series, sha256-pinned originals in
                tests/ingest/fixtures/fred/table-<CODE>.html)

A different host family, endpoint and format, owned by FRED's publication UI. ONE page carries
BOTH surfaces an item's decision needs, so one fetch per series per check() call suffices:

1.  the metadata table (`<table aria-label="metadata - <Title>" name="<Title>">`): rows Title,
    Series ID, Source, Release, Seasonal Adjustment, Frequency, Units, Date Range,
    Last Updated, Notes. asserted fail-closed: exactly one such table, the aria-label/name/Title
    row triple agrees, Series ID == the requested native code, Source is 'International Monetary
    Fund' and Release the IMF Primary Commodity Prices release (the reviewed WORLD-concept
    series: Title starts 'Global price of '), Frequency 'Monthly' == spec M, Seasonal Adjustment
    'Not Seasonally Adjusted' == spec NSA, and the Units label (observed_unit) byte-matches the
    registry — asserted, never copied FROM the registry.
2.  the observations table (`<table id="data-table-observations" aria-labelledby=
    "data-table-title">`): header exactly DATE/VALUE (a third column would be unreviewed
    status drift), body rows `<th scope="row">YYYY-MM-01</th><td>token</td>`. Month-first real
    dates, strictly ascending, no duplicate periods, declared Date Range endpoints equal the
    first/last row dates. Cell tokens are preserved VERBATIM (no float, no rounding, no
    tolerance); the only reviewed missing marker is exactly '.', anything else raises.

Value equality is exact-Decimal in ingest.verify (Ruling AB), which absorbs the table's
trailing-zero padding against the API's trimmed tokens (preflight: all 417 x 12 cells match).
A requested period absent from the table (or a proved '.' cell) returns observed_text=None —
an honest 'not found', never an invented value. observed_flag is honestly None: this channel
has no per-observation status surface. Parsing is structural (html.parser); no regex scrapes
numbers out of the page. html.parser is subclassed WITHOUT defining __init__ or calling
super(): the verifier independence allowlist (Ruling S) forbids super()/dunder attribute use,
and HTMLParser's own constructor (convert_charrefs=True by default) runs normally.

EVIDENCE (Ruling R/G7): metadata and values come from the SAME response, so ItemResult.evidence
is one versioned JSON envelope (schema 'fred-table-evidence', version 1) bundling the exact
wire record: final URL, actual HTTP status and the full body base64-encoded — byte-for-byte
recoverable from the raw store with no HTTP, and readable again by `read_table_page`.
evidence_url is the page's final URL.

INDEPENDENCE: this module shares NO code with the collector (enforced by register_verifier's
static allowlist and by assert_verifier_independent's runtime subprocess). The tiny native-code
shape rule is DUPLICATED ON PURPOSE: if the two copies ever disagree, verification fails
loudly. Requests are paced by the injected Http client; the verifier adds no sleeping of its
own so recorded-fixture tests stay fast. The CSV export (fredgraph.csv) was REJECTED as a
channel (binary numeric tails differ on 10/12 series) and the JSON API is the collector's own
channel — neither is read here.

Registration: the Task 17 CLI calls register_verifier(FredVerifier()).
"""
import base64
import json
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser

from ingest.http import Http, HttpResult
from ingest.models import SeriesSpec
from ingest.verifiers import BlindItem, ItemResult

TABLE_URL = "https://fred.stlouisfed.org/data/"

EVIDENCE_SCHEMA = "fred-table-evidence"
EVIDENCE_VERSION = 1

_MISSING = "."  # FRED's missing-observation marker (the only one reviewed on this channel)

# DUPLICATES of the reviewed registry/metadata pairings, ON PURPOSE (see module docstring).
_FREQUENCY = {"Monthly": "M"}
_SEASONAL = {"Not Seasonally Adjusted": "NSA"}
_IMF_SOURCE = "International Monetary Fund"
_IMF_RELEASE = "Primary Commodity Prices (Not a Press Release)"
_WORLD_TITLE = "Global price of "
_META_KEYS = {"Title", "Series ID", "Source", "Release", "Seasonal Adjustment", "Frequency",
              "Units", "Date Range", "Last Updated", "Notes"}


def _native(code: str | None) -> str:
    """The registry native_code IS the FRED series id ('PALUMUSDM'). DUPLICATE of the
    collector's shape rule, ON PURPOSE: non-empty uppercase ASCII alphanumerics only."""
    if not code or not code.isascii() or not code.isalnum() or code != code.upper():
        raise ValueError(f"FRED native_code must be the uppercase series id, got {code!r}")
    return code


def _month_first(text: str) -> str:
    """A 'YYYY-MM-DD' FIRST-OF-MONTH date -> its canonical period 'YYYY-MM'; raises otherwise
    (malformed or mid-month dates are drift, never normalized silently)."""
    try:
        d = datetime.strptime(text, "%Y-%m-%d")
    except ValueError as e:
        raise ValueError(f"malformed date {text!r}") from e
    if d.day != 1 or d.strftime("%Y-%m-%d") != text:
        raise ValueError(f"non month-first date {text!r}")
    return text[:7]


def _numeric(token: str) -> str:
    """A plain ASCII decimal token, returned VERBATIM. Anything else — blank, unicode digits,
    separators, exponents, a new status marker — raises: the only reviewed missing marker on
    this channel is exactly '.', handled by the caller before this."""
    if not token or not token.isascii():
        raise ValueError(f"unreviewed VALUE cell {token!r} (not a plain ASCII decimal token)")
    digits = token[1:] if token[0] in "+-" else token
    parts = digits.split(".")
    if not any(parts) or len(parts) > 2 or any(not p.isdigit() for p in parts):
        raise ValueError(f"unreviewed VALUE cell {token!r} (grouping/exponents/markers are "
                         f"drift; the only reviewed missing marker is '.')")
    return token


@dataclass
class _Scan:
    """Mutable scanner state (attached to the parser by read_table_page right after
    construction — the class itself defines no __init__, see module docstring)."""
    cur: str | None = None       # 'meta' | 'obs' while inside a reviewed table
    foreign_tables: int = 0      # open non-reviewed (layout/chrome) tables; content ignored
    meta_tables: int = 0
    obs_tables: int = 0
    meta_name: str = ""          # name attribute of the metadata table
    h1_seen: bool = False
    h1_open: bool = False
    h1_parts: list = field(default_factory=list)
    h1: str | None = None        # text of the single <h1 id="data-table-title">
    rows: list = field(default_factory=list)  # (table ident, [(tag, scope, text), ...])
    row: list | None = None
    cell: list | None = None
    cell_tag: str = ""
    cell_scope: str = ""


class _PageParser(HTMLParser):
    """Structural scanner of the fixed /data/<CODE> template. Markup inside reviewed-table
    cells is rejected (never concatenated), nested tables inside reviewed tables are rejected,
    and a table left open at EOF is a truncation. Non-reviewed tables elsewhere on the page
    are ignored entirely — values come ONLY from the identified cells."""

    def handle_starttag(self, tag, attrs):
        st = self.st
        a = dict(attrs)
        if tag == "table":
            if st.cur is not None:
                raise ValueError("a <table> nested inside a reviewed table")
            label = a.get("aria-label") or ""
            if a.get("id") == "data-table-observations":
                st.cur, st.obs_tables = "obs", st.obs_tables + 1
                if a.get("aria-labelledby") != "data-table-title":
                    raise ValueError("observations table without "
                                     "aria-labelledby='data-table-title'")
            elif label.startswith("metadata - "):
                st.cur, st.meta_tables = "meta", st.meta_tables + 1
                name = a.get("name") or ""
                if not name or label != "metadata - " + name:
                    raise ValueError(f"metadata table aria-label {label!r} / name {name!r} "
                                     f"disagree")
                st.meta_name = name
            else:
                st.foreign_tables += 1
            return
        if st.cur is not None:
            if tag in ("thead", "tbody"):
                return
            if tag == "tr":
                if st.row is not None:
                    raise ValueError("<tr> nested inside a row")
                st.row = []
                return
            if tag in ("th", "td"):
                if st.row is None or st.cell is not None:
                    raise ValueError(f"<{tag}> outside a row (or a cell nested in a cell)")
                st.cell, st.cell_tag, st.cell_scope = [], tag, a.get("scope", "")
                return
            raise ValueError(f"unreviewed markup <{tag}> inside a reviewed table")
        if tag == "h1" and a.get("id") == "data-table-title":
            if st.h1_seen:
                raise ValueError("duplicate h1#data-table-title")
            st.h1_seen, st.h1_open, st.h1_parts = True, True, []

    def handle_endtag(self, tag):
        st = self.st
        if tag == "table":
            if st.cur is not None:
                if st.row is not None or st.cell is not None:
                    raise ValueError("</table> with an open row/cell (malformed table)")
                st.cur = None
            elif st.foreign_tables:
                st.foreign_tables -= 1
            return
        if st.cur is None:
            if tag == "h1" and st.h1_open:
                st.h1_open, st.h1 = False, "".join(st.h1_parts)
            return
        if tag in ("thead", "tbody"):
            return
        if tag in ("th", "td"):
            if st.cell is None or tag != st.cell_tag:
                raise ValueError(f"mismatched </{tag}> inside a reviewed table")
            st.row.append((st.cell_tag, st.cell_scope, "".join(st.cell)))
            st.cell = None
            return
        if tag == "tr":
            if st.row is None or st.cell is not None:
                raise ValueError("</tr> out of place (malformed table)")
            if not st.row:
                raise ValueError("empty <tr> in a reviewed table")
            st.rows.append((st.cur, st.row))
            st.row = None
            return
        raise ValueError(f"unreviewed </{tag}> inside a reviewed table")

    def handle_data(self, data):
        st = self.st
        if st.cell is not None:
            st.cell.append(data)
        elif st.h1_open:
            st.h1_parts.append(data)


def read_table_page(body: bytes, code: str, spec: SeriesSpec) -> tuple[str, dict[str, str]]:
    """The one /data/<code> page -> (observed_unit, {canonical period: exact VALUE token}).

    Every identity/shape assertion raises (fail-closed); nothing is echoed from the request.
    This same function is the OFFLINE replay path for archived evidence bytes (no HTTP)."""
    p = _PageParser()
    p.st = _Scan()
    p.feed(body.decode("utf-8"))
    p.close()
    if p.st.cur is not None or p.st.foreign_tables:
        raise ValueError("truncated page: a table is missing its closing tag")
    if p.st.meta_tables != 1:
        raise ValueError(f"{p.st.meta_tables} metadata tables (need exactly 1): FRED error "
                         f"page or a layout change")
    if p.st.obs_tables != 1:
        raise ValueError(f"{p.st.obs_tables} observations tables (need exactly 1): FRED "
                         f"error page or a layout change")

    meta: dict[str, str] = {}
    for ident, cells in p.st.rows:
        if ident != "meta":
            continue
        if len(cells) != 2 or cells[0][:2] != ("th", "row") or cells[1][0] != "td":
            raise ValueError(f"metadata row shape drift: {cells!r}")
        key, value = cells[0][2].strip(), cells[1][2].strip()
        if key in meta:
            raise ValueError(f"duplicate metadata row {key!r}")
        meta[key] = value
    if set(meta) != _META_KEYS:
        raise ValueError(f"unreviewed metadata rows {sorted(set(meta) ^ _META_KEYS)} (need "
                         f"exactly {sorted(_META_KEYS)})")
    if not meta["Title"] or meta["Title"] != p.st.meta_name:
        raise ValueError(f"metadata Title {meta['Title']!r} != table name {p.st.meta_name!r}")
    if p.st.h1 is None or p.st.h1.strip() != f"Table Data - {meta['Title']}":
        raise ValueError(f"page h1 {p.st.h1!r} is not 'Table Data - {meta['Title']}': the "
                         f"observations table is not labelled for this series page")
    if meta["Series ID"] != code:
        raise ValueError(f"page is for Series ID {meta['Series ID']!r}, asked {code!r}")
    if meta["Source"] != _IMF_SOURCE:
        raise ValueError(f"Source {meta['Source']!r} != {_IMF_SOURCE!r} (only the reviewed "
                         f"IMF series are supported)")
    if meta["Release"] != _IMF_RELEASE:
        raise ValueError(f"Release {meta['Release']!r} != {_IMF_RELEASE!r}")
    if not meta["Title"].startswith(_WORLD_TITLE):
        raise ValueError(f"Title {meta['Title']!r} is not a reviewed WORLD concept "
                         f"({_WORLD_TITLE}...)")
    freq = _FREQUENCY.get(meta["Frequency"])
    if freq is None:
        raise ValueError(f"unreviewed Frequency {meta['Frequency']!r}")
    if freq != spec.frequency:
        raise ValueError(f"{spec.id}: table Frequency {meta['Frequency']!r} ({freq}) != "
                         f"registry frequency {spec.frequency!r}")
    seas = _SEASONAL.get(meta["Seasonal Adjustment"])
    if seas is None:
        raise ValueError(f"unreviewed Seasonal Adjustment {meta['Seasonal Adjustment']!r}")
    if seas != spec.seasonal_adjustment:
        raise ValueError(f"{spec.id}: table Seasonal Adjustment "
                         f"{meta['Seasonal Adjustment']!r} ({seas}) != registry "
                         f"{spec.seasonal_adjustment!r}")
    unit = meta["Units"]
    if unit != spec.unit:
        raise ValueError(f"{spec.id}: table Units {unit!r} != registry unit {spec.unit!r}")
    if not meta["Last Updated"]:
        raise ValueError("empty 'Last Updated' metadata cell")
    bounds = meta["Date Range"].split(" to ")
    if len(bounds) != 2:
        raise ValueError(f"unreviewed Date Range {meta['Date Range']!r}")
    for b in bounds:
        _month_first(b)
    if bounds[0] >= bounds[1]:
        raise ValueError(f"Date Range start {bounds[0]!r} not before end {bounds[1]!r}")

    header_seen = 0
    values: dict[str, str] = {}
    seen: set[str] = set()
    dates: list[str] = []
    prev: str | None = None
    for ident, cells in p.st.rows:
        if ident != "obs":
            continue
        if all(tag == "th" and scope == "col" for tag, scope, _ in cells):
            header_seen += 1
            if [(scope, text.strip()) for _, scope, text in cells] != \
                    [("col", "DATE"), ("col", "VALUE")]:
                raise ValueError(f"unreviewed observations header {cells!r} (need exactly "
                                 f"DATE/VALUE; an extra status column is unreviewed drift)")
            continue
        if header_seen != 1:
            raise ValueError("observations data row before/without the single DATE/VALUE "
                             "header row")
        if len(cells) != 2 or cells[0][:2] != ("th", "row") or cells[1][0] != "td":
            raise ValueError(f"observations row shape drift (an extra status column?): "
                             f"{cells!r}")
        date_text = cells[0][2].strip()
        period = _month_first(date_text)
        if period in seen:
            raise ValueError(f"duplicate period {period} in the observations table")
        seen.add(period)
        if prev is not None and period <= prev:
            raise ValueError(f"observations dates out of order at {period}")
        prev = period
        dates.append(date_text)
        token = cells[1][2].strip()
        if token == _MISSING:
            continue  # proved missing marker: no value, never invent one
        values[period] = _numeric(token)
    if header_seen != 1:
        raise ValueError(f"{header_seen} observations header rows (need exactly 1)")
    if not dates:
        raise ValueError("observations table body is empty (client-side rendering change?)")
    if dates[0] != bounds[0] or dates[-1] != bounds[1]:
        raise ValueError(f"declared Date Range {meta['Date Range']!r} but table rows run "
                         f"{dates[0]}..{dates[-1]}")
    return unit, values


def _envelope(r: HttpResult) -> bytes:
    """The item's evidence: one versioned JSON envelope (schema 'fred-table-evidence', v1)
    bundling the exact wire record of the /data/<code> page — final URL, actual HTTP status
    and the full body base64-encoded (byte-for-byte recoverable from the raw store with no
    HTTP; metadata AND values come from this one response, so one record carries both)."""
    doc = {"schema": EVIDENCE_SCHEMA, "version": EVIDENCE_VERSION,
           "table": {"url": r.url, "status": r.status,
                     "body_b64": base64.b64encode(r.body).decode("ascii")}}
    return json.dumps(doc, ensure_ascii=True, separators=(",", ":")).encode("ascii")


class FredVerifier:
    """See the module docstring. ONE /data/<code> page fetch per unique series per check()
    call (the same response is the value source AND the unit/frequency/seasonal-adjustment
    source); every ItemResult carries the versioned evidence envelope, observed_unit read
    from the page's own metadata table, observed_decimal '.', observed_flag None. A period
    absent from the table yields observed_text=None (honest 'not found', decided by
    ingest.verify as a mismatch)."""
    source_name = "fred"

    def check(self, items: list[BlindItem], http: Http) -> list[ItemResult]:
        pages: dict[str, tuple[str, dict[str, str], HttpResult]] = {}
        results: list[ItemResult] = []
        for item in items:
            code = _native(item.spec.native_code)
            if code not in pages:
                r = http.get(TABLE_URL + code)  # keyless public page: no params, no api_key
                if not 200 <= r.status < 300:
                    raise ValueError(f"FRED data table for {code} answered HTTP {r.status}")
                unit, values = read_table_page(r.body, code, item.spec)
                pages[code] = (unit, values, r)
            unit, values, r = pages[code]
            results.append(ItemResult(
                series_id=item.series_id, period=item.period,
                observed_text=values.get(item.period),
                evidence_url=r.url, observed_decimal=".", observed_unit=unit,
                observed_flag=None, evidence=_envelope(r)))
        return results
