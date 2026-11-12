"""Independent verifier for OECD, spec 6b (Task 15 Part B):

    collector:  SDMX-JSON data 2.0 (Accept application/vnd.sdmx.data+json;version=2.0)
    verifier:   the SAME data API path but a genuinely different format family, keyless:
                GET https://sdmx.oecd.org/public/rest/data/<agency>,<dataflow>/<key>
                    ?format=csvfilewithlabels&dimensionAtObservation=AllDimensions
                    &startPeriod=<min sampled>&endPeriod=<max sampled>
                (application/vnd.sdmx.data+csv; labels=name; Task 15 evidence items 2,4,6,8,10,12,
                byte-identical sha256-pinned originals in tests/ingest/fixtures/oecd/verify/)

ONE bounded labelled-CSV response per series carries BOTH surfaces an item's decision needs:
the OBS_VALUE token per TIME_PERIOD and the unit/multiplier/status columns as code+label pairs.
The request window is the sampled items' min..max period; a requested period absent from the
rows returns observed_text=None (an honest 'not found' mismatch decided by ingest.verify) —
sparse samples never invent data and all-periods-present is never assumed.

Structure assertions are fail-closed, parsed by HEADER NAME, never column position (the
unemployment fixture puts BASE_PER before OBS_STATUS): exactly the 4 fixed STRUCTURE* /ACTION
columns, then one (code, label) column pair per pinned key segment (9 in the reviewed shape),
then TIME_PERIOD/OBS_VALUE pairs, then OBS_STATUS/UNIT_MULT/DECIMALS/BASE_PER pairs in any
order; anything else raises (duplicate header names, unknown columns, wrong width). Every row
must carry STRUCTURE=DATAFLOW, ACTION='I', the request-pinned STRUCTURE_ID
'<agency>:<dataflow>(<version>)', and dimension code cells equal to the registry key's pins
(payload identity, not URL trust; a row with drifted coordinates is a foreign series and
fails). TIME_PERIOD cells are canonical YYYY-MM, unique, and inside the requested window;
OBS_VALUE tokens are preserved VERBATIM as plain ASCII decimals (never float, never rounded:
the CSV trims trailing '.0' vs the JSON channel, e.g. '5.80'->'5.8'/'-6.0'->'-6'; exact-Decimal
comparison is engine policy in ingest.verify). UNIT_MULT must be '0' ('Units') matching
spec.multiplier 0 (any other multiplier is a wrong scale, never a conversion excuse); BASE_PER
code and label are blank in every reviewed response and must stay so; DECIMALS is shape-checked
display metadata, never used (CLI publishes 4-5 dp under DECIMALS=2).

Unit/flag come from PUBLISHER EVIDENCE through narrow reviewed maps, never echoed from the
registry: UNIT_MEASURE IX->'index (100=trend)', PB->'balance %', PT_LF_SUB->'%' (labels 'Index',
'Percentage balance', 'Percentage of labour force in the same subgroup' pinned) must equal the
registry unit; OBS_STATUS 'A' ('Normal value', the only code observed in the 77 reviewed
observations; the full codelist probe 404'd, discovery item 13) maps to flag 'normal', ANY
other code fails closed. FREQ 'M' ('Monthly') and ADJUSTMENT ('AA'/'Amplitude adjusted' ->
registry seasonal_adjustment unset, 'Y'/'Calendar and seasonally adjusted' -> the pinned
registry prose) are asserted against the spec the same way.

EVIDENCE (Ruling R/G7): every ItemResult carries one versioned JSON envelope (schema
'oecd-csv-evidence', version 1) bundling the exact wire record — final URL, actual HTTP status
and the full CSV body base64-encoded — byte-for-byte recoverable from the raw store with no
HTTP; `read_csv_evidence` re-reads the archived bytes and recovers values AND units AND flags.

INDEPENDENCE: this module shares NO code with the collector (register_verifier's static
allowlist plus assert_verifier_independent's runtime subprocess). The native-code shape rule
and the metadata maps are DUPLICATED ON PURPOSE: if the two copies ever disagree, verification
fails loudly. No Accept/publisher headers are sent; pacing belongs to the injected Http client
(the verifier adds no timing policy of its own).

Registration: the Task 17 CLI calls register_verifier(OecdVerifier()).
"""
import base64
import csv
import io
import json
import re

