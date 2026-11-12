"""OECD SDMX data API source adapter: the SDMX-JSON data 2.0 channel.

    GET https://sdmx.oecd.org/public/rest/data/<agency>,<dataflow>/<key>
        [?startPeriod=YYYY-MM&endPeriod=YYYY-MM]
    Accept: application/vnd.sdmx.data+json;version=2.0

Recorded evidence in tests/ingest/fixtures/oecd/ (2026-11-12 f3nix, sha256-pinned by
MANIFEST.json; byte-identical to docs/superpowers/handoff/evidence/task-15-oecd/discovery/
items 1,3,5,7,9,11): six active core monthly PT series — oecd.cli.PT (DF_CLI), the four DF_BTS
business-tendency balances and oecd.unemp_m.PT (DF_IALFS_UNE_M, cross_check of
unemployment_rate.PT.M, INE primary). Note the identity trap: oecd.cli.PT is MEASURE=BCICP
(composite business confidence), NOT the dataflow's DEFAULT annotation MEASURE=LI (headline
composite leading indicator) — keys are pinned in full and never defaulted
(registry/mappings-oecd.md).

Registry contract (`SeriesSpec.native_code`): '<agency>,<dataflow>/<key>', exactly the probed
publisher request identity — dataflow carries its DSD ('DSD_STES@DF_CLI'), the key is the
dot-joined pinned dimension codes (one segment per series dimension, e.g.
'PRT.M.BCICP.IX._Z.AA.IX._Z.H'; parse never reorders it). `SeriesSpec.url` is the canonical
request address API_BASE/data/<native_code>. `SeriesSpec.multiplier` records the observed
UNIT_MULT=0; the registry unit remains authoritative prose ('index (100=trend)',
'balance %', '%') because the channel exposes codes/labels, not that prose
(registry/mappings-oecd.md derives it from publisher metadata).

Fetch strategy: ONE request per series native_code, sorted; no pagination (the publisher
answers the whole requested window in one body in evidence; a multiple-dataSets/series payload
fails closed in parse rather than being flattened). The DEFAULT run requests FULL history (no
params); OecdSource(start_period='YYYY-MM', end_period='YYYY-MM') bounds the window for bounded
live/fixture runs without silently truncating production history.

Response shape (fail-closed, SDMX-JSON data 2.0): {meta, data, errors} with errors == [];
meta.schema pinned to the sdmx-json-data-schema 2.0.0 URL. data carries exactly one dataSet
(action 'Information', genuine numeric structure index 0, datastructure URN pinned to the
request agency/DSD) and one structure whose dataflow URN
'urn:sdmx:org.sdmx.infomodel.datastructure.Dataflow=<agency>:<dataflow>(<version>)' must match
the REQUEST identity. dimensions.series are keyed by GENUINE NUMERIC keyPosition 0..n-1 (quoted
aliases rejected) with exactly one pinned value each; the value codes must equal the requested
key segments in order (payload identity, not URL trust). dimensions.observation[0] is
TIME_PERIOD; its values array is UNSORTED in evidence (index->period mapping ALWAYS goes
through values[i].id, never a sorted zip; duplicate/malformed period ids fail). Series entries
index dimensions by canonical ASCII decimal segments ('0:0:...:0'; '00', Unicode digit aliases,
out-of-range indices and extra series keys all raise). Observations are sparse
'"<canonical decimal index>": [<JSON number value | null>, <numeric OBS_STATUS attr index>]':
value tokens are preserved VERBATIM via json.loads(parse_int/parse_float tagging JSON numbers
as _Num — a quoted numeric string is a type flip and raises); null stays value_raw=None
(quarantined non_numeric downstream, never zero-filled). Series attributes must resolve to
UNIT_MULT=0 ('Units') — any other multiplier is a wrong scale, never a conversion excuse — and
DECIMALS is a display hint only (CLI publishes 4-5 dp despite DECIMALS=2). OBS_STATUS is an
observation attribute whose codelist was NOT enumerable (discovery item 13, HTTP 404): only 'A'
('Normal value') is reviewed and mapped to flag_raw='normal'; ANY other code fails closed,
referenced or not.

Archived identity (offline parse): url/params are the identity — netloc sdmx.oecd.org, path
/public/rest/data/<agency>,<dataflow>/<key>, params keys subset of {startPeriod, endPeriod}
(canonical YYYY-MM literals only), the URL query a strict projection of the archived params (no
unreviewed, duplicated or contradicting keys). A declared archived window is a CONTAINMENT
constraint on the decoded periods (a truncated/rebound archive fails closed instead of parsing
as a different window). RawRow.response_index points at the row's own response. parse() needs
no HTTP or DB.
"""
import json
import re
from collections.abc import Iterator
from urllib.parse import parse_qsl, urlsplit

