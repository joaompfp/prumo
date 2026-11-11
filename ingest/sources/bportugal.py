"""Banco de Portugal (BPstat) source adapter: the public JSON-stat 2.0 data API.

    GET https://bpstat.bportugal.pt/data/v1/domains/<domain>/datasets/<dataset>/
        ?lang=EN&series_ids=<id,...>&decimal=true

Registry contract (`SeriesSpec.native_code`):

    <series_id>:<domain_id>/<dataset_id>      e.g. 12099464:26/690b7b36fd36c0dbe249c48cbbc39524

  - ids come from the documented API (https://bpstat.bportugal.pt/data/docs): the series id from
    /data/v1/series/?series_ids=.., domain+dataset from that entry's dataset_id/domain_ids.
    One native_code identifies exactly one BPstat series.
`SeriesSpec.url` is the series' public portal page https://bpstat.bportugal.pt/serie/<series_id>.

`decimal=true` (documented): observation values are the publisher's fixed-decimal STRINGS, "the
exact same number of decimal places as displayed in the BPstat website" ('7.1200'), handed over
verbatim (registry `decimal: '.'`). Full history is fetched (no obs_since/obs_to), so revisions
are seen (the API always serves the current vintage; first-full-fetch then re-fetch is how
revisions reach us). Groups: one request per (domain, dataset) with the group's sorted series
ids; the registry carries no timeout_s (the API answers sub-second to a few seconds), so fetch
omits the timeout kwarg and older Http doubles keep working.

Parsing (JSON-stat 2.0): flat `value`/`status` arrays iterate `id` dimensions row-major with the
LAST dimension (`reference_date`, the time axis) fastest — empirically cross-checked against the
portal channel on 2026-11-11 (value[394] is Euribor 3m@1994-01, '6.9100', not value[1]). Each
requested series is located through `extension.series[].dimension_category` pins (never by list
position: the Euribor payload's category order did not follow the request order), with strict
checks: dense or canonical-key sparse arrays sized to the declared dims, unique increasing
timestamps, no duplicate keys, every requested series present exactly once and mapping to its
own cell block, the pinned category present in the dimension's index. Publisher labels are
checked against the registry spec and raise on drift (fail-closed maps): unit ('Unit of
measure' -> Percentage='%', 'Millions of euros'=MEUR, 'Currency' only as the EUR/USD
pair='USD/EUR'),
periodicity 'Monthly'='M', territory ('Reference territory' -> Portugal='PT', Germany='DE',
'Euro Area - Changing composition'='EA'; the EUR/USD series has no territory dimension and is
identified by its currency pair, geography EA by reviewed convention).
`status` is mapped by ingest.flags.map_bportugal_flag ('F' = final -> normal; the only code
observed in every core series' full history on 2026-11-11): unknown codes raise, a null status on
a valued cell raises, a status on a valueless cell raises; valueless cells (e.g. DE yields before
2000-01) become value-None rows (validate() quarantines them non_numeric).
Periods: month-end ISO dates are handed over as 'YYYY-MM' (all core series are monthly).
Raises on: markup/invalid JSON bodies, API error objects, wrong class/version, truncated or
double-mapped payloads, duplicate period labels, wrong series/unit/frequency/territory.
"""
import json
import re
from collections.abc import Iterator
from datetime import date

from ingest.flags import map_bportugal_flag
from ingest.http import Http
from ingest.models import SeriesSpec
from ingest.sources import RawResponse
from ingest.validate import RawRow

API_BASE = "https://bpstat.bportugal.pt/data/v1/domains"
PAGE_URL = "https://bpstat.bportugal.pt/serie/"
TIME_DIM = "reference_date"

# Reviewed fail-closed maps (live evidence in tests/ingest/test_registry_bportugal_units.py and
# fixtures/bportugal/, 2026-11-11). Anything outside raises.
_UNIT_OF_LABEL = {"Percentage": "%", "Millions of euros": "MEUR"}
_PERIODICITY_OF_LABEL = {"Monthly": "M"}
_TERRITORY_OF_LABEL = {"Portugal": "PT", "Germany": "DE", "Euro Area - Changing composition": "EA"}
_CURRENCY_REF = ("Euro", "United States of America, Dollars")  # reference, counterparty
_CURRENCY_UNIT = "USD/EUR"
_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")

Key = tuple[int, int, str]  # (series id, domain id, dataset id)


def parse_native_code(code: str | None) -> Key:
    """'<series_id>:<domain_id>/<dataset_id>' -> (int, int, dataset); ValueError if malformed."""
    series, sep1, rest = (code or "").partition(":")
    domain, sep2, dataset = rest.partition("/")
    if not (sep1 and sep2 and series.isdigit() and domain.isdigit()
            and re.fullmatch(r"[0-9a-f]{32}", dataset)):
        raise ValueError(f"BPstat native_code must be '<series id>:<domain id>/<32-hex dataset "
                         f"id>', got {code!r}")
    return int(series), int(domain), dataset