from ingest.http import Http, HttpResult
from ingest.models import SeriesSpec
from ingest.verifiers import BlindItem, ItemResult

API_BASE = "https://sdmx.oecd.org/public/rest"
EVIDENCE_SCHEMA = "oecd-csv-evidence"
EVIDENCE_VERSION = 1

_ID = r"[A-Z0-9_]+(?:\.[A-Z0-9_]+)*"
_AGENCY = re.compile(_ID)
_DATAFLOW = re.compile(_ID + "@" + _ID)
_PIN = re.compile(r"[A-Z0-9_]+")
_PERIOD = re.compile(r"[0-9]{4}-(0[1-9]|1[0-2])")  # canonical YYYY-MM, ASCII only
_VALUE = re.compile(r"[+-]?[0-9]+(?:\.[0-9]+)?")  # plain ASCII decimal token, verbatim
_PINS = 9  # every reviewed series key pins exactly 9 dimension segments
_FIXED_HEADER = ("STRUCTURE", "STRUCTURE_ID", "STRUCTURE_NAME", "ACTION")
# pinned (code column, label column) pairs of the reviewed shape; TIME_PERIOD/OBS_VALUE sit
# between the dimension pairs and the remaining attribute pairs in both evidence families.
_ATTR_LABELS = {"TIME_PERIOD": "Time period", "OBS_VALUE": "Observation value",
                "OBS_STATUS": "Observation status", "UNIT_MULT": "Unit multiplier",
                "DECIMALS": "Decimals", "BASE_PER": "Base period"}
_REMAINING = ("OBS_STATUS", "UNIT_MULT", "DECIMALS", "BASE_PER")  # any order (evidence differs)

# DUPLICATES of the reviewed registry/publisher pairings, ON PURPOSE (see module docstring);
# evidence: Task 15 items 2,4,6,8,10,12, the only code/label pairs in the six originals.
_FREQ = {"M": "Monthly"}
_OBS_STATUS = {"A": ("Normal value", "normal")}  # other codes fail closed (codelist 404, it.13)
_UNIT_MEASURE = {"IX": ("Index", "index (100=trend)"),
                 "PB": ("Percentage balance", "balance %"),
                 "PT_LF_SUB": ("Percentage of labour force in the same subgroup", "%")}
_ADJUSTMENT = {"AA": ("Amplitude adjusted", None),
               "Y": ("Calendar and seasonally adjusted", "Calendar and seasonally adjusted")}
_UNIT_MULT = {"0": "Units"}
_DECIMALS = {"1": "One", "2": "Two"}
_REQUEST_PARAMS = {"format": "csvfilewithlabels", "dimensionAtObservation": "AllDimensions"}


def _native(code: str | None) -> tuple[str, str, list[str]]:
    """'<agency>,<dataflow>/<9 dot-joined pins>' -> (agency, dataflow, pins). DUPLICATE of the
    collector's shape rule, ON PURPOSE: a disagreement between the two copies is drift and
    raises here instead of passing verification."""
    if not isinstance(code, str):
        raise ValueError(f"OECD series carries no native_code: {code!r}")
    agency, sep1, rest = code.partition(",")
    dataflow, sep2, key = rest.partition("/")
    pins = key.split(".")
    if not sep1 or not sep2 or not _AGENCY.fullmatch(agency) \
            or not _DATAFLOW.fullmatch(dataflow) or len(pins) != _PINS \
            or any(not _PIN.fullmatch(p) for p in pins):
        raise ValueError(f"OECD native_code must be '<agency>,<dataflow>/<{_PINS} dot-joined "
                         f"pinned codes>', got {code!r}")
    return agency, dataflow, pins


def _window(name: str, value: str) -> str:
    if not isinstance(value, str) or not _PERIOD.fullmatch(value):
        raise ValueError(f"OECD {name} must be a canonical YYYY-MM literal, got {value!r}")
    return value