from ingest.http import Http
from ingest.models import SeriesSpec
from ingest.sources import RawResponse
from ingest.validate import RawRow

API_BASE = "https://sdmx.oecd.org/public/rest"
ACCEPT_SDMX_JSON = "application/vnd.sdmx.data+json;version=2.0"
SCHEMA_URL = ("https://raw.githubusercontent.com/sdmx-twg/sdmx-json/master/data-message/"
              "tools/schemas/2.0.0/sdmx-json-data-schema.json")
ACTION_INFORMATION = "Information"

_ID = r"[A-Z0-9_]+(?:\.[A-Z0-9_]+)*"
_AGENCY = re.compile(_ID)
_DATAFLOW = re.compile(rf"{_ID}@{_ID}")
_KEY = re.compile(rf"{_ID}(?:\.{_ID})*")
_PERIOD = re.compile(r"[0-9]{4}-(0[1-9]|1[0-2])")  # canonical YYYY-MM; ASCII classes only
_INDEX = re.compile(r"0|[1-9][0-9]*")  # canonical ASCII decimal: '00' and aliases rejected
_DIM_VALUE_ID = re.compile(r"[A-Z0-9_]+")
_TS = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}")
_PREPARED = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")
_DG_KEY = re.compile(r"(?:0|[1-9][0-9]*|~)(?::(?:0|[1-9][0-9]*|~))*")
_URN_DATAFLOW = "urn:sdmx:org.sdmx.infomodel.datastructure.Dataflow"
_URN_DATASTRUCTURE = "urn:sdmx:org.sdmx.infomodel.datastructure.DataStructure"
_URN_VERSION = r"[0-9]+(?:\.[0-9]+)*"

_WINDOW_PARAMS = {"startPeriod", "endPeriod"}
_META_KEYS = {"schema", "id", "prepared", "test", "contentLanguages", "sender"}
_STRUCT_KEYS = {"name", "names", "description", "descriptions", "links", "dimensions",
                "attributes", "annotations", "measures", "dataSets"}
_DS_KEYS = {"structure", "action", "links", "annotations", "attributes",
            "dimensionGroupAttributes", "series"}
_DIM_KEYS = {"id", "name", "names", "keyPosition", "roles", "values"}
_DIM_VALUE_KEYS = {"id", "name", "names", "order", "annotations", "parent", "parents"}
_ATTR_KEYS = {"id", "name", "names", "isMandatory", "roles", "relationship", "values"}
_ATTR_VALUE_KEYS = {"id", "order", "name", "names"}
_SERIES_KEYS = {"annotations", "attributes", "observations"}
_ANNOTATION_KEYS = {"id", "title", "type", "text", "texts"}
_SERIES_ATTR_IDS = {"UNIT_MULT", "DECIMALS"}
_REVIEWED_OBS_STATUS = {"A": "normal"}  # 'A' = Normal value; anything else fails closed


def parse_native_code(code: str | None) -> tuple[str, str, str]:
    """'<agency>,<dataflow>/<key>' -> (agency, dataflow, key); ValueError if malformed. The
    full triple is the unique publisher request identity of an active series; dataflow is the
    publisher's 'DSD@DF' token (e.g. 'DSD_STES@DF_CLI')."""
    if not isinstance(code, str):
        raise ValueError(f"OECD native_code must be '<agency>,<dataflow>/<key>', got {code!r}")
    agency, sep1, rest = code.partition(",")
    dataflow, sep2, key = rest.partition("/")
    if not sep1 or not sep2 or not _AGENCY.fullmatch(agency) \
            or not _DATAFLOW.fullmatch(dataflow) or not _KEY.fullmatch(key):
        raise ValueError(f"OECD native_code must be '<agency>,<dataflow>/<key>' with an "
                         f"agency id, a DSD@DF dataflow and dot-joined key pins, got {code!r}")
    return agency, dataflow, key


class _Num(str):
    """Internal JSON-number tag: json.loads(parse_int=parse_float=_Num) marks real JSON number
    tokens (and genuine numeric metadata indices) so a quoted string is never confused with a
    publisher number or index. Never leaves the module as a subclass: tokens are coerced to
    plain str before any RawRow is built."""


def _reject_constant(x: str):
    raise ValueError(f"OECD payload carries a non-JSON constant {x!r}")


def _no_duplicate_keys(pairs: list) -> dict:
    keys = [k for k, _ in pairs]
    if len(set(keys)) != len(keys):
        raise ValueError(f"OECD payload has duplicate keys {sorted(set(keys))[:5]}")
    return dict(pairs)


