"""Independent verifier for Banco de Portugal (BPstat), spec 6b:

    collector:  public documented data API, JSON-stat 2.0
                (/data/v1/domains/<domain>/datasets/<dataset>/?decimal=true)
    verifier:   BPstat PORTAL internal API that drives the bpstat.bportugal.pt SPA
                (/api/observations/ row records + /api/series/?view_full metadata)

A different endpoint family AND a different response schema (one flat row per publication
vintage vs JSON-stat dimension/strides arrays), discovered from the live SPA network trace on
2026-11-11 and reproduced with plain HTTP (no JS, no auth, no cookies, no Referer). The portal
shows values exactly as the website publishes them ('decimal=true' on the collector mirrors the
same rendering, so both channels carry '.'-decimal publisher strings; verification compares
exact Decimals, Ruling AB, which absorbs any rendering-only difference).

Channel mechanics (recorded live in tests/ingest/fixtures/bportugal/verify/):

1.  GET /api/observations/?series_ids=<id>&start_date=<month first>&end_date=<month last>
    -> {"data": [rows]}. One sampled (series, month) per request. A reference_date can have
    SEVERAL rows = publication vintages with distinct pub_date (live revision evidence:
    12099464 @2023-08-31 '3.30' pub 2023-09-04, then '3.31' pub 2023-10-03). The CURRENT value
    is the row with the latest pub_date; a tie, a row for another series/month, a non-public
    privacy_code, or a non-empty free-text description must never be guessed at: they raise.
    An empty data list means the portal has no observation there -> observed_text=None
    ("not found", decided by ingest.verify as a mismatch).
2.  GET /api/series/?view_full=true&page_size=1&series_ids=<id> -> full metadata once per
    series per check() call: recurrence (must equal the spec frequency after the reviewed
    monthly mapping), Unit of measure member (observed_unit, fail-closed map; 'Currency' only
    accepted as the EUR/USD reference pair -> 'USD/EUR'), Reference territory member (must map
    onto spec.geography: Portugal/Germany/Euro Area - Changing composition -> PT/DE/EA; the
    EUR/USD series carries no territory and is pinned by its currency pair, geography EA by
    reviewed convention). Some members have no EN title; the needed surfaces all do.
    observed_flag: this channel exposes NO observation status (rows carry privacy_code 'P' and
    an empty description only), so observed_flag is None and the flag is not compared —
    documented, never echoed from the spec.

EVIDENCE (Ruling R/G7): one item's decision reads TWO publisher responses — the series-metadata
record (observed_unit) and the month-window observations (observed_text). ItemResult.evidence
therefore bundles both exact wire records in a versioned JSON envelope (schema
'bportugal-portal-evidence', v1: per response the final URL, HTTP status and the raw body
base64-encoded, byte-for-byte recoverable from the raw store with no HTTP); the metadata body
is the response the unit was parsed from, bundled per item even though fetched once per series.
evidence_url stays the observations URL for continuity.

INDEPENDENCE: this module shares NO code with the collector (enforced by register_verifier and
by assert_verifier_independent). The tiny native_code parsing and the unit/territory/
periodicity maps are DUPLICATED ON PURPOSE: if the two copies ever disagree, verification fails
loudly. Requests are paced by the injected Http client (RequestsHttp throttles to <=1 req/s);
the verifier adds no sleeping of its own so recorded tests stay fast.
"""
import base64
import json
import re
from datetime import date, datetime, timedelta

from ingest.http import Http, HttpResult
from ingest.models import SeriesSpec
from ingest.verifiers import BlindItem, ItemResult

SERIES_URL = "https://bpstat.bportugal.pt/api/series/"
OBS_URL = "https://bpstat.bportugal.pt/api/observations/"

# DUPLICATES of the collector's reviewed maps, ON PURPOSE (see module docstring).
_UNIT_OF_LABEL = {"Percentage": "%", "Millions of euros": "MEUR"}
_TERRITORY_OF_LABEL = {"Portugal": "PT", "Germany": "DE", "Euro Area - Changing composition": "EA"}
_PERIODICITY_OF_LABEL = {"Monthly": "M"}
_CURRENCY_REF = ("Euro", "United States of America, Dollars")  # reference, counterparty
_CURRENCY_UNIT = "USD/EUR"
_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_PERIOD_RE = re.compile(r"^(\d{4})-(\d{2})$")