def _groups(specs: list[SeriesSpec]) -> list[tuple[int, str, list[SeriesSpec]]]:
    """(domain, dataset, specs) per request, sorted ascending — the deterministic fetch order."""
    by: dict[tuple[int, str], list[SeriesSpec]] = {}
    for s in specs:
        _, domain, dataset = parse_native_code(s.native_code)
        by.setdefault((domain, dataset), []).append(s)
    return [(domain, dataset, members) for (domain, dataset), members in sorted(by.items())]


class BPortugalSource:
    name = "bportugal"
    expected_format = "json"

    def fetch(self, specs: list[SeriesSpec], http: Http) -> Iterator[RawResponse]:
        timeouts = {s.source.timeout_s for s in specs}
        if len(timeouts) != 1:
            raise ValueError(f"BPstat fetch over mixed source timeouts: {timeouts!r}")
        (timeout,) = timeouts
        for domain, dataset, members in _groups(specs):
            params = {"lang": "EN",
                      "series_ids": ",".join(sorted(str(parse_native_code(s.native_code)[0])
                                                    for s in members)),
                      "decimal": "true"}
            url = f"{API_BASE}/{domain}/datasets/{dataset}/"
            # timeout=None = the client's default: the kwarg is then NOT passed, so older Http
            # doubles with a 3-parameter get() keep working (the INE pattern).
            r = http.get(url, params=params) if timeout is None else \
                http.get(url, params=params, timeout=timeout)
            yield RawResponse(url=r.url, params=params, status=r.status, body=r.body)

    def parse(self, specs: list[SeriesSpec],
              responses: list[RawResponse]) -> dict[str, list[RawRow]]:
        groups = _groups(specs)
        if len(responses) != len(groups):
            raise ValueError(f"expected {len(groups)} BPstat responses (one per dataset), "
                             f"got {len(responses)}")
        out: dict[str, list[RawRow]] = {}
        for i, (resp, (_, _, members)) in enumerate(zip(responses, groups)):
            for sid, (freq, rows) in _series_rows(_load(resp.body), members).items():
                out[sid] = [RawRow(period_raw=_period(d, freq), value_raw=v,
                                   flag_raw=f, response_index=i) for d, v, f in rows]
        return out


class _JsonNumber(str):
    """A bare JSON number. With decimal=true BPstat sends every value as a JSON string; a number
    where a string is expected (a value, a status) is a format change and is rejected."""


def _no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    keys = [k for k, _ in pairs]
    if len(set(keys)) != len(keys):
        raise ValueError(f"BPstat JSON object has duplicate keys {sorted(set(keys))[:5]}")
    return dict(pairs)


def _plain(v: object) -> str | None:
    """v must be a real JSON string (not a number); return it, else raise."""
    if isinstance(v, str) and not isinstance(v, _JsonNumber):
        return v
    raise ValueError(f"expected a JSON string token, got {v!r}")


def _int_token(v: object, what: str) -> int:
    if not isinstance(v, _JsonNumber) or not v.isdigit():
        raise ValueError(f"{what} must be a non-negative JSON integer, got {v!r}")
    return int(v)


def _load(body: bytes) -> dict:
    head = body[:64].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    if head.startswith(b"<"):
        raise ValueError(f"BPstat answered markup, not JSON: {body[:80]!r}")
    try:
        doc = json.loads(body, parse_float=_JsonNumber, parse_int=_JsonNumber,
                         object_pairs_hook=_no_duplicate_keys)
    except (ValueError, UnicodeDecodeError) as e:
        raise ValueError(f"BPstat body is not valid JSON: {e}") from e
    if not isinstance(doc, dict) or doc.get("class") != "dataset" or "value" not in doc:
        raise ValueError(f"BPstat payload is not a JSON-stat dataset (API error or format "
                         f"change): {head[:60]!r} keys {sorted(doc)[:6] if isinstance(doc, dict) else '?'}")
    if doc.get("version") != "2.0":
        raise ValueError(f"BPstat JSON-stat version {doc.get('version')!r}, expected '2.0'")
    return doc