def _loads(body: bytes, what: str):
    head = body[:64].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    if head.startswith(b"<"):
        raise ValueError(f"OECD {what} answered markup/HTML, not SDMX-JSON: {body[:80]!r}")
    try:
        return json.loads(body, parse_int=_Num, parse_float=_Num,
                          parse_constant=_reject_constant,
                          object_pairs_hook=_no_duplicate_keys)
    except (ValueError, UnicodeDecodeError) as e:
        raise ValueError(f"OECD {what} is not valid JSON: {e}") from e


def _str(v, what: str) -> str:
    """A genuine non-empty JSON STRING (never a tagged number)."""
    if type(v) is not str or not v.strip():
        raise ValueError(f"OECD {what} must be a non-empty JSON string, got {v!r}")
    return v


def _index_value(v, what: str) -> int:
    """A GENUINE JSON number used as a structure/data index (keyPosition, attribute index,
    annotation reference): canonical decimal, non-negative, never a quoted alias."""
    if type(v) is not _Num or not _INDEX.fullmatch(v):
        raise ValueError(f"OECD {what} must be a genuine numeric JSON index (canonical "
                         f"decimal, unquoted), got {v!r}")
    return int(v)


def _annotation_refs(v, what: str, n_annotations: int) -> None:
    if not isinstance(v, list) or any(
            _index_value(a, f"{what} annotation reference") >= n_annotations for a in v):
        raise ValueError(f"OECD {what} annotation references out of range: {v!r}")


def _links(entries, what: str, want_rel: str, urn_prefix: str) -> None:
    """The one identity link of a structure/dataSet: exactly one entry whose rel and urn pin
    the requested publisher identity."""
    if not isinstance(entries, list) or len(entries) != 1:
        raise ValueError(f"OECD {what} must carry exactly one identity link, got {entries!r}")
    (link,) = entries
    if not isinstance(link, dict) or not set(link) <= {"rel", "href", "urn"}:
        raise ValueError(f"OECD {what} link shape drifted: {link!r}")
    if link.get("rel") != want_rel or type(link.get("urn")) is not str \
            or not re.fullmatch(re.escape(urn_prefix) + rf"\({_URN_VERSION}\)", link["urn"]):
        raise ValueError(f"OECD {what} identity urn drifted: {link!r}")


def _dim_values(entries, what: str, n_annotations: int) -> list[str]:
    """The pinned codes of a dimension's values; each entry must be a well-formed value object
    and ids must be unique (duplicate codes would make an index->code mapping ambiguous)."""
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"OECD {what} carries no values")
    codes = []
    for v in entries:
        if not isinstance(v, dict) or not set(v) <= _DIM_VALUE_KEYS or \
                "id" not in v or "name" not in v:
            raise ValueError(f"OECD {what} value shape drifted: {v!r}")
        code = _str(v["id"], f"{what} value id")
        if not _DIM_VALUE_ID.fullmatch(code):
            raise ValueError(f"OECD {what} value id is not a publisher code: {code!r}")
        _str(v["name"], f"{what} value name")
        if "order" in v:
            _index_value(v["order"], f"{what} value order")
        if "parent" in v:
            _str(v["parent"], f"{what} value parent")
        if "parents" in v and (not isinstance(v["parents"], list)
                               or any(type(p) is not str or not p for p in v["parents"])):
            raise ValueError(f"OECD {what} value parents drifted: {v['parents']!r}")
        if "annotations" in v:
            _annotation_refs(v["annotations"], f"{what} value", n_annotations)
        codes.append(code)
    if len(set(codes)) != len(codes):
        raise ValueError(f"OECD {what} carries duplicate value codes {codes!r}")
    return codes


