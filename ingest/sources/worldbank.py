"""World Bank World Development Indicators source adapter: the keyless API v2 JSON channel.

    GET https://api.worldbank.org/v2/country/<geo;geo;...>/indicator/<CODE>
        ?format=json&per_page=20000[&page=N]

Recorded evidence in tests/ingest/fixtures/worldbank/ (2026-11-11, sha256-pinned by
MANIFEST.json). Keyless, `active` coverage = 930 series over 19 indicators x 54 geographies
(registry/unmapped-worldbank.md: the 52 gdp_per_capita_ppp series are INACTIVE over a proven
unit-definition conflict — the publisher serves current international $, not the registry's
constant 2017 dollars).

Registry contract (`SeriesSpec.native_code`): '<WDI indicator code>:<publisher ISO3>' — e.g.
'NY.GDP.MKTP.CD:PRT'. ISO3 codes derive from the publisher's own country metadata (archived
country-metadata.json), never a hand-built ISO2 table. `SeriesSpec.url` is the canonical
institution series address https://api.worldbank.org/v2/country/<ISO3>/indicator/<CODE>.

Fetch strategy: ONE request per indicator carrying the indicator's full registry geography set
(joined by ';', sorted; the publisher maps EU->EUU, GR->GRC, ... and the payload asserts it).
per_page=20000 covers the full annual history single-page at current scope (54 geos x ~66
years = ~3.5K rows); pagination is followed when meta declares pages>1 (page, pages, per_page,
total cross-checked per response and across a series' pages; a duplicated page or a drifting
count fails closed). Requests are grouped by indicator ONLY — never one request per
observation/country.

Response shape (fail-closed): [meta, rows]; meta keys exactly {page, pages, per_page, total,
sourceid ("2" = WDI), lastupdated}; non-2xx, HTML, the publisher error shape
([{"message": ...}]), truncated row counts or page-count drift all raise. Each row must have
exactly {indicator{id,value}, country{id,value}, countryiso3code, date, value, unit,
obs_status, decimal}: number tokens via json.loads(parse_int/parse_float TAGGING JSON numbers
as _Num, a str subclass internal to this module — a JSON string is NEVER a number token, so a
quoted "04442" cannot silently become the stored value while still Decimal-matching the CSV
channel); identity labels must be genuine JSON strings (type is str, not _Num); `value` is a
JSON number token (verbatim str, exponents PRESERVED — the existing validator quarantines
scientific notation as non_numeric; this adapter never reformats) or null (missing ->
value_raw=None, quarantined non_numeric downstream; never zero-filled); per-observation `unit`
and `obs_status` are empty strings in all archived evidence -> unit_raw=None (absent,
declared honestly) and flag_raw='normal' by explicit declaration of the reviewed shape; ANY
non-empty unit/obs_status is an unreviewed vocabulary and raises. Row identity is asserted in
the payload: indicator.id equals the response URL's indicator, countryiso3code matches the
series' native ISO3 AND country.id matches the registry geography (publisher ISO2); duplicates
of (series, date) raise. parse() does NOT require the complete page set — replay of archived
partial sets (e.g. the r1 page-1-of-14 probe) must work; completeness is fetch()'s contract.
"""
import json
import re
from collections.abc import Iterator

from ingest.http import Http
from ingest.models import SeriesSpec
from ingest.sources import RawResponse
from ingest.validate import RawRow

API_BASE = "https://api.worldbank.org/v2"
PER_PAGE = 20000
WDI_SOURCE_ID = "2"

_INDICATOR = re.compile(r"[A-Z0-9]+(?:\.[A-Z0-9]+)+")
_ISO3 = re.compile(r"[A-Z]{3}")
_DATE = re.compile(r"\d{4}")
_INT_TOKEN = re.compile(r"\d+")
_LASTUPDATED = re.compile(r"\d{4}-\d{2}-\d{2}")
_URL_PATH = re.compile(r"^/v2/country/([A-Z]{2}(?:;[A-Z]{2})*)/indicator/([A-Z0-9.]+)$")

_META_KEYS = {"page", "pages", "per_page", "total", "sourceid", "lastupdated"}
_ROW_KEYS = {"indicator", "country", "countryiso3code", "date", "value", "unit",
             "obs_status", "decimal"}


def parse_native_code(code: str | None) -> tuple[str, str]:
    """'<WDI indicator>:<publisher ISO3>' -> (indicator, iso3); ValueError if malformed.
    The full pair is the unique publisher identity of an active series."""
    indicator, sep, iso3 = (code or "").partition(":")
    if not sep or not _INDICATOR.fullmatch(indicator) or not _ISO3.fullmatch(iso3):
        raise ValueError(f"World Bank native_code must be '<indicator>:<ISO3>', got {code!r}")
    return indicator, iso3