def _native(code: str | None) -> int:
    """'<series_id>:<domain>/<32-hex dataset>' -> the BPstat series id.

    DUPLICATE of the collector's parse_native_code, ON PURPOSE (see module docstring)."""
    series, sep1, rest = (code or "").partition(":")
    domain, sep2, dataset = rest.partition("/")
    if not (sep1 and sep2 and series.isdigit() and domain.isdigit()
            and re.fullmatch(r"[0-9a-f]{32}", dataset)):
        raise ValueError(f"BPstat native_code must be '<series id>:<domain id>/<32-hex dataset "
                         f"id>', got {code!r}")
    return int(series)


def _no_duplicate_keys(pairs: list) -> dict:
    keys = [k for k, _ in pairs]
    if len(set(keys)) != len(keys):
        raise ValueError(f"portal payload has duplicate keys {sorted(set(keys))[:5]}")
    return dict(pairs)


def _load(body: bytes, what: str) -> dict:
    head = body[:64].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    if head.startswith(b"<"):
        raise ValueError(f"portal {what} answered markup, not JSON: {body[:80]!r}")
    try:
        doc = json.loads(body, object_pairs_hook=_no_duplicate_keys)
    except (ValueError, UnicodeDecodeError) as e:
        raise ValueError(f"portal {what} is not valid JSON: {e}") from e
    if not isinstance(doc, dict) or not isinstance(doc.get("data"), list):
        raise ValueError(f"portal {what} is not the expected {{'data': [...]}} payload")
    return doc


def _title(multilang: dict) -> str | None:
    """EN title preferred; fall back to PT (some members ship PT only)."""
    if not isinstance(multilang, dict):
        return None
    v = multilang.get("EN") or multilang.get("PT")
    return v if isinstance(v, str) else None


def _meta_of(body: bytes, spec: SeriesSpec, sid: int) -> str:
    """observed_unit from the series' metadata record; raises on any identity drift."""
    doc = _load(body, "series metadata")
    data = doc["data"]
    if len(data) != 1 or data[0].get("id") != sid:
        raise ValueError(f"series metadata answered {len(data)} record(s) for id "
                         f"{data[0].get('id') if data else '?'}, asked {sid}")
    rec = data[0]
    labels = {}
    for mc in rec.get("membercombination") or []:
        d, m = _title(mc.get("dimension", {}).get("title")), _title(mc.get("member", {}).get("title"))
        if d and m:
            labels[d] = m
    freq = _PERIODICITY_OF_LABEL.get(labels.get("Periodicity") or "")
    if freq is None:
        raise ValueError(f"portal periodicity {labels.get('Periodicity')!r} not in the "
                         f"reviewed map")
    if rec.get("recurrence") != freq:
        raise ValueError(f"portal recurrence {rec.get('recurrence')!r} and periodicity member "
                         f"{labels.get('Periodicity')!r} disagree")
    if freq != spec.frequency:
        raise ValueError(f"{spec.id}: portal periodicity {labels.get('Periodicity')!r} ({freq}) "
                         f"!= registry frequency {spec.frequency!r}")
    unit = labels.get("Unit of measure")
    if unit == "Currency":
        if (labels.get("Reference currency"), labels.get("Counterparty currency")) != _CURRENCY_REF:
            raise ValueError(f"'Currency' unit without the reviewed EUR/USD pair: {labels!r}")
        observed_unit = _CURRENCY_UNIT
    else:
        observed_unit = _UNIT_OF_LABEL.get(unit or "")
    if observed_unit is None:
        raise ValueError(f"unknown portal unit-of-measure label {unit!r} for {spec.id}")
    territory = labels.get("Reference territory")
    if territory is not None:
        geo = _TERRITORY_OF_LABEL.get(territory)
        if geo is None:
            raise ValueError(f"unknown portal territory label {territory!r}")
        if geo != spec.geography:
            raise ValueError(f"{spec.id}: portal territory {territory!r} ({geo}) != registry "
                             f"geography {spec.geography!r}")
    elif spec.geography != "EA" \
            or (labels.get("Reference currency"), labels.get("Counterparty currency")) \
            != _CURRENCY_REF:
        raise ValueError(f"{spec.id}: no territory dimension and not the reviewed EUR/USD euro "
                         f"reference rate (geography EA): {labels!r}")
    return observed_unit


def _window(period: str) -> tuple[str, str]:
    """'YYYY-MM' -> (month first day, month last day) ISO dates (monthly series are
    end-dated)."""
    m = _PERIOD_RE.fullmatch(period)
    if not m:
        raise ValueError(f"verifier reviewed canonical monthly periods only, got {period!r}")
    y, mm = int(m.group(1)), int(m.group(2))
    if not 1 <= mm <= 12:
        raise ValueError(f"bad month in period {period!r}")
    end = date(y + (mm == 12), mm % 12 + 1, 1) - timedelta(days=1)
    return date(y, mm, 1).isoformat(), end.isoformat()