def _payload(body: bytes, agency: str, dataflow: str, key: str,
             what: str) -> list[tuple[str, str | None, str]]:
    """One OECD SDMX-JSON data response for ONE pinned series, strictly shaped. Returns the
    rows as (period, value token or None, OBS_STATUS code)."""
    doc = _loads(body, what)
    if not isinstance(doc, dict) or set(doc) != {"meta", "data", "errors"}:
        raise ValueError(f"OECD {what} top-level keys drifted: "
                         f"{sorted(doc) if isinstance(doc, dict) else doc!r}")
    if not isinstance(doc["errors"], list) or doc["errors"]:
        raise ValueError(f"OECD {what} is an error response: {doc['errors']!r}")

    meta = doc["meta"]
    if not isinstance(meta, dict) or not set(meta) <= _META_KEYS:
        raise ValueError(f"OECD {what} meta keys drifted: {sorted(meta)!r}")
    if meta.get("schema") != SCHEMA_URL or type(meta.get("schema")) is not str:
        raise ValueError(f"OECD {what} is not schema {SCHEMA_URL}: {meta.get('schema')!r}")
    if type(meta.get("prepared")) is not str or not _PREPARED.fullmatch(meta["prepared"]):
        raise ValueError(f"OECD {what} meta.prepared drifted: {meta.get('prepared')!r}")
    if type(meta.get("test")) is not bool or meta["test"] is not False:
        raise ValueError(f"OECD {what} meta.test must be the JSON boolean false: "
                         f"{meta.get('test')!r}")
    if "contentLanguages" in meta and (
            not isinstance(meta["contentLanguages"], list)
            or any(type(c) is not str or not c for c in meta["contentLanguages"])):
        raise ValueError(f"OECD {what} meta.contentLanguages drifted: "
                         f"{meta['contentLanguages']!r}")
    sender = meta.get("sender")
    if not isinstance(sender, dict) or type(sender.get("id")) is not str \
            or not sender["id"].strip():
        raise ValueError(f"OECD {what} meta.sender drifted: {sender!r}")

    data = doc["data"]
    if not isinstance(data, dict) or set(data) != {"dataSets", "structures"}:
        raise ValueError(f"OECD {what} data keys drifted: "
                         f"{sorted(data) if isinstance(data, dict) else data!r}")
    structs = data["structures"]
    if not isinstance(structs, list) or len(structs) != 1:
        raise ValueError(f"OECD {what} must carry exactly one structure")
    datasets = data["dataSets"]
    if not isinstance(datasets, list) or len(datasets) != 1:
        raise ValueError(f"OECD {what} must carry exactly one dataSet (a multi-dataset "
                         "response is an unreviewed shape)")

    struct = structs[0]
    if not isinstance(struct, dict) or not set(struct) <= _STRUCT_KEYS \
            or not {"name", "dimensions", "attributes"} <= set(struct):
        raise ValueError(f"OECD {what} structure keys drifted: {sorted(struct)!r}")
    _str(struct["name"], f"{what} structure name")
    dsd = dataflow.split("@", 1)[0]
    _links(struct.get("links"), f"{what} structure links", "datastructure",
           f"{_URN_DATAFLOW}={agency}:{dataflow}")
    if not isinstance(struct.get("dataSets"), list) or len(struct["dataSets"]) != 1 \
            or _index_value(struct["dataSets"][0], f"{what} structure dataSets") != 0:
        raise ValueError(f"OECD {what} structure dataSets reference drifted: "
                         f"{struct.get('dataSets')!r}")
    annotations = struct.get("annotations", [])
    if not isinstance(annotations, list) or any(
            not isinstance(a, dict) or not set(a) <= _ANNOTATION_KEYS for a in annotations):
        raise ValueError(f"OECD {what} structure annotations shape drifted")
    n_annotations = len(annotations)

    dims = struct["dimensions"]
    if not isinstance(dims, dict) or set(dims) != {"dataSet", "series", "observation"}:
        raise ValueError(f"OECD {what} dimensions keys drifted: "
                         f"{sorted(dims) if isinstance(dims, dict) else dims!r}")
    if dims["dataSet"] != []:
        raise ValueError(f"OECD {what} carries dataset dimensions (unreviewed): "
                         f"{dims['dataSet']!r}")
    series_dims = dims["series"]
    if not isinstance(series_dims, list) or not series_dims:
        raise ValueError(f"OECD {what} carries no series dimensions")
    pins: list[list[str]] = [[]] * len(series_dims)
    positions = set()
    for d in series_dims:
        if not isinstance(d, dict) or not set(d) <= _DIM_KEYS \
                or not {"id", "name", "keyPosition", "values"} <= set(d):
            raise ValueError(f"OECD {what} series dimension shape drifted: {d!r}")
        _str(d["id"], f"{what} series dimension id")
        _str(d["name"], f"{what} series dimension name")
        if "roles" in d and (not isinstance(d["roles"], list)
                             or any(type(r) is not str or not r for r in d["roles"])):
            raise ValueError(f"OECD {what} series dimension roles drifted: {d!r}")
        pos = _index_value(d["keyPosition"], f"{what} series dimension "
                                             f"{d['id']!r} keyPosition")
        if pos in positions or pos >= len(series_dims):
            raise ValueError(f"OECD {what} series dimension keyPosition drifted: {pos} "
                             f"(duplicate or out of range 0..{len(series_dims) - 1})")
        positions.add(pos)
        # A series-request response lists the PINNED value plus (hierarchy) parents; the
        # series key's index at this dimension resolves the actual pin.
        pins[pos] = _dim_values(d["values"], f"{what} series dimension {d['id']!r}",
                                n_annotations)
    if len(positions) != len(series_dims):
        raise ValueError(f"OECD {what} series dimension keyPositions do not cover "
                         f"0..{len(series_dims) - 1}")

    obs_dims = dims["observation"]
    if not isinstance(obs_dims, list) or len(obs_dims) != 1:
        raise ValueError(f"OECD {what} must carry exactly one observation dimension")
    tp_dim = obs_dims[0]
    if not isinstance(tp_dim, dict) or not set(tp_dim) <= _DIM_KEYS \
            or not {"id", "name", "keyPosition", "values"} <= set(tp_dim):
        raise ValueError(f"OECD {what} observation dimension shape drifted: {tp_dim!r}")
    if tp_dim.get("id") != "TIME_PERIOD":
        raise ValueError(f"OECD {what} observation dimension is not TIME_PERIOD: "
                         f"{tp_dim.get('id')!r}")
    if _index_value(tp_dim["keyPosition"], f"{what} TIME_PERIOD keyPosition") != \
            len(series_dims):
        raise ValueError(f"OECD {what} TIME_PERIOD keyPosition must be {len(series_dims)}")
    if not isinstance(tp_dim["values"], list) or not tp_dim["values"]:
        raise ValueError(f"OECD {what} TIME_PERIOD carries no values")
    periods: list[str] = []
    for v in tp_dim["values"]:
        if not isinstance(v, dict) or not set(v) <= {"id", "name", "names", "start", "end"} \
                or not {"id", "start", "end"} <= set(v):
            raise ValueError(f"OECD {what} TIME_PERIOD value shape drifted: {v!r}")
        p = v["id"]
        if type(p) is not str or not _PERIOD.fullmatch(p):
            raise ValueError(f"OECD {what} TIME_PERIOD id is not a canonical ASCII YYYY-MM: "
                             f"{p!r}")
        for ts_key in ("start", "end"):
            ts = v[ts_key]
            if type(ts) is not str or not _TS.fullmatch(ts) or ts[:7] != p:
                raise ValueError(f"OECD {what} TIME_PERIOD {p!r} {ts_key} drifted: {ts!r}")
        if v["start"][8:10] != "01" or (type(v.get("name")) is str and v["name"] != p):
            raise ValueError(f"OECD {what} TIME_PERIOD {p!r} start/name drifted: {v!r}")
        periods.append(p)
    if len(set(periods)) != len(periods):
        raise ValueError(f"OECD {what} carries duplicate TIME_PERIOD ids")

    attrs = struct["attributes"]
    if not isinstance(attrs, dict) or set(attrs) != {"dataSet", "dimensionGroup", "series",
                                                     "observation"}:
        raise ValueError(f"OECD {what} attributes keys drifted: "
                         f"{sorted(attrs) if isinstance(attrs, dict) else attrs!r}")
    if attrs["dataSet"] != [] or attrs["dimensionGroup"] != []:
        raise ValueError(f"OECD {what} carries dataset/dimension-group attribute definitions "
                         "(unreviewed)")
    attr_defs = attrs["series"]
    if not isinstance(attr_defs, list) or not attr_defs:
        raise ValueError(f"OECD {what} series attributes missing")
    series_attr_ids = []
    for a in attr_defs:
        if not isinstance(a, dict) or not set(a) <= _ATTR_KEYS or "id" not in a:
            raise ValueError(f"OECD {what} series attribute shape drifted: {a!r}")
        aid = _str(a["id"], f"{what} series attribute id")
        if aid not in _SERIES_ATTR_IDS:
            raise ValueError(f"OECD {what} carries the unreviewed series attribute {aid!r}")
        if aid in series_attr_ids:
            raise ValueError(f"OECD {what} series attribute {aid!r} defined twice")
        series_attr_ids.append(aid)
        if type(a.get("isMandatory")) is not bool:
            raise ValueError(f"OECD {what} series attribute {aid} isMandatory must be a "
                             "JSON boolean")
        vals = _dim_values_like(a.get("values"), f"{what} series attribute {aid}",
                                decimals=(aid == "DECIMALS"))
        if aid == "UNIT_MULT" and set(vals) != {"0"}:
            raise ValueError(f"OECD {what} UNIT_MULT values {vals!r} are not the reviewed "
                             "'0' (Units): any other multiplier is a wrong scale, fail closed")
    if "UNIT_MULT" not in series_attr_ids or "DECIMALS" not in series_attr_ids:
        raise ValueError(f"OECD {what} series attributes must define UNIT_MULT and DECIMALS: "
                         f"{series_attr_ids!r}")

    obs_attr_defs = attrs["observation"]
    if not isinstance(obs_attr_defs, list) or len(obs_attr_defs) != 1:
        raise ValueError(f"OECD {what} observation attributes must be exactly OBS_STATUS")
    obs_attr = obs_attr_defs[0]
    if not isinstance(obs_attr, dict) or not set(obs_attr) <= _ATTR_KEYS \
            or obs_attr.get("id") != "OBS_STATUS":
        raise ValueError(f"OECD {what} observation attribute shape drifted: {obs_attr!r}")
    obs_status_table = _dim_values(obs_attr.get("values"), f"{what} OBS_STATUS",
                                   n_annotations)
    if any(c not in _REVIEWED_OBS_STATUS for c in obs_status_table):
        raise ValueError(f"OECD {what} OBS_STATUS table carries unreviewed codes "
                         f"{obs_status_table!r}: only 'A' (Normal value) is reviewed; "
                         "fail closed, never guess a status (discovery item 13: full codelist "
                         "not enumerable)")

    measures = struct.get("measures")
    if not isinstance(measures, dict) or set(measures) != {"observation"} \
            or not isinstance(measures["observation"], list) \
            or len(measures["observation"]) != 1 \
            or measures["observation"][0].get("id") != "OBS_VALUE":
        raise ValueError(f"OECD {what} measures must be exactly OBS_VALUE: {measures!r}")

    ds = datasets[0]
    if not isinstance(ds, dict) or set(ds) != _DS_KEYS:
        raise ValueError(f"OECD {what} dataSet keys drifted: "
                         f"{sorted(ds) if isinstance(ds, dict) else ds!r}")
    if _index_value(ds["structure"], f"{what} dataSet structure") != 0:
        raise ValueError(f"OECD {what} dataSet must reference structure 0")
    if ds["action"] != ACTION_INFORMATION or type(ds["action"]) is not str:
        raise ValueError(f"OECD {what} dataSet action drifted: {ds['action']!r}")
    _links(ds["links"], f"{what} dataSet links", "datastructure",
           f"{_URN_DATASTRUCTURE}={agency}:{dsd}")
    _annotation_refs(ds["annotations"], f"{what} dataSet", n_annotations)
    if ds["attributes"] != []:
        raise ValueError(f"OECD {what} dataSet attributes must be empty in the reviewed "
                         f"shape: {ds['attributes']!r}")
    dga = ds["dimensionGroupAttributes"]
    # Dimension-group keys reference arbitrary dimension subsets (evidence carries 9- AND
    # 10-segment keys): shape-check canonical segments only; values are annotation indices.
    if not isinstance(dga, dict) or any(
            type(k) is not str or not _DG_KEY.fullmatch(k) for k in dga):
        raise ValueError(f"OECD {what} dimensionGroupAttributes keys drifted: "
                         f"{list(dga)[:3]!r}")
    for k, v in dga.items():
        _annotation_refs(v, f"{what} dimensionGroupAttributes {k!r}", n_annotations)

    series_entries = ds["series"]
    if not isinstance(series_entries, dict) or len(series_entries) != 1:
        raise ValueError(f"OECD {what} must carry exactly one series entry (one pinned "
                         f"series per request), got {list(series_entries)!r}")
    (series_key, entry), = series_entries.items()
    seg = series_key.split(":")
    if len(seg) != len(series_dims) or any(type(k) is not str or not _INDEX.fullmatch(k)
                                           for k in seg):
        raise ValueError(f"OECD {what} series key {series_key!r} is not canonical decimal "
                         f"segments x{len(series_dims)} (aliases/'00'/Unicode rejected)")
    key_pins = key.split(".")
    for pos, k in enumerate(seg):
        i = int(k)
        if i >= len(pins[pos]):
            raise ValueError(f"OECD {what} series key {series_key!r} index {i} out of range "
                             f"for dimension {pos} ({len(pins[pos])} values)")
        # FULL pinned identity: the payload dimension value the key resolves to must equal the
        # requested key segment (payload identity, never URL trust).
        if pins[pos][i] != key_pins[pos]:
            raise ValueError(f"OECD {what} identity drift: series key {series_key!r} resolves "
                             f"dimension {pos} to {pins[pos][i]!r} but the request pinned "
                             f"{key_pins[pos]!r}")
    if not isinstance(entry, dict) or not set(entry) <= _SERIES_KEYS \
            or "observations" not in entry:
        raise ValueError(f"OECD {what} series entry shape drifted: {sorted(entry)!r}")
    _annotation_refs(entry.get("annotations", []), f"{what} series", n_annotations)
    attr_idx = entry.get("attributes", [])
    if not isinstance(attr_idx, list) or len(attr_idx) != len(attr_defs):
        raise ValueError(f"OECD {what} series attributes must index every series attribute "
                         f"definition: {attr_idx!r}")
    resolved: dict[str, str] = {}
    for i, a in enumerate(attr_idx):
        table = _dim_values_like(attr_defs[i].get("values"), f"{what} series attribute "
                                 f"{attr_defs[i]['id']}",
                                 decimals=(attr_defs[i]["id"] == "DECIMALS"))
        j = _index_value(a, f"{what} series attribute index")
        if j >= len(table):
            raise ValueError(f"OECD {what} series attribute {attr_defs[i]['id']} index {j} "
                             f"out of range ({len(table)} values)")
        resolved[attr_defs[i]["id"]] = table[j]
    if resolved.get("UNIT_MULT") != "0":
        raise ValueError(f"OECD {what} series resolves UNIT_MULT={resolved.get('UNIT_MULT')!r}"
                         " != '0' (Units): wrong scale, fail closed")
    if not re.fullmatch(r"[0-9]+", resolved.get("DECIMALS", "")):
        raise ValueError(f"OECD {what} DECIMALS is not a digit string: "
                         f"{resolved.get('DECIMALS')!r} (display hint, never used)")

    obs = entry["observations"]
    if not isinstance(obs, dict) or not obs:
        raise ValueError(f"OECD {what} series carries no observations "
                         "(an empty series is an unreviewed shape, fail closed)")
    rows: list[tuple[str, str | None, str]] = []
    for ix, tup in obs.items():
        if type(ix) is not str or not _INDEX.fullmatch(ix) or int(ix) >= len(periods):
            raise ValueError(f"OECD {what} observation index {ix!r} is not a canonical ASCII "
                             f"decimal index 0..{len(periods) - 1} (aliases rejected)")
        if not isinstance(tup, list) or len(tup) != 1 + len(obs_attr_defs) or not tup:
            raise ValueError(f"OECD {what} observation entry must be [value, OBS_STATUS "
                             f"attribute index]: {tup!r}")
        v = tup[0]
        if v is None:
            token = None
        elif type(v) is _Num:
            token = str(v)
        else:
            raise ValueError(f"OECD {what} observation value must be a genuine JSON number "
                             f"(or null), got {type(v).__name__} {v!r}: a quoted numeric "
                             "string is a type flip, fail closed")
        si = _index_value(tup[1], f"{what} observation OBS_STATUS attribute index")
        if si >= len(obs_status_table):
            raise ValueError(f"OECD {what} observation OBS_STATUS attribute index {si} out "
                             f"of range ({len(obs_status_table)} values)")
        rows.append((periods[int(ix)], token, obs_status_table[si]))
    return rows