class _Num(str):
    """Internal JSON-number tag: json.loads(parse_int=parse_float=_Num) marks real JSON number
    tokens so a quoted string can never be confused with a publisher number. Never leaves the
    module as a subclass: tokens are coerced to plain str before any RawRow is built."""


def _reject_constant(x: str):
    raise ValueError(f"World Bank payload carries a non-JSON constant {x!r}")


def _no_duplicate_keys(pairs: list) -> dict:
    keys = [k for k, _ in pairs]
    if len(set(keys)) != len(keys):
        raise ValueError(f"World Bank payload has duplicate keys {sorted(set(keys))[:5]}")
    return dict(pairs)


def _loads(body: bytes, what: str):
    head = body[:64].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    if head.startswith(b"<"):
        raise ValueError(f"World Bank {what} answered markup/HTML, not JSON: {body[:80]!r}")
    try:
        return json.loads(body, parse_int=_Num, parse_float=_Num,
                          parse_constant=_reject_constant,
                          object_pairs_hook=_no_duplicate_keys)
    except (ValueError, UnicodeDecodeError) as e:
        raise ValueError(f"World Bank {what} is not valid JSON: {e}") from e


def _meta_int(v, name: str) -> int:
    """Meta counts arrive as bare JSON ints ON SOME ENDPOINTS and quoted digits on others
    (evidence: per_page quoted on /v2/indicator metadata, bare on data pages); both are
    accepted, anything else (bool, 1.5, text) is not."""
    if isinstance(v, bool):
        raise ValueError(f"World Bank meta {name!r} must be an integer, got {v!r}")
    if isinstance(v, (_Num, str)) and _INT_TOKEN.fullmatch(str(v)):
        return int(v)
    raise ValueError(f"World Bank meta {name!r} must be an integer, got {v!r}")


def _dataset(body: bytes, what: str) -> tuple[dict, list]:
    """Strict [meta, rows] envelope; the publisher error shape ([{"message": [...]}]) and any
    other shape fail closed."""
    doc = _loads(body, what)
    if isinstance(doc, list) and len(doc) == 1 and isinstance(doc[0], dict) \
            and "message" in doc[0]:
        raise ValueError(f"World Bank {what} is an API error response: {doc[0]!r}")
    if not isinstance(doc, list) or len(doc) != 2 or not isinstance(doc[0], dict):
        raise ValueError(f"World Bank {what} has an unexpected shape (not [meta, rows]): "
                         f"{body[:120]!r}")
    meta, rows = doc
    if set(meta) != _META_KEYS:
        raise ValueError(f"World Bank {what} meta keys drifted: {sorted(meta)}")
    if str(meta["sourceid"]) != WDI_SOURCE_ID:
        raise ValueError(f"World Bank {what} is not source {WDI_SOURCE_ID} (WDI): "
                         f"{meta['sourceid']!r}")
    if type(meta["lastupdated"]) is not str or not _LASTUPDATED.fullmatch(meta["lastupdated"]):
        raise ValueError(f"World Bank {what} lastupdated drifted: {meta['lastupdated']!r}")
    out = {"page": _meta_int(meta["page"], "page"), "pages": _meta_int(meta["pages"], "pages"),
           "per_page": _meta_int(meta["per_page"], "per_page"),
           "total": _meta_int(meta["total"], "total"),
           "sourceid": WDI_SOURCE_ID, "lastupdated": meta["lastupdated"]}
    if not (1 <= out["page"] <= out["pages"]) or out["per_page"] < 1 or out["total"] < 0:
        raise ValueError(f"World Bank {what} meta page counts inconsistent: {meta!r}")
    if out["total"] == 0:
        if rows not in (None, []):
            raise ValueError(f"World Bank {what} declares total=0 but carries rows")
        return out, []
    if not isinstance(rows, list):
        raise ValueError(f"World Bank {what} declares total={out['total']} but rows is "
                         f"{type(rows).__name__} (truncation/drift)")
    n = len(rows)
    if n > out["per_page"]:
        raise ValueError(f"World Bank {what} page holds {n} rows > per_page "
                         f"{out['per_page']} (page counts inconsistent)")
    if out["page"] == out["pages"]:
        if n != out["total"] - out["per_page"] * (out["pages"] - 1):
            raise ValueError(f"World Bank {what} meta total {out['total']} but the final page "
                             f"holds {n} rows (truncation/drift)")
    elif n != out["per_page"]:
        raise ValueError(f"World Bank {what} page {out['page']} of {out['pages']} holds {n} "
                         f"rows != per_page {out['per_page']} (truncation/drift)")
    return out, rows


