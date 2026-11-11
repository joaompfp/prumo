"""Independent verifier for World Bank WDI (spec 6b):

    collector: keyless API v2 JSON
        api.worldbank.org/v2/country/<geos>/indicator/<CODE>?format=json&per_page=20000
    verifier:  the publisher's genuine BULK CSV ZIP EXPORT — a different endpoint family AND a
        different (CSV table inside a ZIP archive) serialization, not a JSON re-serialization:
        GET https://api.worldbank.org/v2/en/indicator/<CODE>?downloadformat=csv
        (HTTP 200 application/zip; recorded 2026-11-11 as full archives in
        tests/ingest/fixtures/worldbank/, sha256-pinned by MANIFEST.json)

Channel mechanics (from the archived bytes):
- The ZIP holds exactly THREE members: the main data CSV
  'API_<CODE>_DS2_en_csv_v2_<rev>.csv', 'Metadata_Indicator_API_<CODE>_...csv' and
  'Metadata_Country_API_<CODE>_...csv'. Any other member count/name, a path-traversal name
  ('..', absolute) or a member whose size disagrees with its declared entry fails closed; the
  archive is processed IN MEMORY (never extracted to the filesystem) with bounded member
  count/uncompressed size/reads (ZIP-bomb guards: MAX_MEMBERS, MAX_MEMBER_BYTES,
  MAX_TOTAL_BYTES; actual reads are capped and the realized length must equal the entry's).
- The main CSV starts with a metadata block: '"Data Source","World Development Indicators",',
  a blank row, '"Last Updated Date","<YYYY-MM-DD>",' (shape-validated ONLY; per the blind
  protocol it is never compared against collector metadata), another blank row, then the
  table header '"Country Name","Country Code","Indicator Name","Indicator Code","1960",...'
  and one row per country/aggregate, all cells quoted, every row ending in a trailing comma
  (the header's final cell is empty accordingly). Year columns must be unique; rows must be
  unique per Country Code (+Indicator Code, which must equal the requested CODE on every row);
  duplicates or header drift fail closed.
- Values are quoted decimal-string tokens ('.' decimal), '' = missing -> the item is reported
  not-found (observed_text=None); a sampled observation whose cell is empty is a genuine
  mismatch decided by ingest.verify, never zero-filled or skipped here. Tokens are returned
  VERBATIM (no stripping/reformatting).
- NO per-cell status/footnote surface and NO machine-readable unit column exist in this
  channel: observed_flag=None and observed_unit=None, honestly (unit evidence lives in the
  indicator sourceNote prose; the registry unit labels are audited in
  tests/ingest/test_registry_worldbank_units.py, not here).

EVIDENCE (Ruling R/AC/G7): the ONE deciding ZIP response per (item, indicator) is archived in
a versioned JSON envelope ('worldbank-csv-evidence' v1: {"responses": [{"url", "status",
"body_base64"}]}) — exact bytes, FINAL url and ACTUAL http status, byte-for-byte recoverable
from the raw store without HTTP. The envelope format is module-local (no shared code with the
collector); one ZIP is fetched per indicator per check() call (in-memory cache only, never
persisted).

INDEPENDENCE: this module shares NO code with the collector (enforced by register_verifier's
static allowlist and the assert_verifier_independent subprocess guard). The native_code
identity split is DUPLICATED ON PURPOSE: two copies that ever disagree fail verification.
Requests are one GET per indicator per check; sleeping/throttling is the injected Http's job.
"""
import base64
import csv
import io
import json
import re
import zipfile

from ingest.http import Http
from ingest.verifiers import BlindItem, ItemResult

CSV_URL = "https://api.worldbank.org/v2/en/indicator/{code}?downloadformat=csv"
EVIDENCE_SCHEMA = "worldbank-csv-evidence"
EVIDENCE_VERSION = 1

# ZIP-bomb / safety bounds: the published shape is 3 members, main data CSV observed at
# ~300 KB uncompressed (2026-11-11); the caps leave two orders of magnitude of headroom.
MAX_MEMBERS = 3
MAX_MEMBER_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024

_INDICATOR = re.compile(r"[A-Z0-9]+(?:\.[A-Z0-9]+)+")
_ISO3 = re.compile(r"[A-Z]{3}")
_PERIOD = re.compile(r"\d{4}")
_DATE_STAMP = re.compile(r"\d{4}-\d{2}-\d{2}")


