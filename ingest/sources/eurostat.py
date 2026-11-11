"""Eurostat source adapter: JSON-stat 2.0 from the dissemination Statistics API.

    GET https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/<dataset>
        ?<dim>=<code>&...&geo=<g1>&geo=<g2>...

Registry contract (`SeriesSpec.native_code`), shared by every Eurostat series:

    <dataset>:<dim>=<code>,<dim>=<code>,...

  - every dimension of the dataset except `time` is pinned to exactly one code, in the
    dataset's own dimension order (the JSON-stat `id` order = the SDMX key order), `geo`
    included; e.g. `une_rt_m:freq=M,s_adj=SA,age=TOTAL,unit=PC_ACT,sex=T,geo=PT`;
  - so one native_code identifies exactly one Eurostat time series, and its `unit=` code is the
    unit the registry's `unit` label stands for (pairing checked when the registry was mapped,
    see registry/unmapped-eurostat.md).
`SeriesSpec.url` is the dataset's public data-browser page.

Requests: one per (dataset, non-geo key) with every geo of that group as repeated `geo=`
parameters and no time filter (full history, so revisions are seen). A whole dataset in one
request is too large for the synchronous API: Eurostat answers HTTP 413 "ASYNCHRONOUS_RESPONSE"
above a cell-count threshold, and the unrequested cartesian product of codes would be wasted.

Parsing: numbers are the publisher's tokens (`json.loads(parse_float=str, parse_int=str)`),
periods are Eurostat's own time codes ('2024', '2024-S1', '2024-Q1', '2024-03'; validate()
normalises them), status flags are mapped by `ingest.flags.map_eurostat_flag` onto the shared
vocabulary ('normal' stored explicitly). A status is '<flags>|<confidentiality>'
(`ingest.flags.split_eurostat_status`); a cell with a confidentiality code ('|C' confidential,
'|N' not for publication) has no publishable value whatever the payload holds. Such a cell, and
any cell that has a status but no value, is handed over with value None (validate() quarantines it as non_numeric, so the
publisher's "no value" stays on record). `unit_raw` is None: the cell is located by the unit code
pinned in native_code, so the registry unit is authoritative (validate() semantics).
Raises on anything unexpected: HTML or non-JSON body, a JSON error object, a JSON-stat structure
whose dimensions differ from native_code, malformed sizes/indices, unknown flags.
"""
import json
from collections.abc import Iterator
from urllib.parse import urlsplit

from ingest.flags import map_eurostat_flag, split_eurostat_status
from ingest.http import Http
from ingest.models import SeriesSpec
from ingest.sources import RawResponse
from ingest.validate import RawRow

BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"

Key = tuple[tuple[str, str], ...]  # ((dim, code), ...) in dataset order


def parse_native_code(code: str | None) -> tuple[str, Key]:
    """'<dataset>:<dim>=<code>,...' -> (dataset, ((dim, code), ...)); ValueError if malformed
    (missing dataset, a dimension without '=', a duplicated dimension, no `geo`, or `time`)."""
    if not code or ":" not in code:
        raise ValueError(f"Eurostat native_code must be '<dataset>:<dim>=<code>,...', got {code!r}")
    dataset, _, rest = code.partition(":")
    pairs = []
    for part in rest.split(","):
        dim, eq, val = part.partition("=")
        if not (dataset and dim and eq and val) or "=" in val or ":" in val:
            raise ValueError(f"malformed Eurostat native_code {code!r} (at {part!r})")
        pairs.append((dim, val))
    dims = [d for d, _ in pairs]
    if len(set(dims)) != len(dims) or "geo" not in dims or "time" in dims:
        raise ValueError(f"Eurostat native_code {code!r} must pin each dimension once, "
                         "including geo and excluding time")
    return dataset, tuple(pairs)


def _groups(specs: list[SeriesSpec]) -> list[tuple[str, Key, list[str], list[SeriesSpec]]]:
    """(dataset, non-geo key, sorted geos, specs) per request, in a deterministic order."""
    by: dict[tuple[str, Key], list[SeriesSpec]] = {}
    for s in specs:
        dataset, key = parse_native_code(s.native_code)
        by.setdefault((dataset, tuple((d, c) for d, c in key if d != "geo")), []).append(s)
    out = []
    for (dataset, rest), members in sorted(by.items()):
        geos = sorted({dict(parse_native_code(s.native_code)[1])["geo"] for s in members})
        out.append((dataset, rest, geos, members))
    return out


class EurostatSource:
    name = "eurostat"
    expected_format = "json"

    def fetch(self, specs: list[SeriesSpec], http: Http) -> Iterator[RawResponse]:
        for dataset, rest, geos, _ in _groups(specs):
            params: dict = {d: c for d, c in rest}
            params["geo"] = geos
            r = http.get(BASE_URL + dataset, params=params)
            yield RawResponse(url=r.url, params=params, status=r.status, body=r.body)

    def parse(self, specs: list[SeriesSpec],
              responses: list[RawResponse]) -> dict[str, list[RawRow]]:
        groups = _groups(specs)
        if len(responses) != len(groups):
            raise ValueError(f"expected {len(groups)} Eurostat responses (one per request), "
                             f"got {len(responses)}")
        out: dict[str, list[RawRow]] = {}
        for i, (resp, (dataset, _, _, members)) in enumerate(zip(responses, groups)):
            path = urlsplit(resp.url).path
            if not path.endswith("/data/" + dataset):
                raise ValueError(f"response {i} is for {path!r}, expected dataset {dataset!r}")
            cube = _Cube(_load(resp.body))
            for s in members:
                out[s.id] = cube.rows(parse_native_code(s.native_code)[1], i)
        return out


