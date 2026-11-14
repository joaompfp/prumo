"""Independent verifier for World Bank WDI (spec 6b):

    collector: keyless API v2 JSON
        api.worldbank.org/v2/country/<geos>/indicator/<CODE>?format=json&per_page=20000
    verifier:  the publisher's genuine BULK CSV ZIP EXPORT — a different endpoint family AND a
        different (CSV table inside a ZIP archive) serialization, not a JSON re-serialization:
        GET https://api.worldbank.org/v2/<lang>/indicator/<CODE>?downloadformat=csv
        (HTTP 200 application/zip; the 'en' archives were recorded 2026-11-11 in
        tests/ingest/fixtures/worldbank/, sha256-pinned by MANIFEST.json)

EXPORT LOCALE CONTRACT (strict, fail-closed): the channel exists under per-locale routes
(/v2/en/, /v2/es/, ...) whose archives carry localized identity markers. Which locales may be
used AT ALL is the exact allowlist `CSV_LANGUAGES` below; the caller picks ONE at construction
(`WorldBankVerifier(csv_language=...)`, default 'en' = the original behavior). Everything the
verifier accepts is then tied to that locale: the exact URL template, the localized Data Source
title row, and the ZIP member-name infix `DS2_<lang>_csv_v2_<rev>`. There is NO arbitrary
URL/locale input, NO automatic fallback or retry and NO request rewriting: a mismatch between
the chosen locale and the served archive (crossed locale, foreign member names, foreign title)
fails closed, and a language outside the allowlist fails at construction before any request.
Task 17A adds one reviewed extension: an optional per-indicator locale map
(`WorldBankVerifier(indicator_locales={<CODE>: <lang>})`), same allowlisted endpoints/parsers,
validated and copied at construction, with no automatic fallback between locales — an indicator
absent from the map simply uses the instance's csv_language.

Channel mechanics (from the archived bytes):
- The ZIP holds exactly THREE members: the main data CSV
  'API_<CODE>_DS2_<lang>_csv_v2_<rev>.csv', 'Metadata_Indicator_API_<CODE>_DS2_<lang>_csv_v2_
  <rev>.csv' and 'Metadata_Country_API_<CODE>_DS2_<lang>_csv_v2_<rev>.csv', ALL SHARING the
  same revision number <rev>; a split revision is identity drift. Any other member count/name,
  a path-traversal name ('..', absolute) or a member whose size disagrees with its declared
  entry fails closed; the archive is processed IN MEMORY (never extracted to the filesystem)
  with bounded member count/uncompressed size/reads (ZIP-bomb guards: MAX_MEMBERS,
  MAX_MEMBER_BYTES, MAX_TOTAL_BYTES; actual reads are capped and the realized length must equal
  the entry's).
- The main CSV starts with a metadata block: '"Data Source","<localized title>",', a blank
  row, '"Last Updated Date","<YYYY-MM-DD>",' (shape-validated ONLY; per the blind protocol it
  is never compared against collector metadata), another blank row, then the table header
  '"Country Name","Country Code","Indicator Name","Indicator Code","1960",...' (these labels,
  like the 'Data Source' and 'Last Updated Date' row keys, are NOT localized by this exporter)
  and one row per country/aggregate, all cells quoted, every row ending in a trailing comma
  (the header's final cell is empty accordingly). Year columns must be unique; rows must be
  unique per Country Code (+Indicator Code, which must equal the requested CODE on every row);
  duplicates or header drift fail closed. The per-row Indicator Name cell IS localized (e.g.
  'Crecimiento del PIB (% anual)'); only agreement on a single name across rows is asserted.
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
import decimal
import io
import json
import re
import zipfile

from ingest.http import Http
from ingest.verifiers import BlindItem, ItemResult, VerifierUnavailable

# The ONLY admitted export locales of the SAME publisher per-indicator CSV exporter:
# language -> (exact URL template, expected localized Data Source title of the archive).
# Extending this is an explicit, reviewed change — never a runtime parameter.
CSV_LANGUAGES: dict[str, tuple[str, str]] = {
    "en": ("https://api.worldbank.org/v2/en/indicator/{code}?downloadformat=csv",
           "World Development Indicators"),
    # 2026-11-12 f0nix recovery: the SAME exporter under /v2/es/ (title 'Indicadores del
    # desarrollo mundial', English column labels, '.'-decimal tokens byte-identical to the
    # JSON channel, 54/54 series matched exactly for both recovered indicators); genuine
    # ZIPs recorded in tests/ingest/fixtures/worldbank/csv-es-*.zip.
    "es": ("https://api.worldbank.org/v2/es/indicator/{code}?downloadformat=csv",
           "Indicadores del desarrollo mundial"),
}
CSV_URL = CSV_LANGUAGES["en"][0]  # the original English template (kept name)
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
_EXPONENT = re.compile(r"-?[0-9]+(\.[0-9]+)?E([+-][0-9]+)")
# |exponent| bound for the exponent rewrite: real WDI cells sit within about E-12..E+15, and an
# unbounded exponent ('1E+999999999', 12 bytes) would make the plain rewrite build a ~1 GB
# string. Larger exponents are refused as export drift (the item fails, never a silent pass).
MAX_EXPONENT = 400


def _plain(cell: str) -> str:
    """The CSV writes very small/large values in exponent form ('2.12913319746322E-06') where
    the API writes the plain decimal ('0.00000212913319746322'); found by the Task 21 census
    of every cell. Rewritten EXACTLY (Decimal, never float) into plain notation so the engine's
    exact-Decimal comparison applies; any other token is returned verbatim. ValueError for an
    exponent beyond +/-MAX_EXPONENT."""
    m = _EXPONENT.fullmatch(cell)
    if m is None:
        return cell
    if abs(int(m.group(2))) > MAX_EXPONENT:
        raise ValueError(f"World Bank CSV cell {cell[:40]!r} has an exponent beyond "
                         f"+/-{MAX_EXPONENT} (export drift; refused)")
    return format(decimal.Decimal(cell), "f")


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


def _member_patterns(code: str, language: str) -> tuple:
    """Exact full-name patterns of the THREE members of one locale's export: the main data CSV
    and the two metadata companions, each `..._DS2_<language>_csv_v2_<rev>.csv` with the
    revision number captured; the three revisions must be ONE (checked by _read_export). A
    member outside this exact identity — another locale, another exporter layout — is drift."""
    c, lang = re.escape(code), re.escape(language)
    return (re.compile(rf"API_{c}_DS2_{lang}_csv_v2_(\d+)\.csv"),
            re.compile(rf"Metadata_Indicator_API_{c}_DS2_{lang}_csv_v2_(\d+)\.csv"),
            re.compile(rf"Metadata_Country_API_{c}_DS2_{lang}_csv_v2_(\d+)\.csv"))


def _read_export(body: bytes, code: str, language: str, what: str) -> bytes:
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
        main_p, meta_i_p, meta_c_p = _member_patterns(code, language)
        main = meta_i = meta_c = None
        rev_m = rev_i = rev_c = None
        total = 0
        for info in infos:
            name = info.filename
            if "/" in name or "\\" in name or ".." in name or not name:
                raise ValueError(f"World Bank CSV export member name unsafe: {name!r}")
            total += info.file_size
            if total > MAX_TOTAL_BYTES:
                raise ValueError(f"World Bank CSV export for {what} exceeds the total size cap")
            m = main_p.fullmatch(name)
            if m:
                if main is not None:
                    raise ValueError(f"World Bank CSV export for {what} has ambiguous main "
                                     f"members: {z.namelist()!r}")
                main, rev_m = info, m.group(1)
                continue
            m = meta_i_p.fullmatch(name)
            if m:
                meta_i, rev_i = info, m.group(1)
                continue
            m = meta_c_p.fullmatch(name)
            if m:
                meta_c, rev_c = info, m.group(1)
                continue
            raise ValueError(f"World Bank CSV export for {what} carries an unexpected "
                             f"member {name!r} (identity drift: not the {code} DS2_{language} "
                             f"members)")
        if main is None or meta_i is None or meta_c is None:
            raise ValueError(f"World Bank CSV export for {what} misses the expected "
                             f"{code} DS2_{language} members: {z.namelist()!r}")
        if not rev_m == rev_i == rev_c:
            raise ValueError(f"World Bank CSV export for {what} members disagree on the "
                             f"revision ({rev_m!r}/{rev_i!r}/{rev_c!r}): identity drift")
        return _read_member(z, main, MAX_MEMBER_BYTES, what)


def _table(main: bytes, code: str, title: str, what: str) -> tuple[dict[str, list[str]], dict[str, int]]:
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
    if rows[0] != ["Data Source", title, ""]:
        raise ValueError(f"World Bank CSV export for {what} Data Source title of the chosen "
                         f"locale drifted (expected {title!r}): {rows[0]!r}")
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
    versioned envelope (exact ZIP bytes + final URL + actual HTTP status).

    csv_language: the ONE export locale this instance reads by default, from the exact
    CSV_LANGUAGES allowlist; the default 'en' is the original behavior. An unknown language is
    rejected HERE, at construction, before any request; a served archive that does not carry
    that locale's identity (URL/title/DS2_<lang> member names with one shared revision) fails
    closed — no fallback, no retry, no request rewriting.

    indicator_locales: optional EXPLICIT per-indicator overrides {WDI indicator code: locale}
    (Task 17A; the reviewed recovery mapping lives in ingest.operations). Both keys and values
    are validated at construction (indicator codes must match the WDI code shape, locales must
    be in CSV_LANGUAGES); the mapping is COPIED, so mutating the caller's dict afterwards can
    never change verification. An indicator not in the map uses csv_language. There is no
    automatic fallback between locales: the mapped locale's archive fails closed exactly like
    any other locale mismatch."""

    source_name = "worldbank"

    def __init__(self, csv_language: str = "en",
                 indicator_locales: dict[str, str] | None = None):
        if csv_language not in CSV_LANGUAGES:
            raise ValueError(f"WorldBankVerifier csv_language must be one of "
                             f"{sorted(CSV_LANGUAGES)}, got {csv_language!r} (the export "
                             f"locale is an exact allowlist; arbitrary URLs/locales are "
                             f"never accepted)")
        bad_codes = sorted(c for c in (indicator_locales or {})
                           if not _INDICATOR.fullmatch(c))
        bad_locales = sorted({lang for lang in (indicator_locales or {}).values()
                              if lang not in CSV_LANGUAGES})
        if bad_codes or bad_locales:
            raise ValueError(f"WorldBankVerifier indicator_locales must map WDI indicator "
                             f"codes to admitted locales {sorted(CSV_LANGUAGES)}; got "
                             f"malformed indicator codes {bad_codes} and/or unknown locales "
                             f"{bad_locales}")
        self.csv_language = csv_language
        self._indicator_locales = dict(indicator_locales or {})

    @property
    def indicator_locales(self) -> dict[str, str]:
        """A copy of the per-indicator locale overrides; mutating it changes nothing."""
        return dict(self._indicator_locales)

    def _channel(self, code: str) -> tuple[str, str, str]:
        """(URL template, localized Data Source title, locale) one indicator is read through."""
        lang = self._indicator_locales.get(code, self.csv_language)
        url, title = CSV_LANGUAGES[lang]
        return url, title, lang

    not_compared = {
        "unit": "the bulk CSV export has no machine-readable unit column (unit evidence is the "
                "indicator sourceNote prose; registry labels audited in "
                "tests/ingest/test_registry_worldbank_units.py)",
        "flag": "the bulk CSV export has no per-cell status or footnote surface"}

    def request_key(self, item: BlindItem):
        return _indicator_of(item.spec.native_code)[0]  # one ZIP per indicator: full history

    def reread(self, evidence: bytes, item: BlindItem) -> ItemResult:
        """Pure re-decision from the archived envelope: the locale is the one the recorded
        final URL names (exact CSV_LANGUAGES template), never this instance's configuration."""
        return self.reread_many(evidence, [item])[0]

    def reread_many(self, evidence: bytes, items: list[BlindItem]) -> list[ItemResult]:
        """reread of items sharing one envelope: each indicator's export is parsed once."""
        tables: dict[str, tuple] = {}
        out = []
        for item in items:
            code, _ = _indicator_of(item.spec.native_code)
            if code not in tables:
                tables[code] = self._archived_table(evidence, code, item.series_id)
            rows, ycol, url = tables[code]
            out.append(_result(item, rows, ycol, code, url, evidence))
        return out

    def _archived_table(self, evidence: bytes, code: str, what: str):
        doc = json.loads(evidence)
        if doc.get("schema") != EVIDENCE_SCHEMA or doc.get("version") != EVIDENCE_VERSION \
                or len(doc.get("responses") or []) != 1:
            raise ValueError("not a worldbank-csv-evidence v1 envelope of one response")
        rec = doc["responses"][0]
        if not 200 <= rec["status"] < 300:
            raise ValueError(f"archived response has HTTP status {rec['status']}")
        langs = [lang for lang, (url_t, _) in CSV_LANGUAGES.items()
                 if url_t.format(code=code) == rec["url"]]
        if len(langs) != 1:
            raise ValueError(f"archived URL {rec['url']!r} is not an admitted export of {code}")
        body = base64.b64decode(rec["body_base64"], validate=True)
        title = CSV_LANGUAGES[langs[0]][1]
        rows, ycol = _table(_read_export(body, code, langs[0], what), code, title, what)
        return rows, ycol, rec["url"]

    def check(self, items: list[BlindItem], http: Http) -> list[ItemResult]:
        # code -> (rows, year columns, final url, evidence envelope built ONCE per indicator)
        tables: dict[str, tuple[dict[str, list[str]], dict[str, int], str, bytes]] = {}
        results: list[ItemResult] = []
        for item in items:
            code, _ = _indicator_of(item.spec.native_code)
            if not _PERIOD.fullmatch(item.period):  # before any request
                raise ValueError(f"World Bank verifier accepts canonical yearly periods only, "
                                 f"got {item.period!r}")
            if code not in tables:
                url_t, title, lang = self._channel(code)
                r = http.get(url_t.format(code=code))
                if not 200 <= r.status < 300:
                    raise VerifierUnavailable(
                        f"World Bank CSV export for indicator {code} answered HTTP {r.status} "
                        f"(fail closed on every non-2xx)")
                rows, ycol = _table(_read_export(r.body, code, lang, item.series_id),
                                    code, title, item.series_id)
                tables[code] = (rows, ycol, r.url, _envelope(r.url, r.status, r.body))
            rows, ycol, url, evidence = tables[code]
            results.append(_result(item, rows, ycol, code, url, evidence))
        return results


def _result(item: BlindItem, rows: dict[str, list[str]], ycol: dict[str, int], code: str,
            url: str, evidence: bytes) -> ItemResult:
    """One item read from a parsed export table (shared by check and reread)."""
    _, iso3 = _indicator_of(item.spec.native_code)
    if not _PERIOD.fullmatch(item.period):
        raise ValueError(f"World Bank verifier accepts canonical yearly periods only, "
                         f"got {item.period!r}")
    if item.period not in ycol:
        raise ValueError(f"World Bank CSV export for {code} has no column for the "
                         f"requested period {item.period!r} (export drift)")
    row = rows.get(iso3)
    cell = row[ycol[item.period]] if row is not None else ""
    return ItemResult(series_id=item.series_id, period=item.period,
                      observed_text=_plain(cell) if cell != "" else None, evidence_url=url,
                      observed_decimal=".", observed_unit=None, observed_flag=None,
                      evidence=evidence)