def _indicator_of(code: str | None) -> tuple[str, str]:
    """'<WDI indicator>:<publisher ISO3>' -> (indicator, iso3). DUPLICATE of the collector's
    parse_native_code, ON PURPOSE (see module docstring)."""
    indicator, sep, iso3 = (code or "").partition(":")
    if not sep or not _INDICATOR.fullmatch(indicator) or not _ISO3.fullmatch(iso3):
        raise ValueError(f"World Bank native_code must be '<indicator>:<ISO3>', got {code!r}")
    return indicator, iso3


def _envelope(url: str, status: int, body: bytes) -> bytes:
    """The evidence bytes of one item: the ONE deciding CSV ZIP response in a versioned JSON
    envelope — final URL, ACTUAL http status (recorded from the received HttpResult, never
    implied) and the raw archive byte-for-byte (base64)."""
    doc = {"schema": EVIDENCE_SCHEMA, "version": EVIDENCE_VERSION,
           "responses": [{"url": url, "status": status,
                          "body_base64": base64.b64encode(body).decode("ascii")}]}
    return json.dumps(doc, ensure_ascii=True, separators=(",", ":")).encode("ascii")


def _read_member(z, info, limit: int, what: str) -> bytes:
    """Bounded read of one member: never reads past `limit` bytes; the realized length must
    equal the entry's declared size (a lying central directory is an integrity failure)."""
    if info.file_size > limit:
        raise ValueError(f"World Bank CSV ZIP member {info.filename!r} too large "
                         f"({info.file_size} bytes > cap {limit})")
    with z.open(info) as f:
        data = f.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"World Bank CSV ZIP member {info.filename!r} exceeds cap {limit}")
    if len(data) != info.file_size:
        raise ValueError(f"World Bank CSV ZIP member {info.filename!r} realized {len(data)} "
                         f"bytes != declared {info.file_size} (truncated/lying archive)")
    return data


def _read_export(body: bytes, code: str, what: str) -> bytes:
    """The main data CSV bytes of a deciding ZIP, with every safety guard fail-closed."""
    if not body.startswith(b"PK"):
        raise ValueError(f"World Bank CSV export for {what} is not a ZIP (markup/garbage): "
                         f"{body[:80]!r}")
    try:
        z = zipfile.ZipFile(io.BytesIO(body))
    except zipfile.BadZipFile as e:
        raise ValueError(f"World Bank CSV export for {what} is a malformed ZIP: {e}") from e
    with z:
        infos = z.infolist()
        if len(infos) != MAX_MEMBERS:
            raise ValueError(f"World Bank CSV export for {what} carries {len(infos)} members, "
                             f"expected exactly {MAX_MEMBERS}: {z.namelist()!r}")
        main = meta_i = meta_c = None
        total = 0
        for info in infos:
            name = info.filename
            if "/" in name or "\\" in name or ".." in name or not name:
                raise ValueError(f"World Bank CSV export member name unsafe: {name!r}")
            total += info.file_size
            if total > MAX_TOTAL_BYTES:
                raise ValueError(f"World Bank CSV export for {what} exceeds the total size cap")
            if name.startswith(f"API_{code}_DS2_") and name.endswith(".csv"):
                if main is not None:
                    raise ValueError(f"World Bank CSV export for {what} has ambiguous main "
                                     f"members: {z.namelist()!r}")
                main = info
            elif name.startswith(f"Metadata_Indicator_API_{code}_DS2_"):
                meta_i = info
            elif name.startswith(f"Metadata_Country_API_{code}_DS2_"):
                meta_c = info
            else:
                raise ValueError(f"World Bank CSV export for {what} carries an unexpected "
                                 f"member {name!r} (identity drift)")
        if main is None or meta_i is None or meta_c is None:
            raise ValueError(f"World Bank CSV export for {what} misses the expected "
                             f"{code} members: {z.namelist()!r}")
        return _read_member(z, main, MAX_MEMBER_BYTES, what)