def _index_of(dim: dict) -> list[str]:
    """A dimension's category ids in flat order. Only the list form was observed (2026-11-11);
    the JSON-stat label->position dict form must be reviewed before use."""
    cat = dim.get("category")
    if not isinstance(cat, dict):
        raise ValueError(f"dimension without 'category': {dim!r}")
    idx = cat.get("index")
    if not isinstance(idx, list):
        raise ValueError(f"dimension {cat.get('label', dim.get('label'))!r}: category.index is "
                         f"not a list ({type(idx).__name__}) — unsliced dict form not reviewed")
    out = [str(_plain(v)) for v in idx]
    if len(set(out)) != len(out):
        raise ValueError(f"duplicate category ids/period labels in "
                         f"{dim.get('label')!r}: {out[:8]!r}")
    labels = cat.get("label")
    if labels is not None and (not isinstance(labels, dict) or set(labels) != set(out)):
        raise ValueError(f"category.label of {dim.get('label')!r} does not cover its index")
    return out


def _cells_column(col: object, size: int, what: str) -> list:
    """`value`/`status` as a per-flat-index list; dense list or sparse dict keyed by the
    CANONICAL ASCII decimal of the flat index ('0', '1', ...). Alias spellings that int()
    would fold onto the same cell ('00', '+1', Unicode digit aliases) raise: two keys for one
    cell is a silent overwrite, i.e. data corruption."""
    if isinstance(col, list):
        if len(col) != size:
            raise ValueError(f"{what} has {len(col)} cells but the dimensions declare {size} "
                             f"(truncated or malformed payload)")
        return col
    if isinstance(col, dict):  # sparse form
        out = [None] * size
        for k, v in col.items():
            kk = str(k)
            if not (kk.isascii() and kk.isdigit()):
                raise ValueError(f"sparse {what} key {kk!r} is not an ASCII decimal index")
            i = int(kk)
            if str(i) != kk:
                raise ValueError(f"sparse {what} key {kk!r} is a non-canonical alias of cell "
                                 f"{i} (would silently overwrite it)")
            if i >= size:
                raise ValueError(f"sparse {what} key {kk!r} outside 0..{size - 1}")
            out[i] = v
        return out
    raise ValueError(f"{what} is neither a list nor a sparse dict: {type(col).__name__}")


def _labels_of(doc: dict, pins: dict[str, str], dims: dict[str, list[str]],
               dims_doc: dict) -> dict[str, str]:
    """dimension label -> pinned category label for one series (EN, lang is pinned in fetch)."""
    out = {}
    for d, cat in pins.items():
        dim_title = _plain(dims_doc[d].get("label"))
        labels = dims_doc[d]["category"].get("label") or {}
        out[str(dim_title)] = labels.get(cat, cat)
    return out


def _check_identity(spec: SeriesSpec, labels: dict[str, str]) -> None:
    """The payload's own metadata must agree with the registry spec — wrong series/unit/
    frequency/territory payloads raise here (never silently served)."""
    unit = labels.get("Unit of measure")
    if unit == "Currency":
        # ambiguous publisher label: pin the currency pair (EUR per USD quote)
        if (labels.get("Reference currency"), labels.get("Counterparty currency")) != _CURRENCY_REF:
            raise ValueError(f"'Currency' unit without the reviewed EUR/USD pair: {labels!r}")
        observed_unit = _CURRENCY_UNIT
    else:
        observed_unit = _UNIT_OF_LABEL.get(unit or "")
    if observed_unit is None:
        raise ValueError(f"unknown BPstat unit-of-measure label {unit!r} for {spec.id}")
    if observed_unit != spec.unit:
        raise ValueError(f"{spec.id}: payload unit {observed_unit!r} != registry {spec.unit!r}")
    periodicity = _PERIODICITY_OF_LABEL.get(labels.get("Periodicity") or "")
    if periodicity is None:
        raise ValueError(f"unknown BPstat periodicity label {labels.get('Periodicity')!r}")
    if periodicity != spec.frequency:
        raise ValueError(f"{spec.id}: payload periodicity {periodicity!r} != registry "
                         f"frequency {spec.frequency!r}")
    territory = labels.get("Reference territory")
    if territory is not None:
        geo = _TERRITORY_OF_LABEL.get(territory)
        if geo is None:
            raise ValueError(f"unknown BPstat territory label {territory!r}")
        if geo != spec.geography:
            raise ValueError(f"{spec.id}: payload territory {territory!r} ({geo}) != registry "
                             f"geography {spec.geography!r}")
    elif spec.geography != "EA" \
            or (labels.get("Reference currency"), labels.get("Counterparty currency")) \
            != _CURRENCY_REF:
        raise ValueError(f"{spec.id}: no territory dimension and not the reviewed EUR/USD euro "
                         f"reference rate (geography EA): {labels!r}")