def _token(v, what: str) -> str | None:
    """A publisher value: null -> None (missing, never zero); a JSON NUMBER (tagged _Num;
    quoted strings rejected even when numeric-shaped) -> the verbatim token as plain str,
    exponent forms PRESERVED (validation quarantines them; no reformatting here)."""
    if v is None:
        return None
    if type(v) is not _Num:
        raise ValueError(f"{what} must be a JSON number token, got {v!r}")
    return str(v)


def _label(v, what: str) -> str:
    """A genuine JSON STRING (never a tagged number): identity labels are type-checked."""
    if type(v) is not str or not v.strip():
        raise ValueError(f"World Bank {what} must be a non-empty JSON string, got {v!r}")
    return v


def _row(row, what: str) -> tuple[str, str, str, str | None, str]:
    """(indicator_id, iso3, country_id, value_token, date) of one data row, strictly shaped.
    Raises on: missing/extra fields, non-string identity labels, non-empty unit/status
    (unreviewed vocabulary), a quoted or non-numeric value token."""
    if not isinstance(row, dict) or set(row) != _ROW_KEYS:
        raise ValueError(f"World Bank {what} row fields drifted: {row!r}")
    ind, country = row["indicator"], row["country"]
    if not isinstance(ind, dict) or set(ind) != {"id", "value"}:
        raise ValueError(f"World Bank {what} row indicator block drifted: {ind!r}")
    if not isinstance(country, dict) or set(country) != {"id", "value"}:
        raise ValueError(f"World Bank {what} row country block drifted: {country!r}")
    ind_id = _label(ind["id"], f"{what} row indicator.id")
    _label(ind["value"], f"{what} row indicator.value")
    country_id = _label(country["id"], f"{what} row country.id")
    _label(country["value"], f"{what} row country.value")
    iso3 = row["countryiso3code"]
    if type(iso3) is not str or not _ISO3.fullmatch(iso3):
        raise ValueError(f"World Bank {what} row countryiso3code is not an ISO3 label: "
                         f"{iso3!r}")
    d = row["date"]
    if type(d) is not str or not _DATE.fullmatch(d):
        raise ValueError(f"World Bank {what} row date is not a YYYY label, got {d!r}")
    if type(row["unit"]) is not str or row["unit"] != "":
        raise ValueError(f"World Bank {what} row carries a non-empty unit surface "
                         f"{row['unit']!r}: unreviewed vocabulary, fail closed")
    if type(row["obs_status"]) is not str or row["obs_status"] != "":
        raise ValueError(f"World Bank {what} row carries a non-empty obs_status surface "
                         f"{row['obs_status']!r}: unreviewed vocabulary, fail closed")
    dec = row["decimal"]
    if type(dec) is not _Num or not _INT_TOKEN.fullmatch(str(dec)):
        raise ValueError(f"World Bank {what} row 'decimal' hint must be a JSON integer, got "
                         f"{dec!r}")  # a publisher FORMATTING hint only, never used to truncate
    return ind_id, iso3, country_id, _token(row["value"], f"{what} row value"), d


def _url_identity(url: str, what: str) -> str:
    """The indicator code a response URL claims to answer; the path shape is fixed."""
    from urllib.parse import urlsplit
    m = _URL_PATH.match(urlsplit(url).path)
    if not m:
        raise ValueError(f"World Bank {what} URL is not a /v2/country/<geos>/indicator/<code> "
                         f"request: {url!r}")
    return m.group(2)


def _check_non2xx(resp: RawResponse, what: str) -> None:
    if not 200 <= resp.status < 300:
        raise ValueError(f"World Bank {what} request for {resp.url!r} answered HTTP "
                         f"{resp.status} (fail closed on every non-2xx)")