def _header(header: list[str], what: str) -> dict:
    """Column layout by NAME -> {"dims": [(code_ix, label_ix)], attr: (code_ix, label_ix)};
    raises on duplicate/unknown/drifted columns. Positions of the attribute pairs after
    TIME_PERIOD/OBS_VALUE are NOT fixed (item 12 puts BASE_PER before OBS_STATUS)."""
    if header[:4] != list(_FIXED_HEADER):
        raise ValueError(f"OECD {what} header does not start with {_FIXED_HEADER}: {header!r}")
    if len(set(header)) != len(header):
        raise ValueError(f"OECD {what} has duplicate header names: {header!r}")
    i, dims, rest = 4, [], len(header)
    while i < rest and header[i] != "TIME_PERIOD":
        if not _PIN.fullmatch(header[i]) or header[i] in _ATTR_LABELS or \
                header[i] in _FIXED_HEADER:
            raise ValueError(f"OECD {what} unknown column {header[i]!r}")
        if i + 1 >= rest or not header[i + 1] or _PIN.fullmatch(header[i + 1]):
            raise ValueError(f"OECD {what} dimension {header[i]!r} lacks its label column")
        dims.append((i, i + 1))
        i += 2
    if len(dims) != _PINS:
        raise ValueError(f"OECD {what} carries {len(dims)} dimension pairs, need {_PINS} "
                         "(code+label per pinned key segment; unreviewed shape, fail closed)")
    ix: dict = {"dims": dims}
    for name in ("TIME_PERIOD", "OBS_VALUE"):
        if i + 1 >= rest or header[i] != name or header[i + 1] != _ATTR_LABELS[name]:
            raise ValueError(f"OECD {what} expects the {name}/{_ATTR_LABELS[name]!r} pair after "
                             f"the dimensions: {header[i:i + 2]!r}")
        ix[name] = (i, i + 1)
        i += 2
    while i < rest:
        name = header[i]
        if name not in _REMAINING or name in ix or i + 1 >= rest \
                or header[i + 1] != _ATTR_LABELS[name]:
            raise ValueError(f"OECD {what} unknown column {name!r} (need one of "
                             f"{_REMAINING} with its pinned label)")
        ix[name] = (i, i + 1)
        i += 2
    if any(name not in ix for name in _REMAINING):
        raise ValueError(f"OECD {what} header is missing columns: "
                         f"{sorted(set(_REMAINING) - set(ix))}")
    return ix


