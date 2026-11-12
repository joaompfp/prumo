"""Independent verifier for the E-REDES Open Data Portal (spec 6b):

    collector: OpenDataSoft explore v2.1 JSON records API
        e-redes.opendatasoft.com/api/explore/v2.1/catalog/datasets/<dataset>/records?where=...
    verifier:  the same portal's exports service - a DIFFERENT endpoint AND a different (CSV
        table) serialization of the same published data (the REN/BPstat precedent):
        GET .../datasets/<dataset>/exports/csv?lang=pt&timezone=UTC
            &where=datahora >= "<day>" AND datahora < "<day + 1>"
        ONE export per SAMPLED UTC day of the sample (Task 17B: a min..max span query is
        seed-dependent and can never match an exact recorded bundle under a fresh sample),
        plus .../datasets/<dataset> (metadata - the unit evidence: field labels '(kWh)')

Channel mechanics (genuine recorded fixtures tests/ingest/fixtures/eredes/, 2026-11-12):
- exports/csv answers UTF-8-BOM, ';'-separated, CRLF, header
  'datahora;dia;mes;ano;date;time;dgm;pre;total', ascending rows, full-precision plain
  decimals, datahora in the canonical UTC spelling when timezone=UTC is requested. All 288
  tokens of the recorded one-day window are byte-identical to the JSON channel (checked at
  recording time, MANIFEST.json). The where clause is honored (the archive is windowed).
- dia/mes/ano/date/time are the publisher's LISBON-LOCAL wall-time echo of the period (WEST =
  UTC+1 in summer: the genuine summer archive carries date 2026-04-02 / time 00:45 at
  2026-04-01T23:45:00+00:00). They are validated for canonical shape and internal consistency
  (date == ano-mes-dia) but NEVER equated with the authoritative UTC datahora of column 0, and
  no local offset is recomputed here.
- The dataset has NO per-record status/quality surface on either channel -> observed_flag is
  honestly None. Units come from the metadata field labels ('Market (kWh)' etc.), so BOTH the
  deciding CSV and the metadata response are archived per item.

EVIDENCE (Ruling R/AC/G7): ItemResult.evidence is the versioned JSON envelope
'eredes-csv-evidence' v1 {"responses": [{"url", "status", "body_base64"}, ...]} holding the
item's OWN DAY deciding CSV response AND the unit metadata response - exact bytes, FINAL urls
and ACTUAL HTTP statuses, all byte-for-byte recoverable from the raw store without HTTP;
evidence_url is that day's CSV final URL. The envelope shape is E-REDES-local to this module
and unchanged from the one-day form, so previously archived one-day evidence still replays.

INDEPENDENCE: this module shares NO code with the collector (enforced by register_verifier and
assert_verifier_independent); the dataset/field/label constants are DUPLICATED ON PURPOSE - if
the two copies ever disagree, verification fails loudly. Items whose period is missing from the
export answer observed_text=None (a mismatch), never an invented value.
"""
import base64
import csv
import io
import json
import re
from datetime import date, timedelta

from ingest.http import Http
from ingest.verifiers import BlindItem, ItemResult

API_BASE = "https://e-redes.opendatasoft.com/api/explore/v2.1/catalog/datasets"
PRODUCTION_DATASET = "energia-produzida-total-nacional"
FIELDS = frozenset({"dgm", "pre", "total"})  # DUPLICATE of the collector's map, ON PURPOSE
EXPECTED_HEADER = ["datahora", "dia", "mes", "ano", "date", "time", "dgm", "pre", "total"]
EVIDENCE_SCHEMA = "eredes-csv-evidence"
EVIDENCE_VERSION = 1

_NATIVE_CODE = re.compile(r"([a-z0-9][a-z0-9-]*):(dgm|pre|total)$")
_PERIOD = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\+00:00")
_NUMBER = re.compile(r"-?[0-9]+(\.[0-9]+)?")  # observed CSV token grammar (decimal '.')
_LABEL_UNIT = re.compile(r"[^(]*\(([^()]+)\)$")
_WALL_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_WALL_TIME = re.compile(r"([01][0-9]|2[0-3]):[0-5][0-9]")