def _current(doc: dict, sid: int, period: str) -> str | None:
    """The currently-published value token (verbatim string) for (series, month), or None when
    the portal has no observation there. Any inconsistency raises."""
    rows = doc["data"]
    if not rows:
        return None
    dates = set()
    for row in rows:
        if not isinstance(row, dict) or row.get("series_id") != sid:
            raise ValueError(f"observation row for another series: {row!r}")
        ref = row.get("reference_date")
        if not isinstance(ref, str) or ref[:7] != period or not _DATE_RE.fullmatch(ref):
            raise ValueError(f"observation row outside the requested month {period}: {ref!r}")
        if row.get("privacy_code") != "P":
            raise ValueError(f"observation row with privacy_code {row.get('privacy_code')!r} "
                             f"(only public 'P' reviewed)")
        if row.get("description"):
            raise ValueError(f"observation row carries a free-text description "
                             f"{row.get('description')!r} — an unreviewed annotation surface")
        if not isinstance(row.get("value"), str) or not isinstance(row.get("pub_date"), str):
            raise ValueError(f"observation row without a string value/pub_date: {row!r}")
        dates.add(ref)
    if len(dates) != 1:
        raise ValueError(f"{len(dates)} distinct reference dates inside month {period}: "
                         f"{sorted(dates)}")
    published = {}
    for row in rows:
        try:
            when = datetime.fromisoformat(row["pub_date"].replace("Z", "+00:00"))
        except ValueError as e:
            raise ValueError(f"unparseable pub_date {row['pub_date']!r}") from e
        if when in published:
            raise ValueError(f"two vintages with identical pub_date {row['pub_date']!r}")
        published[when] = row["value"]
    return published[max(published)]


EVIDENCE_SCHEMA = "bportugal-portal-evidence"
EVIDENCE_VERSION = 1


def _wire_record(r: HttpResult) -> dict:
    """One portal response exactly as received: final URL (with query), status, raw body
    base64-encoded so the original bytes are recoverable byte-for-byte."""
    return {"url": r.url, "status": r.status,
            "body_b64": base64.b64encode(r.body).decode("ascii")}


def _envelope(meta: HttpResult, observations: HttpResult) -> bytes:
    """The evidence bytes of one item: a small versioned JSON document bundling the TWO portal
    responses the decision used (series metadata and month-window observations)."""
    doc = {"schema": EVIDENCE_SCHEMA, "version": EVIDENCE_VERSION,
           "metadata": _wire_record(meta), "observations": _wire_record(observations)}
    return json.dumps(doc, ensure_ascii=True, separators=(",", ":")).encode("ascii")


class BPortugalVerifier:
    """See the module docstring. One /api/series/ metadata fetch per series per check() call,
    plus one month-window /api/observations/ fetch per sampled item. An item's decision uses
    BOTH portal responses (metadata -> observed_unit, observations -> observed_text), so
    ItemResult.evidence is a small VERSIONED JSON envelope (schema 'bportugal-portal-evidence',
    version 1) bundling both wire records — exact final URL, HTTP status and the raw body
    base64-encoded (byte-for-byte recoverable from the raw store, no HTTP needed; Ruling R/G7).
    evidence_url stays the observations URL; observed_flag is honestly None (this channel
    exposes no observation status, so ingest.verify skips the flag comparison)."""
    source_name = "bportugal"

    def check(self, items: list[BlindItem], http: Http) -> list[ItemResult]:
        meta: dict[int, tuple[str, HttpResult]] = {}  # sid -> (observed_unit, wire record)
        results: list[ItemResult] = []
        for item in items:
            sid = _native(item.spec.native_code)
            if sid not in meta:
                r = http.get(SERIES_URL, params={"view_full": "true", "page_size": "1",
                                                 "series_ids": str(sid)})
                if not 200 <= r.status < 300:
                    raise ValueError(f"portal series metadata for {sid} answered HTTP {r.status}")
                meta[sid] = (_meta_of(r.body, item.spec, sid), r)
            unit, meta_r = meta[sid]
            start, end = _window(item.period)
            params = {"series_ids": str(sid), "start_date": start, "end_date": end}
            r = http.get(OBS_URL, params=params)
            if not 200 <= r.status < 300:
                raise ValueError(f"portal observations for {sid} {item.period} answered HTTP "
                                 f"{r.status}")
            observed = _current(_load(r.body, "observations"), sid, item.period)
            results.append(ItemResult(
                series_id=item.series_id, period=item.period, observed_text=observed,
                evidence_url=r.url, observed_decimal=".", observed_unit=unit,
                observed_flag=None, evidence=_envelope(meta_r, r)))
        return results