class WorldBankSource:
    """WDI JSON source. Full annual history per (indicator, registry-geography set); one
    response per indicator page, fetched in sorted indicator order."""

    name = "worldbank"
    expected_format = "json"

    def fetch(self, specs: list[SeriesSpec], http: Http) -> Iterator[RawResponse]:
        timeouts = {s.source.timeout_s for s in specs}
        if len(timeouts) != 1:
            raise ValueError(f"World Bank fetch over mixed source timeouts: {timeouts!r}")
        (timeout,) = timeouts
        groups: dict[str, set[str]] = {}
        for s in specs:
            code, _ = parse_native_code(s.native_code)
            groups.setdefault(code, set()).add(s.geography)
        for code in sorted(groups):
            geos = ";".join(sorted(groups[code]))
            url = f"{API_BASE}/country/{geos}/indicator/{code}"
            page = 1
            while True:
                params = {"format": "json", "per_page": str(PER_PAGE)}
                if page > 1:
                    params["page"] = str(page)
                r = http.get(url, params=params) if timeout is None else \
                    http.get(url, params=params, timeout=timeout)
                yield RawResponse(url=r.url, params=params, status=r.status, body=r.body)
                if not 200 <= r.status < 300:
                    break  # the pipeline classifies it; never retry/filter here
                meta, _ = _dataset(r.body, f"indicator {code} page {page}")
                if page >= meta["pages"]:
                    break
                page += 1

    def parse(self, specs: list[SeriesSpec],
              responses: list[RawResponse]) -> dict[str, list[RawRow]]:
        """Map archived responses to per-series rows. Rows self-identify
        (indicator.id + countryiso3code + country.id); the URL's indicator must agree. See the
        module docstring for the fail-closed contract."""
        wanted: dict[str, SeriesSpec] = {}
        for s in specs:
            code, iso3 = parse_native_code(s.native_code)
            key = f"{code}:{iso3}"
            if key in wanted:
                raise ValueError(f"duplicate native_code among World Bank specs: {key}")
            wanted[key] = s
        codes_wanted = {k.split(":")[0] for k in wanted}
        rows: dict[str, list[RawRow]] = {s.id: [] for s in specs}
        seen_pages: dict[str, tuple] = {}  # code -> (pages, per_page, total, set-of-page-ids)
        seen_rows: set[tuple[str, str]] = set()  # (series_id, date) across ALL responses
        seen_countries: dict[str, tuple[str, str]] = {}  # iso3 -> (country.id, country.value)
        for i, resp in enumerate(responses):
            what = f"response[{i}]"
            _check_non2xx(resp, what)
            url_code = _url_identity(resp.url, what)
            if url_code not in codes_wanted:
                raise ValueError(f"World Bank response[{i}] answered unrequested indicator "
                                 f"{url_code!r}")
            meta, data = _dataset(resp.body, what)
            if url_code in seen_pages:
                prev = seen_pages[url_code]
                if prev[:3] != (meta["pages"], meta["per_page"], meta["total"]):
                    raise ValueError(f"World Bank pages of {url_code} disagree on "
                                     f"pages/per_page/total across responses")
                pages_seen = prev[3]
            else:
                pages_seen = set()
                seen_pages[url_code] = (meta["pages"], meta["per_page"], meta["total"],
                                        pages_seen)
            if meta["page"] in pages_seen:
                raise ValueError(f"World Bank indicator {url_code} page {meta['page']} "
                                 f"arrived twice")
            pages_seen.add(meta["page"])
            for raw in data:
                ind_id, iso3, country_id, token, d = _row(raw, what)
                if ind_id != url_code:
                    raise ValueError(f"World Bank response[{i}] URL indicator {url_code!r} "
                                     f"does not match payload indicator {ind_id!r}")
                spec = wanted.get(f"{ind_id}:{iso3}")
                if spec is None:
                    raise ValueError(f"World Bank response[{i}] carries unrequested identity "
                                     f"{ind_id}:{iso3} (countryiso3code/geography drift)")
                if country_id != spec.geography:
                    raise ValueError(f"World Bank response[{i}] row {ind_id}:{iso3} carries "
                                     f"country.id {country_id!r} != registry geography "
                                     f"{spec.geography!r}")
                country_label = raw["country"]["value"]
                if iso3 in seen_countries and seen_countries[iso3] != (country_id,
                                                                       country_label):
                    raise ValueError(f"World Bank country identity for {iso3} drifts across "
                                     f"responses: {seen_countries[iso3]!r} vs "
                                     f"{(country_id, country_label)!r}")
                seen_countries[iso3] = (country_id, country_label)
                if (spec.id, d) in seen_rows:
                    raise ValueError(f"World Bank duplicate row for {spec.id} date {d} "
                                     f"(duplicate identity across pages)")
                seen_rows.add((spec.id, d))
                rows[spec.id].append(RawRow(period_raw=d, value_raw=token, unit_raw=None,
                                            flag_raw="normal", response_index=i))
        return rows