def _wall_cells(row: list[str]) -> None:
    """dia/mes/ano/date/time CSV cells are the publisher's LISBON-LOCAL wall-time echo of the
    period: canonical shapes and internal consistency (date == ano-mes-dia) only, NEVER equated
    with the authoritative UTC datahora of column 0 (WEST summer shows UTC+1, so a 23:45 UTC
    row legitimately carries the next local date and 00:45). DUPLICATE shape rules of the
    collector's, ON PURPOSE."""
    d = row[4]
    if _WALL_DATE.fullmatch(d) is None:
        raise ValueError(f"E-REDES CSV date cell is not canonical YYYY-MM-DD: {row!r}")
    try:
        dd = date.fromisoformat(d)
    except ValueError as e:
        raise ValueError(f"E-REDES CSV date cell is not a real Gregorian date: {row!r}") from e
    if (row[3] != f"{dd.year:04d}" or row[2] != f"{dd.month:02d}"
            or row[1] != f"{dd.day:02d}"):
        raise ValueError(f"E-REDES CSV row's dia/mes/ano cells disagree with date {d!r}: "
                         f"{row!r}")
    if _WALL_TIME.fullmatch(row[5]) is None:
        raise ValueError(f"E-REDES CSV time cell is not canonical HH:MM: {row!r}")


def _dataset_and_field(code) -> tuple[str, str]:
    """'<dataset>:<field>' -> (dataset, field). DUPLICATE of the collector's, ON PURPOSE."""
    m = _NATIVE_CODE.fullmatch(code or "")
    if m is None or m.group(1) != PRODUCTION_DATASET:
        raise ValueError(f"unreviewed E-REDES native_code {code!r}")
    return m.group(1), m.group(2)


def _envelope(records: list[dict]) -> bytes:
    """The evidence bytes of one item: the deciding CSV response AND the unit metadata
    response - final URLs, ACTUAL HTTP statuses, raw bodies base64 (byte-for-byte recoverable
    offline)."""
    doc = {"schema": EVIDENCE_SCHEMA, "version": EVIDENCE_VERSION,
           "responses": [{"url": r["url"], "status": r["status"],
                          "body_base64": base64.b64encode(r["body"]).decode("ascii")}
                         for r in records]}
    return json.dumps(doc, ensure_ascii=True, separators=(",", ":")).encode("ascii")


def _csv_rows(body: bytes, what: str) -> list[list[str]]:
    head = body[:64].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    if head.startswith(b"<"):
        raise ValueError(f"E-REDES CSV export for {what} answered markup: {body[:80]!r}")
    try:
        text = body.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ValueError(f"E-REDES CSV export for {what} is not UTF-8: {e}") from e
    try:
        rows = list(csv.reader(io.StringIO(text, newline=""), delimiter=";", strict=True))
    except csv.Error as e:
        raise ValueError(f"E-REDES CSV export for {what} is malformed CSV: {e}") from e
    blank = [not row or all(not c.strip() for c in row) for row in rows]
    if any(blank):
        first = blank.index(True)
        if not all(blank[first:]):
            raise ValueError(f"E-REDES CSV export for {what} has an interior blank row")
    rows = [row for row, b in zip(rows, blank) if not b]
    if not rows or rows[0] != EXPECTED_HEADER:
        raise ValueError(f"E-REDES CSV export header drifted: {rows[0] if rows else None!r}")
    return rows[1:]