def _load(body: bytes) -> dict:
    head = body[:64].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    if head.startswith((b"<!doctype", b"<html", b"<?xml", b"<")):
        raise ValueError(f"Eurostat answered markup, not JSON-stat: {body[:80]!r}")
    try:
        doc = json.loads(body, parse_float=str, parse_int=str)
    except (ValueError, UnicodeDecodeError) as e:
        raise ValueError(f"Eurostat body is not JSON: {e}") from e
    if not isinstance(doc, dict):
        raise ValueError(f"Eurostat JSON is a {type(doc).__name__}, expected an object")
    if "error" in doc:
        raise ValueError(f"Eurostat error object: {doc['error']!r}")
    if doc.get("class") != "dataset":
        raise ValueError(f"not a JSON-stat dataset (class={doc.get('class')!r})")
    return doc


def _check_extent(name: str, table: dict | list, total: int) -> None:
    """A truncated payload must not silently lose cells (e.g. the newest periods): an array
    must cover the whole cube (an empty status array means no status at all); an object's
    keys must be flat indices inside it."""
    if isinstance(table, list):
        if len(table) != total and not (name == "status" and not table):
            raise ValueError(f"JSON-stat {name} array has {len(table)} cells, cube has {total}")
        return
    for key in table:
        if not (isinstance(key, str) and key.isdigit() and int(key) < total):
            raise ValueError(f"JSON-stat {name} key {key!r} outside the cube of {total} cells")


class _Cube:
    """A JSON-stat 2.0 dataset: values flattened row-major over `id` (last dimension fastest),
    `value`/`status` either arrays or {"<flat index>": ...} objects (sparse)."""

    def __init__(self, doc: dict):
        try:
            self.ids = list(doc["id"])
            self.size = [int(n) for n in doc["size"]]
            dims = doc["dimension"]
            self.index = {d: dims[d]["category"]["index"] for d in self.ids}
        except (KeyError, TypeError, ValueError) as e:
            raise ValueError(f"malformed JSON-stat structure: {e!r}") from e
        if len(self.ids) != len(self.size) or "time" not in self.ids:
            raise ValueError(f"JSON-stat id/size mismatch or no time dimension: {self.ids}")
        for d, n in zip(self.ids, self.size):
            idx = self.index[d]
            if isinstance(idx, list):  # JSON-stat allows an array of codes
                idx = {c: p for p, c in enumerate(idx)}
            positions = sorted(int(p) for p in idx.values())
            if positions != list(range(n)):
                raise ValueError(f"JSON-stat dimension {d!r}: index does not match size {n}")
            self.index[d] = {c: int(p) for c, p in idx.items()}
        self.stride = [1] * len(self.ids)
        for k in range(len(self.ids) - 2, -1, -1):
            self.stride[k] = self.stride[k + 1] * self.size[k + 1]
        self.value = doc.get("value")
        self.status = doc.get("status") or {}
        if not isinstance(self.value, (dict, list)) or not isinstance(self.status, (dict, list)):
            raise ValueError("JSON-stat value/status must be an array or an object")
        total = self.stride[0] * self.size[0] if self.size else 0
        for name, table in (("value", self.value), ("status", self.status)):
            _check_extent(name, table, total)

    def _cell(self, table, flat: int):
        if isinstance(table, list):
            return table[flat]
        return table.get(str(flat))

    def rows(self, key: Key, response_index: int) -> list[RawRow]:
        pinned = dict(key)
        if set(pinned) | {"time"} != set(self.ids):
            raise ValueError(f"dataset dimensions {self.ids} do not match native_code "
                             f"dimensions {sorted(pinned)}")
        base = 0
        for d, stride in zip(self.ids, self.stride):
            if d == "time":
                continue
            pos = self.index[d].get(pinned[d])
            if pos is None:  # Eurostat omits codes with no data at all: no rows (Ruling M)
                return []
            base += pos * stride
        t_stride = self.stride[self.ids.index("time")]
        rows = []
        for period, pos in sorted(self.index["time"].items(), key=lambda kv: kv[1]):
            flat = base + pos * t_stride
            value, status = self._cell(self.value, flat), self._cell(self.status, flat)
            if value is not None and not isinstance(value, str):
                raise ValueError(f"unexpected JSON-stat value {value!r} at {flat}")
            if status is not None and not isinstance(status, str):
                raise ValueError(f"unexpected JSON-stat status {status!r} at {flat}")
            if value is None and status is None:
                continue  # nothing published for this period
            flags, confidentiality = split_eurostat_status(status)
            if confidentiality is not None:
                value = None  # confidential / not for publication: no publishable value
            flag = map_eurostat_flag(flags, value_present=value is not None)
            rows.append(RawRow(period_raw=period, value_raw=value, flag_raw=flag,
                               response_index=response_index))
        return rows