def _table(main: bytes, code: str, what: str) -> tuple[dict[str, list[str]], dict[str, int]]:
    """(row per Country Code, year -> column) of the main CSV, strictly shaped."""
    try:
        text = main.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ValueError(f"World Bank CSV export for {what} is not UTF-8: {e}") from e
    try:
        rows = list(csv.reader(io.StringIO(text), strict=True))
    except csv.Error as e:
        raise ValueError(f"World Bank CSV export for {what} is malformed CSV: {e}") from e
    if len(rows) < 6:
        raise ValueError(f"World Bank CSV export for {what} is too short: {len(rows)} rows")
    if rows[0] != ["Data Source", "World Development Indicators", ""]:
        raise ValueError(f"World Bank CSV export for {what} header block drifted: {rows[0]!r}")
    if rows[1] or not rows[2] or rows[2][0] != "Last Updated Date" or len(rows[2]) != 3 \
            or rows[2][2] != "" or not _DATE_STAMP.fullmatch(rows[2][1]):
        raise ValueError(f"World Bank CSV export for {what} Last Updated row drifted: "
                         f"{rows[2]!r}")  # the date is shape-validated ONLY (blind protocol)
    if rows[3]:
        raise ValueError(f"World Bank CSV export for {what} header block drifted: {rows[3]!r}")
    header = rows[4]
    if header[:4] != ["Country Name", "Country Code", "Indicator Name", "Indicator Code"] \
            or header[-1] != "" or len(header) < 6:
        raise ValueError(f"World Bank CSV export for {what} table header drifted: {header!r}")
    years = header[4:-1]
    if not years or any(not _PERIOD.fullmatch(y) for y in years) \
            or len(set(years)) != len(years) or years != sorted(years):
        raise ValueError(f"World Bank CSV export for {what} year columns are not unique "
                         f"ascending year labels: {years[:5]!r}...")
    ycol = {y: i + 4 for i, y in enumerate(years)}
    data = rows[5:]
    seen: dict[str, list[str]] = {}
    names = set()
    for r in data:
        if len(r) != len(header) or r[-1] != "":
            raise ValueError(f"World Bank CSV export for {what} row has {len(r)} cells "
                             f"(header {len(header)}): {r[:6]!r}")
        iso3, name, rcode = r[1], r[2], r[3]
        if not _ISO3.fullmatch(iso3):
            raise ValueError(f"World Bank CSV export for {what} row country code is not an "
                             f"ISO3 label: {iso3!r}")
        if rcode != code:
            raise ValueError(f"World Bank CSV export for {what} carries Indicator Code "
                             f"{rcode!r} != requested {code!r} (identity drift)")
        if iso3 in seen:
            raise ValueError(f"World Bank CSV export for {what} repeats the country row "
                             f"{iso3!r} (duplicate identity)")
        seen[iso3] = r
        names.add(name)
    if len(names) != 1:
        raise ValueError(f"World Bank CSV export for {what} disagrees on the indicator name: "
                         f"{sorted(names)[:3]!r}")
    return seen, ycol


class WorldBankVerifier:
    """See the module docstring: one full CSV ZIP per indicator (cached inside a single
    check() call), period/identity read from the table itself, observed_unit/observed_flag
    honestly None (no such surfaces in this channel), evidence = the deciding response's
    versioned envelope (exact ZIP bytes + final URL + actual HTTP status)."""

    source_name = "worldbank"

    def check(self, items: list[BlindItem], http: Http) -> list[ItemResult]:
        zips: dict[str, tuple[bytes, str, int]] = {}  # code -> (body, final url, status)
        tables: dict[str, tuple[dict[str, list[str]], dict[str, int]]] = {}
        results: list[ItemResult] = []
        for item in items:
            code, iso3 = _indicator_of(item.spec.native_code)
            if not _PERIOD.fullmatch(item.period):
                raise ValueError(f"World Bank verifier accepts canonical yearly periods only, "
                                 f"got {item.period!r}")
            if code not in zips:
                r = http.get(CSV_URL.format(code=code))
                if not 200 <= r.status < 300:
                    raise ValueError(f"World Bank CSV export for indicator {code} answered "
                                     f"HTTP {r.status} (fail closed on every non-2xx)")
                zips[code] = (r.body, r.url, r.status)
                tables[code] = _table(_read_export(r.body, code, item.series_id),
                                      code, item.series_id)
            body, url, status = zips[code]
            rows, ycol = tables[code]
            row = rows.get(iso3)
            if item.period not in ycol:
                raise ValueError(f"World Bank CSV export for {code} has no column for the "
                                 f"requested period {item.period!r} (export drift)")
            cell = row[ycol[item.period]] if row is not None else ""
            results.append(ItemResult(
                series_id=item.series_id, period=item.period,
                observed_text=cell if cell != "" else None,
                evidence_url=url, observed_decimal=".", observed_unit=None,
                observed_flag=None, evidence=_envelope(url, status, body)))
        return results