def _dim_values_like(entries, what: str, *, decimals: bool) -> list[str]:
    """The id list of an attribute definition's values (codes or digit labels)."""
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"OECD {what} carries no values")
    ids = []
    for v in entries:
        if not isinstance(v, dict) or not set(v) <= _ATTR_VALUE_KEYS or "id" not in v:
            raise ValueError(f"OECD {what} value shape drifted: {v!r}")
        vid = _str(v["id"], f"{what} value id")
        if decimals and not re.fullmatch(r"[0-9]+", vid):
            raise ValueError(f"OECD {what} value id is not a digit label: {vid!r}")
        if "order" in v:
            _index_value(v["order"], f"{what} value order")
        ids.append(vid)
    if len(set(ids)) != len(ids):
        raise ValueError(f"OECD {what} carries duplicate value ids {ids!r}")
    return ids


def _identify(resp: RawResponse, what: str) -> tuple[str, str, str, dict]:
    """(agency, dataflow, key, params) of an archived response from its url/params identity."""
    if not isinstance(resp.params, dict):
        raise ValueError(f"OECD {what} carries no archived params: request identity is "
                         "unidentifiable")
    parts = urlsplit(resp.url)
    if parts.scheme != "https" or parts.netloc != "sdmx.oecd.org":
        raise ValueError(f"OECD {what} URL is not the sdmx.oecd.org data API: {resp.url!r}")
    seg = parts.path.split("/")
    if len(seg) != 6 or seg[:4] != ["", "public", "rest", "data"]:
        raise ValueError(f"OECD {what} URL is not a /public/rest/data/<agency>,<dataflow>/"
                         f"<key> request: {resp.url!r}")
    agency, dataflow, key = parse_native_code(f"{seg[4]}/{seg[5]}")
    params = {k: str(v) for k, v in resp.params.items()}
    if not set(params) <= _WINDOW_PARAMS:
        raise ValueError(f"OECD {what} archived params carry unreviewed keys "
                         f"{sorted(set(params) - _WINDOW_PARAMS)}: {params!r}")
    for k, v in params.items():
        if not _PERIOD.fullmatch(v):
            raise ValueError(f"OECD {what} archived param {k}={v!r} is not a canonical "
                             "YYYY-MM literal")
    # The archived URL query is a STRICT projection of the archived params: every key present
    # in the URL must be a reviewed key and must agree with params exactly; duplicated keys
    # are rejected (a dict view would hide them).
    pairs = parse_qsl(parts.query, keep_blank_values=True)
    qkeys = [k for k, _ in pairs]
    if len(set(qkeys)) != len(qkeys):
        raise ValueError(f"OECD {what} URL query carries duplicated keys: {resp.url!r}")
    q = dict(pairs)
    if not set(q) <= _WINDOW_PARAMS:
        raise ValueError(f"OECD {what} URL query carries unreviewed keys "
                         f"{sorted(set(q) - _WINDOW_PARAMS)}: {resp.url!r}")
    if any(k not in params or q[k] != params[k] for k in q):
        raise ValueError(f"OECD {what} URL query disagrees with archived params: "
                         f"{resp.url!r} vs {params!r}")
    return agency, dataflow, key, params