def read_csv_evidence(body: bytes, native_code: str | None, spec: SeriesSpec, *,
                      start: str, end: str) -> tuple[str, dict[str, tuple[str, str]]]:
    """One bounded csvfilewithlabels response for ONE pinned series -> (observed unit prose,
    {canonical period: (exact OBS_VALUE token, registry flag)}), strictly fail-closed per the
    module docstring. This same function is the OFFLINE replay path for archived evidence
    bytes (no HTTP); start/end are a containment constraint on the decoded periods."""
    agency, dataflow, pins = _native(native_code)
    start, end = _window("start", start), _window("end", end)
    if start > end:
        raise ValueError(f"OECD window is inverted: {start} > {end}")
    what = f"csvfilewithlabels {native_code}"
    if not isinstance(body, bytes) or not body.strip():
        raise ValueError(f"OECD {what} answered a blank body (fail closed)")
    head = body.lstrip()[:1]
    if head == b"<":
        raise ValueError(f"OECD {what} answered HTML/markup, not CSV: {body[:80]!r}")
    try:
        text = body.decode("utf-8", errors="strict")
    except UnicodeDecodeError as e:
        raise ValueError(f"OECD {what} is not UTF-8: {e}") from e
    rows = list(csv.reader(io.StringIO(text, newline="")))
    if len(rows) < 2:
        raise ValueError(f"OECD {what} carries no data rows")
    ix = _header(rows[0], what)
    struct_id = re.compile(re.escape(agency) + ":" + re.escape(dataflow)
                           + r"\([0-9]+(?:\.[0-9]+)*\)")
    dim_codes = [c for c, _ in ix["dims"]]
    dim_labels = [c for _, c in ix["dims"]]
    um = um_label = adj = adj_label = fr = fr_label = -1
    for name, (c, lb) in zip([rows[0][c] for c, _ in ix["dims"]], ix["dims"]):
        if name == "UNIT_MEASURE":
            um, um_label = c, lb
        elif name == "ADJUSTMENT":
            adj, adj_label = c, lb
        elif name == "FREQ":
            fr, fr_label = c, lb
    if min(um, adj, fr) < 0:
        raise ValueError(f"OECD {what} header lacks the UNIT_MEASURE/ADJUSTMENT/FREQ "
                         "dimensions (unreviewed shape, fail closed)")
    unit = ""
    values: dict[str, tuple[str, str]] = {}
    for n, row in enumerate(rows[1:], 2):
        if len(row) != len(rows[0]):
            raise ValueError(f"OECD {what} row {n} width {len(row)} != header "
                             f"{len(rows[0])} (malformed width)")
        if row[0] != "DATAFLOW":
            raise ValueError(f"OECD {what} row {n} STRUCTURE {row[0]!r} != 'DATAFLOW'")
        if not struct_id.fullmatch(row[1]):
            raise ValueError(f"OECD {what} STRUCTURE_ID {row[1]!r} is not the requested "
                             f"'{agency}:{dataflow}(<version>)' (dataflow identity drift)")
        if not row[2]:
            raise ValueError(f"OECD {what} row {n} carries a blank STRUCTURE_NAME")
        if row[3] != "I":
            raise ValueError(f"OECD {what} row {n} ACTION {row[3]!r} != 'I'")
        got = tuple(row[c] for c in dim_codes)
        if got != tuple(pins):
            raise ValueError(f"OECD {what} row {n} coordinate {got} != the pinned key "
                             f"{tuple(pins)} (foreign series or identity drift)")
        if any(not row[c] for c in dim_labels):
            raise ValueError(f"OECD {what} row {n} carries a blank dimension label")
        c, lb = ix["TIME_PERIOD"]
        period = row[c]
        if not _PERIOD.fullmatch(period):
            raise ValueError(f"OECD {what} TIME_PERIOD {period!r} is not canonical YYYY-MM")
        if row[lb]:
            raise ValueError(f"OECD {what} TIME_PERIOD label {row[lb]!r} must stay blank "
                             "(labelled CSV leaves it empty in the reviewed shape)")
        if period in values:
            raise ValueError(f"OECD {what} duplicate period {period}")
        if not start <= period <= end:
            raise ValueError(f"OECD {what} row period {period} outside the requested window "
                             f"{start}..{end} (unrequested out-of-window row, fail closed)")
        c, lb = ix["OBS_VALUE"]
        token = row[c]
        if not _VALUE.fullmatch(token):
            raise ValueError(f"OECD {what} OBS_VALUE {token!r} is not a plain ASCII decimal "
                             "token (blank/grouped/exponent cells are unreviewed, fail closed)")
        if row[lb]:
            raise ValueError(f"OECD {what} OBS_VALUE label {row[lb]!r} must stay blank")
        c, lb = ix["OBS_STATUS"]
        flag = _OBS_STATUS.get(row[c])
        if flag is None or row[lb] != flag[0]:
            raise ValueError(f"OECD {what} OBS_STATUS {row[c]!r} label {row[lb]!r}: only 'A' "
                             "('Normal value') is reviewed; fail closed, never guess a status "
                             "(discovery item 13: full codelist not enumerable)")
        c, lb = ix["UNIT_MULT"]
        if _UNIT_MULT.get(row[c]) != row[lb] or not row[lb]:
            raise ValueError(f"OECD {what} UNIT_MULT {row[c]!r} label {row[lb]!r} is not the "
                             "reviewed '0'/'Units' pair")
        if row[c] != "0" or spec.multiplier != 0:
            raise ValueError(f"OECD {what} UNIT_MULT {row[c]!r} vs registry multiplier "
                             f"{spec.multiplier!r}: any non-zero multiplier is a wrong scale")
        c, lb = ix["DECIMALS"]
        if _DECIMALS.get(row[c]) != row[lb] or not row[lb]:
            raise ValueError(f"OECD {what} DECIMALS {row[c]!r} label {row[lb]!r} unreviewed "
                             "(display metadata, never used; shape is still pinned)")
        c, lb = ix["BASE_PER"]
        if row[c] or row[lb]:
            raise ValueError(f"OECD {what} BASE_PER {row[c]!r}/{row[lb]!r} not blank: an "
                             "unreviewed base period, no base year is ever invented")
        label = _UNIT_MEASURE.get(row[um])
        if label is None or row[um_label] != label[0]:
            raise ValueError(f"OECD {what} UNIT_MEASURE {row[um]!r} label {row[um_label]!r} "
                             "is unreviewed (fail closed)")
        unit = label[1]
        if unit != spec.unit:
            raise ValueError(f"{spec.id}: publisher UNIT_MEASURE {row[um]!r} maps to {unit!r} "
                             f"!= registry unit {spec.unit!r} (asserted, never echoed)")
        adj_pair = _ADJUSTMENT.get(row[adj])
        if adj_pair is None or row[adj_label] != adj_pair[0]:
            raise ValueError(f"OECD {what} ADJUSTMENT {row[adj]!r} label {row[adj_label]!r} "
                             "is unreviewed")
        if adj_pair[1] != spec.seasonal_adjustment:
            raise ValueError(f"{spec.id}: publisher ADJUSTMENT {row[adj]!r} expects registry "
                             f"seasonal_adjustment {adj_pair[1]!r}, got "
                             f"{spec.seasonal_adjustment!r} (adjustment drift)")
        if _FREQ.get(row[fr]) != row[fr_label] or not row[fr_label]:
            raise ValueError(f"OECD {what} FREQ {row[fr]!r} label {row[fr_label]!r} unreviewed")
        if row[fr] != spec.frequency:
            raise ValueError(f"{spec.id}: publisher FREQ {row[fr]!r} != registry frequency "
                             f"{spec.frequency!r}")
        values[period] = (token, flag[1])
    return unit, values