class EredesVerifier:
    """One CSV export per (dataset, SAMPLED UTC day) + one metadata response per check; the
    period is read FROM THE CSV's own datahora tokens (string equality with the canonical UTC
    period, never echoed from the request), observed_unit from the metadata field label,
    observed_flag honestly None. Each item's result maps back to its OWN day's response."""

    source_name = "eredes"

    def check(self, items: list[BlindItem], http: Http) -> list[ItemResult]:
        cache: dict[tuple, tuple[bytes, str, int]] = {}

        def get(url: str, params: dict | None) -> tuple[bytes, str, int]:
            key = (url, tuple(sorted((params or {}).items())))
            if key not in cache:
                r = http.get(url, params=params)
                if not 200 <= r.status < 300:
                    raise ValueError(f"E-REDES verifier request for {url!r} answered HTTP "
                                     f"{r.status} (fail closed on every non-2xx)")
                cache[key] = (r.body, r.url, r.status)
            return cache[key]

        results: list[ItemResult] = []
        by_dataset: dict[str, list[BlindItem]] = {}
        for item in items:
            dataset, _field = _dataset_and_field(item.spec.native_code)
            if _PERIOD.fullmatch(item.period) is None:
                raise ValueError(f"E-REDES verifier reviewed canonical PT15M periods only, "
                                 f"got {item.period!r}")
            date.fromisoformat(item.period[:10])  # raises on a non-Gregorian date
            by_dataset.setdefault(dataset, []).append(item)

        state: dict[str, dict] = {}
        for dataset, its in by_dataset.items():
            days = sorted({i.period[:10] for i in its})
            meta_body, meta_url, meta_status = get(f"{API_BASE}/{dataset}", None)
            meta = json.loads(meta_body)  # strict metadata parse (identity + labels)
            if meta.get("dataset_id") != dataset:
                raise ValueError(f"E-REDES metadata dataset_id drifted from {dataset!r}")
            labels = {}
            for f in meta.get("fields", []):
                if isinstance(f, dict) and f.get("name") in FIELDS:
                    m = _LABEL_UNIT.fullmatch(str(f.get("label", "")))
                    if m is None:
                        raise ValueError(f"E-REDES field {f.get('name')!r} label is not "
                                         f"'<name> (<unit>)': {f.get('label')!r}")
                    labels[f["name"]] = (m.group(1), f.get("type"))
            day_state: dict[str, dict] = {}
            seen_ts: set[str] = set()  # a datahora seen in ANY of this dataset's day files
            for day_s in days:
                day = date.fromisoformat(day_s)
                where = f'datahora >= "{day.isoformat()}" AND ' \
                        f'datahora < "{(day + timedelta(days=1)).isoformat()}"'
                csv_body, csv_url, csv_status = get(f"{API_BASE}/{dataset}/exports/csv",
                                                    {"lang": "pt", "timezone": "UTC",
                                                     "where": where})
                by_ts = {}
                for row in _csv_rows(csv_body, dataset):
                    if len(row) != len(EXPECTED_HEADER):
                        raise ValueError(f"E-REDES CSV row has {len(row)} cells: {row!r}")
                    ts = row[0]
                    if _PERIOD.fullmatch(ts) is None:
                        raise ValueError(f"E-REDES CSV datahora is not the canonical UTC "
                                         f"spelling: {ts!r}")
                    _wall_cells(row)
                    if ts in seen_ts:
                        raise ValueError(f"E-REDES CSV export repeats datahora {ts!r}")
                    seen_ts.add(ts)
                    if ts[:10] != day.isoformat():
                        raise ValueError(f"E-REDES CSV row {ts!r} outside the requested day "
                                         f"window {where!r}")
                    by_ts[ts] = row
                day_state[day.isoformat()] = {
                    "by_ts": by_ts, "csv_url": csv_url,
                    "evidence": _envelope([
                        {"url": csv_url, "status": csv_status, "body": csv_body},
                        {"url": meta_url, "status": meta_status, "body": meta_body}])}
            state[dataset] = {"labels": labels, "days": day_state}

        for item in items:
            dataset, field = _dataset_and_field(item.spec.native_code)
            st = state[dataset]
            if field not in st["labels"] or st["labels"][field][1] != "double":
                raise ValueError(f"E-REDES metadata field {field!r} missing or not double")
            unit = st["labels"][field][0]
            d = st["days"][item.period[:10]]  # every sampled day was fetched above
            row = d["by_ts"].get(item.period)
            if row is None:
                results.append(ItemResult(item.series_id, item.period, None,
                                          d["csv_url"], ".", unit, None, d["evidence"]))
                continue
            token = row[EXPECTED_HEADER.index(field)].strip()
            if _NUMBER.fullmatch(token) is None:
                raise ValueError(f"E-REDES CSV {field} @ {item.period} is not a number "
                                 f"token: {row[EXPECTED_HEADER.index(field)]!r}")
            results.append(ItemResult(item.series_id, item.period, token, d["csv_url"],
                                      ".", unit, None, d["evidence"]))
        return results