def _period_arg(name: str, v: str | None) -> str | None:
    if v is None:
        return None
    if not isinstance(v, str) or not _PERIOD.fullmatch(v):
        raise ValueError(f"OECD {name} must be a canonical YYYY-MM literal or None, got {v!r}")
    return v


def _native_code(s: SeriesSpec) -> str:
    """The series' canonical registry native_code; raises unless well-formed (fail fast)."""
    nc = s.native_code
    parse_native_code(nc)
    if not isinstance(nc, str):
        raise ValueError(f"OECD series {s.id!r} carries no native_code")
    return nc


class OecdSource:
    """OECD SDMX-JSON data 2.0 source. One response per series native_code, sorted; full
    history by default, or the explicit start_period/end_period window (both canonical
    YYYY-MM). See the module docstring for the fail-closed contract."""

    name = "oecd"
    expected_format = "json"

    def __init__(self, start_period: str | None = None, end_period: str | None = None):
        self._start = _period_arg("start_period", start_period)
        self._end = _period_arg("end_period", end_period)
        if self._start is not None and self._end is not None and self._start > self._end:
            raise ValueError(f"OECD window is inverted: start_period {self._start} > "
                             f"end_period {self._end}")

    def fetch(self, specs: list[SeriesSpec], http: Http) -> Iterator[RawResponse]:
        timeouts = {s.source.timeout_s for s in specs}
        if len(timeouts) != 1:
            raise ValueError(f"OECD fetch over mixed source timeouts: {timeouts!r}")
        (timeout,) = timeouts
        params: dict[str, str] = {}
        if self._start is not None:
            params["startPeriod"] = self._start
        if self._end is not None:
            params["endPeriod"] = self._end
        headers = {"Accept": ACCEPT_SDMX_JSON}
        for nc in sorted({_native_code(s) for s in specs}):
            url = f"{API_BASE}/data/{nc}"
            r = http.get(url, params=dict(params), headers=headers) if timeout is None else \
                http.get(url, params=dict(params), headers=headers, timeout=timeout)
            yield RawResponse(url=r.url, params=dict(params), status=r.status, body=r.body)

    def parse(self, specs: list[SeriesSpec],
              responses: list[RawResponse]) -> dict[str, list[RawRow]]:
        """Map archived responses to per-series rows. See the module docstring for the
        fail-closed contract: identity comes from the archived url/params + payload structure,
        never from request order."""
        wanted: dict[str, SeriesSpec] = {}
        for s in specs:
            nc = _native_code(s)
            if nc in wanted:
                raise ValueError(f"duplicate native_code among OECD specs: {nc!r}")
            wanted[nc] = s
        rows: dict[str, list[RawRow]] = {s.id: [] for s in specs}
        seen: set[str] = set()
        for i, resp in enumerate(responses):
            what = f"response[{i}]"
            if not 200 <= resp.status < 300:
                raise ValueError(f"OECD {what} for {resp.url!r} answered HTTP {resp.status} "
                                 "(fail closed on every non-2xx)")
            agency, dataflow, key, params = _identify(resp, what)
            nc = f"{agency},{dataflow}/{key}"
            if nc not in wanted:
                raise ValueError(f"OECD {what} answered unrequested series {nc!r}")
            if nc in seen:
                raise ValueError(f"OECD {what} arrived twice for series {nc!r}")
            seen.add(nc)
            for period, token, status in _payload(resp.body, agency, dataflow, key, what):
                if "startPeriod" in params and period < params["startPeriod"]:
                    raise ValueError(f"OECD {what} decodes period {period} outside the "
                                     f"archived window startPeriod={params['startPeriod']} "
                                     "(window identity is a containment constraint)")
                if "endPeriod" in params and period > params["endPeriod"]:
                    raise ValueError(f"OECD {what} decodes period {period} outside the "
                                     f"archived window endPeriod={params['endPeriod']} "
                                     "(window identity is a containment constraint)")
                flag = _REVIEWED_OBS_STATUS.get(status)
                if flag is None:
                    raise ValueError(f"OECD {what} carries unreviewed OBS_STATUS code "
                                     f"{status!r}: fail closed, never guess")
                rows[wanted[nc].id].append(RawRow(period_raw=period, value_raw=token,
                                                  unit_raw=None, flag_raw=flag,
                                                  response_index=i))
        return rows