def _envelope(r: HttpResult) -> bytes:
    """The item's evidence: one versioned JSON envelope (schema 'oecd-csv-evidence', v1)
    bundling the exact wire record of the bounded CSV response — final URL, actual HTTP status
    and the full body base64-encoded (byte-for-byte recoverable from the raw store with no
    HTTP; metadata AND values come from this one response, so one record carries both)."""
    doc = {"schema": EVIDENCE_SCHEMA, "version": EVIDENCE_VERSION,
           "csv": {"url": r.url, "status": r.status,
                   "body_b64": base64.b64encode(r.body).decode("ascii")}}
    return json.dumps(doc, ensure_ascii=True, separators=(",", ":")).encode("ascii")


class OecdVerifier:
    """See the module docstring. ONE bounded csvfilewithlabels CSV fetch per unique series per
    check() call (window = the sampled items' min..max period; the same response is the value
    source AND the unit/flag source); every ItemResult carries the versioned evidence envelope,
    observed_unit translated from the publisher UNIT_MEASURE code, observed_flag from the
    publisher OBS_STATUS code ('A' -> 'normal'), observed_decimal '.'. A period absent from the
    response yields observed_text=None (honest 'not found', decided by ingest.verify)."""
    source_name = "oecd"

    def check(self, items: list[BlindItem], http: Http) -> list[ItemResult]:
        groups: dict[str, list[BlindItem]] = {}
        for item in items:
            nc = item.spec.native_code
            _native(nc)  # fail fast on a malformed registry identity
            if nc not in groups:
                groups[nc] = []
            groups[nc].append(item)
        pages: dict[str, tuple] = {}
        for nc, group in groups.items():
            start = min(i.period for i in group)
            end = max(i.period for i in group)
            params = {**_REQUEST_PARAMS, "startPeriod": _window("startPeriod", start),
                      "endPeriod": _window("endPeriod", end)}
            r = http.get(f"{API_BASE}/data/{nc}", params=params)
            if not 200 <= r.status < 300:
                raise ValueError(f"OECD csvfilewithlabels for {nc} answered HTTP {r.status}")
            pages[nc] = (r, read_csv_evidence(r.body, nc, group[0].spec,
                                              start=params["startPeriod"],
                                              end=params["endPeriod"]))
        results = []
        for item in items:
            r, (unit, values) = pages[item.spec.native_code]
            got = values.get(item.period)
            results.append(ItemResult(
                series_id=item.series_id, period=item.period,
                observed_text=got[0] if got else None,
                evidence_url=r.url, observed_decimal=".", observed_unit=unit,
                observed_flag=got[1] if got else None, evidence=_envelope(r)))
        return results