def _series_rows(doc: dict, members: list[SeriesSpec]) -> dict[str, tuple]:
    """spec.id -> (frequency, [(ISO date, value token | None, mapped flag | None), ...])."""
    ids, sizes = doc.get("id"), doc.get("size")
    dims_doc = doc.get("dimension")
    if not (isinstance(ids, list) and isinstance(sizes, list) and isinstance(dims_doc, dict)):
        raise ValueError("JSON-stat dataset without id/size/dimension")
    if len(ids) != len(sizes) or set(ids) != set(dims_doc) or ids.count(TIME_DIM) != 1:
        raise ValueError(f"JSON-stat id/size/dimension mismatch: {ids!r}")
    id_list = [str(_plain(i)) for i in ids]
    extents = [_int_token(s, "size entry") for s in sizes]
    if min(extents, default=0) < 1:
        raise ValueError(f"empty dimension in size {sizes!r}")
    dims = {d: _index_of(dims_doc[d]) for d in id_list}
    if [len(dims[d]) for d in id_list] != extents:
        raise ValueError("category index lengths do not match the declared extents")
    role = doc.get("role") or {}
    if role.get("time") != [TIME_DIM]:
        raise ValueError(f"JSON-stat role.time must be ['reference_date'], got {role!r}")
    n_cells = 1
    for n in extents:
        n_cells *= n
    values = _cells_column(doc["value"], n_cells, "value")
    statuses = _cells_column(doc.get("status"), n_cells, "status") \
        if doc.get("status") is not None else [None] * n_cells
    strides = [1] * len(id_list)
    for i in range(len(id_list) - 2, -1, -1):
        strides[i] = strides[i + 1] * extents[i + 1]
    t_axis = id_list.index(TIME_DIM)
    dates = dims[TIME_DIM]
    for d in dates:
        m = _DATE_RE.fullmatch(d)
        if not m:
            raise ValueError(f"reference_date entry {d!r} is not an ISO date")
        date(int(m.group(1)), int(m.group(2)), int(m.group(3)))  # ValueError if impossible
    if dates != sorted(dates):
        raise ValueError("reference_date axis is not strictly chronological")

    ext = doc.get("extension")
    if not isinstance(ext, dict) or not isinstance(ext.get("series"), list):
        raise ValueError("payload without extension.series (cannot map series to cells)")
    by_id: dict[int, list[tuple[str, str]]] = {}
    for entry in ext["series"]:
        sid = _int_token(entry.get("id"), "extension.series id")
        pins = []
        for p in entry.get("dimension_category") or []:
            pins.append((str(_int_token(p.get("dimension_id"), "dimension id")),
                         str(_int_token(p.get("category_id"), "category id"))))
        if sid in by_id or len(pins) != len({d for d, _ in pins}):
            raise ValueError(f"extension.series entry for {sid} is duplicated or double-pinned")
        by_id[sid] = pins

    out: dict[str, tuple] = {}
    blocks: set[tuple] = set()
    for spec in members:
        sid, _, _ = parse_native_code(spec.native_code)
        if sid not in by_id:
            raise ValueError(f"requested series {sid} ({spec.id}) is absent from this payload")
        pins = dict(by_id[sid])
        if set(pins) != set(id_list) - {TIME_DIM}:
            raise ValueError(f"series {sid} pins {sorted(pins)} but the payload dimensions are "
                             f"{sorted(set(id_list) - {TIME_DIM})}")
        block = tuple(dims[d].index(pins[d]) for d in id_list if d != TIME_DIM)
        if block in blocks:
            raise ValueError(f"series {sid} shares an identical cell block with another "
                             f"requested series (double-mapped payload)")
        blocks.add(block)
        _check_identity(spec, _labels_of(doc, pins, dims, dims_doc))
        pos = dict(zip([d for d in id_list if d != TIME_DIM], block))
        base = sum(pos[id_list[i]] * strides[i] for i in range(len(id_list))
                   if id_list[i] != TIME_DIM)
        rows = []
        for t, when in enumerate(dates):
            flat = base + t * strides[t_axis]
            token = values[flat]
            status = statuses[flat]
            if token is None:
                flag = map_bportugal_flag(status if status is None else _plain(status),
                                          value_present=False)
            else:
                token = _plain(token)
                if status is None:
                    raise ValueError(f"valued cell {token!r} without status at {when}")
                flag = map_bportugal_flag(_plain(status), value_present=True)
            rows.append((when, token, flag))
        out[spec.id] = (spec.frequency, rows)
    return out


def _period(iso: str, frequency: str) -> str:
    """Month-end ISO date -> canonical period label handed to validate(). Only 'M' is shipped
    in the registry today (monthly series end-dated); anything else raises for review."""
    if frequency == "M":
        return iso[:7]
    raise ValueError(f"BPstat adapter reviewed monthly series only; frequency {frequency!r} "
                     f"must be reviewed before mapping periods")
