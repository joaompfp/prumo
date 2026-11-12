"""E-REDES Open Data Portal source adapter (OpenDataSoft explore v2.1 JSON records API).

    GET https://e-redes.opendatasoft.com/api/explore/v2.1/catalog/datasets/<dataset>
        -> dataset metadata (identity, native fields/labels, licence)
    GET .../datasets/<dataset>/records?where=datahora >= "<day>" AND datahora < "<next day>"
        &order_by=datahora&limit=100[&offset=...]
        -> one UTC day of native 15-minute records per page set

Native scope (Task 16): dataset energia-produzida-total-nacional, fields dgm/pre/total — the
metadata labels ('Market (kWh)', 'Special Regime (kWh)', 'Total (kWh)') say the values are
energy per 15-minute interval in kWh; they are stored verbatim, never rescaled, clamped (a
negative dgm is native and valid) or summed locally. dgm/pre/total are distribution-side
E-REDES concepts and are NOT equated with REN transmission concepts.

`SeriesSpec.native_code` is '<dataset>:<field>' with the production dataset and dgm/pre/total
the only reviewed combinations (anything else fails closed until separately reviewed).

Windows: the constructor takes an EXPLICIT [from_ts, to_ts) window of canonical UTC day
boundaries ('YYYY-MM-DDT00:00:00+00:00') for replay/catch-up (e.g. from 2026-04-01 onward), or
none for the default safe bounded refresh of the last 3 complete UTC days. Each day is
requested separately (96 native quarter-hour records each), so neither the 100-record page
limit nor the 10000 offset cap can ever truncate a window: page sets are asserted complete
(total_count constant across pages, offsets contiguous, result count == total_count) and any
impossible density fails closed instead of silently stopping at 100 or 10000.

Fetch yields every response verbatim (metadata included); parse() rebuilds windows from the
VALIDATED request params (where), asserts per-window completeness/order/identity, reads numbers
as tagged JSON number tokens (a quoted string is never a number token; the exact publisher
token reaches RawRow as a plain str, float tails preserved), and fail-closes on metadata drift
(dataset id, datahora type, field types/labels, licence, publisher), unknown record keys, a
non-canonical or duplicated datahora, or inconsistency between the dia/mes/ano/date/time echo
columns and datahora. No status/quality surface exists on this dataset, so flag_raw=None.

Recorded evidence: tests/ingest/fixtures/eredes/ (2026-11-12, MANIFEST.json). Cadence and units
are publisher facts from the metadata; the independent verification channel is the same
portal's /exports/csv (different endpoint AND format) — see ingest/verifiers/eredes.py.
"""
import json
import re
from collections.abc import Iterator
from datetime import date, timedelta

from ingest.http import Http
from ingest.models import SeriesSpec
from ingest.sources import RawResponse
from ingest.validate import RawRow

API_BASE = "https://e-redes.opendatasoft.com/api/explore/v2.1/catalog/datasets"
PRODUCTION_DATASET = "energia-produzida-total-nacional"
# native field -> genuine metadata label (fixture metadata.body, 2026-11-12); the labels are
# the unit evidence, so a label drift is a format change, never a relabel.
FIELD_LABELS = {"dgm": "Market (kWh)", "pre": "Special Regime (kWh)", "total": "Total (kWh)"}
RECORD_KEYS = frozenset({"datahora", "dia", "mes", "ano", "date", "time", *FIELD_LABELS})
PAGE_SIZE = 100  # OpenDataSoft v2.1 records page maximum
OFFSET_CAP = 10000  # OpenDataSoft v2.1 hard cap: offset + limit beyond this fails
DEFAULT_RECENT_DAYS = 3  # portal publishes daily; 3 complete UTC days => bounded overlap

_KEY = re.compile(r"[a-z0-9][a-z0-9-]*")
_DAY_TS = re.compile(r"(\d{4})-(\d{2})-(\d{2})T00:00:00\+00:00")
_WHERE = re.compile(r'datahora >= "(\d{4}-\d{2}-\d{2})" AND datahora < "(\d{4}-\d{2}-\d{2})"')
# Canonical PT15M record timestamp (structure only; the full Gregorian/quarter rule is
# enforced downstream by validate->normalize_period).
_DATAHORA = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\+00:00")
_NUMBER = re.compile(r"-?[0-9]+(\.[0-9]+)?")  # observed token grammar (decimal '.', float tails)


def parse_native_code(code: str | None) -> tuple[str, str]:
    """'<dataset>:<field>' -> (dataset, field); the production dataset and dgm/pre/total are
    the only reviewed combinations (fail closed on anything else)."""
    dataset, sep, field = (code or "").partition(":")
    if not sep or not dataset or not field or ":" in field:
        raise ValueError(f"E-REDES native_code must be '<dataset>:<field>', got {code!r}")
    if dataset != PRODUCTION_DATASET or not _KEY.fullmatch(dataset):
        raise ValueError(f"unreviewed E-REDES dataset in native_code {code!r}")
    if field not in FIELD_LABELS:
        raise ValueError(f"unreviewed E-REDES field in native_code {code!r}")
    return dataset, field


class _Num(str):
    """Internal JSON-number tag (json.loads parse_int/parse_float): marks genuine JSON number
    tokens so a quoted string can never pass as a publisher number. Never leaves this module as
    a subclass: tokens are coerced to plain str before any RawRow is built."""


def _no_duplicate_keys(pairs: list) -> dict:
    keys = [k for k, _ in pairs]
    if len(set(keys)) != len(keys):
        raise ValueError(f"E-REDES payload has duplicate keys {sorted(set(keys))[:5]}")
    return dict(pairs)


def _loads(body: bytes, what: str):
    head = body[:64].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    if head.startswith(b"<"):
        raise ValueError(f"E-REDES {what} answered markup, not JSON: {body[:80]!r}")
    try:
        return json.loads(body, parse_int=_Num, parse_float=_Num,
                          object_pairs_hook=_no_duplicate_keys)
    except (ValueError, UnicodeDecodeError) as e:
        raise ValueError(f"E-REDES {what} is not valid JSON: {e}") from e


def _token(v, what: str) -> str:
    """A publisher number token: a JSON NUMBER (tagged), strict grammar; plain str out."""
    if type(v) is not _Num or not _NUMBER.fullmatch(v):
        raise ValueError(f"{what} must be a number token, got {v!r}")
    return str(v)


def _text(v, what: str) -> str:
    if type(v) is not str or not v:
        raise ValueError(f"{what} must be a non-empty JSON string, got {v!r}")
    return v


def _total_count(doc, what: str) -> int:
    tc = doc.get("total_count") if isinstance(doc, dict) else None
    if type(tc) is not _Num or not re.fullmatch(r"[0-9]+", tc):
        raise ValueError(f"E-REDES {what} total_count must be a JSON integer, got {tc!r}")
    return int(tc)


def _check_non2xx(resp: RawResponse) -> None:
    if not 200 <= resp.status < 300:
        raise ValueError(f"E-REDES response for {resp.url!r} answered HTTP {resp.status} "
                         "(fail closed on every non-2xx)")


def _assert_metadata(body: bytes, dataset: str) -> None:
    """Dataset identity, native fields/types/labels (unit evidence) and licence from genuine
    publisher metadata; any drift is a format change, never inferred around."""
    doc = _loads(body, "metadata")
    if not isinstance(doc, dict):
        raise ValueError(f"E-REDES metadata must be a JSON object, got {type(doc).__name__}")
    if _text(doc.get("dataset_id"), "dataset_id") != dataset:
        raise ValueError(f"E-REDES metadata dataset_id drifted from {dataset!r}")
    metas = doc.get("metas")
    default = metas.get("default") if isinstance(metas, dict) else None
    if not isinstance(default, dict):
        raise ValueError("E-REDES metadata lacks metas.default")
    if _text(default.get("license"), "license") != "CC BY 4.0" or \
            _text(default.get("license_url"), "license_url") != \
            "https://creativecommons.org/licenses/by/4.0/":
        raise ValueError("E-REDES licence metadata drifted from CC BY 4.0")
    if _text(default.get("publisher"), "publisher") != "E-REDES":
        raise ValueError("E-REDES publisher metadata drifted")
    fields = doc.get("fields")
    if not isinstance(fields, list):
        raise ValueError("E-REDES metadata lacks a fields list")
    by_name = {}
    for f in fields:
        if not isinstance(f, dict) or type(f.get("name")) is not str:
            raise ValueError(f"E-REDES metadata field entry malformed: {f!r}")
        by_name[f["name"]] = f
    ts = by_name.get("datahora")
    if ts is None or ts.get("type") != "datetime":
        raise ValueError("E-REDES datahora field missing or not datetime")
    for name, label in FIELD_LABELS.items():
        f = by_name.get(name)
        if f is None or f.get("type") != "double":
            raise ValueError(f"E-REDES field {name!r} missing or not double")
        if f.get("label") != label:
            raise ValueError(f"E-REDES field {name!r} label drifted from {label!r}: "
                             f"{f.get('label')!r}")


def _limit_of(params: dict) -> int:
    raw = params.get("limit")
    try:
        limit = int(raw)
    except (TypeError, ValueError):
        raise ValueError(f"E-REDES records params must pin an integer limit, got {raw!r}")
    if str(limit) != str(raw) or not (1 <= limit <= PAGE_SIZE):
        raise ValueError(f"E-REDES records limit must be in 1..{PAGE_SIZE}, got {raw!r}")
    return limit


def _day_of(where: str) -> date:
    m = _WHERE.fullmatch(where or "")
    if not m:
        raise ValueError(f"E-REDES records params must pin a day window, got where={where!r}")
    d1 = date.fromisoformat(m.group(1))
    d2 = date.fromisoformat(m.group(2))
    if d2 != d1 + timedelta(days=1):
        raise ValueError(f"E-REDES records window must span exactly one UTC day, got "
                         f"{where!r}")
    return d1


class EredesSource:
    """E-REDES OpenDataSoft JSON source. See the module docstring: explicit [from_ts, to_ts)
    day-aligned window for replay/catch-up (e.g. since 2026-04-01), or none for the default
    last-3-complete-UTC-days refresh. One metadata + one page set per (dataset, day)."""

    name = "eredes"
    expected_format = "json"

    def __init__(self, from_ts: str | None = None, to_ts: str | None = None, *,
                 today: date | None = None):
        if (from_ts is None) != (to_ts is None):
            raise ValueError("E-REDES needs both from_ts and to_ts, or neither")
        if from_ts is None:
            t = today or date.today()
            first = t - timedelta(days=DEFAULT_RECENT_DAYS)
            last = t  # today is running/partial; the portal lags ~1 day, overlap is bounded
        else:
            first, last = self._boundary(from_ts), self._boundary(to_ts)
        if last <= first:
            raise ValueError(f"E-REDES window must be non-empty [from, to), got "
                             f"{from_ts!r} .. {to_ts!r}")
        days, d = [], first
        while d < last:
            days.append(d)
            d += timedelta(days=1)
        self.days = tuple(days)

    @staticmethod
    def _boundary(ts: str) -> date:
        m = _DAY_TS.fullmatch(str(ts))
        if not m:
            raise ValueError(f"E-REDES window bounds must be canonical UTC day starts "
                             f"'YYYY-MM-DDT00:00:00+00:00', got {ts!r}")
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError as e:
            raise ValueError(f"E-REDES window bound is not a real date: {ts!r}") from e

    @staticmethod
    def _where(day: date) -> str:
        return f'datahora >= "{day.isoformat()}" AND ' \
               f'datahora < "{(day + timedelta(days=1)).isoformat()}"'

    def fetch(self, specs: list[SeriesSpec], http: Http) -> Iterator[RawResponse]:
        timeouts = {s.source.timeout_s for s in specs}
        if len(timeouts) != 1:
            raise ValueError(f"E-REDES fetch over mixed source timeouts: {timeouts!r}")
        (timeout,) = timeouts
        datasets = sorted({parse_native_code(s.native_code)[0] for s in specs})

        def get(url, params):
            r = http.get(url, params=params) if timeout is None else \
                http.get(url, params=params, timeout=timeout)
            return r

        for dataset in datasets:
            r = get(f"{API_BASE}/{dataset}", None)
            yield RawResponse(url=r.url, params=None, status=r.status, body=r.body)
            if not 200 <= r.status < 300:
                continue  # the pipeline classifies non-2xx; no point paging its records
            for day in self.days:
                offset = 0
                while True:
                    params = {"where": self._where(day), "order_by": "datahora",
                              "limit": PAGE_SIZE}
                    if offset:
                        params["offset"] = offset
                    r = get(f"{API_BASE}/{dataset}/records", params)
                    yield RawResponse(url=r.url, params=params, status=r.status, body=r.body)
                    if not 200 <= r.status < 300:
                        break  # classified failed-fetch by the pipeline
                    total = _total_count(_loads(r.body, "records"), "records")
                    offset += PAGE_SIZE
                    if offset >= total:
                        break
                    if offset + PAGE_SIZE > OFFSET_CAP:
                        raise ValueError(
                            f"E-REDES window at {day} has total_count {total}: beyond the "
                            f"OpenDataSoft {OFFSET_CAP} offset cap; split the window finer "
                            "(fail closed - never silently stop at 100/10000)")

    def parse(self, specs: list[SeriesSpec],
              responses: list[RawResponse]) -> dict[str, list[RawRow]]:
        wanted = {parse_native_code(s.native_code): s for s in specs}
        if len(wanted) != len(specs):
            raise ValueError("duplicate native_code among E-REDES specs")
        rows: dict[str, list[RawRow]] = {s.id: [] for s in specs}
        pages: dict[tuple[str, str], list[tuple[int, int, RawResponse]]] = {}
        n_metadata = 0
        for i, resp in enumerate(responses):
            _check_non2xx(resp)
            for dataset, _ in wanted:
                if resp.url == f"{API_BASE}/{dataset}":
                    n_metadata += 1
                    _assert_metadata(resp.body, dataset)
                    break
                if resp.url == f"{API_BASE}/{dataset}/records" or \
                        resp.url.startswith(f"{API_BASE}/{dataset}/records?"):
                    params = resp.params if isinstance(resp.params, dict) else {}
                    if params.get("order_by") != "datahora":
                        raise ValueError(f"E-REDES records response must order by datahora: "
                                         f"{params!r}")
                    where = params.get("where")
                    if not isinstance(where, str) or _WHERE.fullmatch(where) is None:
                        raise ValueError(f"E-REDES records params must pin a day window, got "
                                         f"where={where!r}")
                    pages.setdefault((dataset, where), []).append(
                        (int(params.get("offset", 0)), _limit_of(params), resp))
                    break
            else:
                raise ValueError(f"E-REDES response URL is not the metadata or records "
                                 f"endpoint of a requested dataset: {resp.url!r}")
        if n_metadata < 1:
            raise ValueError("E-REDES run lacks the dataset metadata response (every response "
                             "is archived evidence, metadata included)")
        resp_index = {id(resp): i for i, resp in enumerate(responses)}
        for (dataset, where), group in pages.items():
            group.sort(key=lambda p: p[0])
            limits = {lim for _, lim, _ in group}
            if len(limits) != 1:
                raise ValueError(f"E-REDES pages of {where!r} mix limit values {sorted(limits)}")
            (limit,) = limits
            offsets = [o for o, _, _ in group]
            if offsets != [limit * k for k in range(len(group))]:
                raise ValueError(f"E-REDES pages of {where!r} have non-contiguous offsets "
                                 f"{offsets} (limit {limit}) - a missing page fails the whole "
                                 "window")
            total = None
            chunk: list[tuple[dict, int]] = []  # (record, response_index), window order
            for offset, lim, resp in group:
                doc = _loads(resp.body, "records")
                tc = _total_count(doc, "records")
                if total is None:
                    total = tc
                elif tc != total:
                    raise ValueError(f"E-REDES total_count drifted mid-window {where!r}: "
                                     f"{total} -> {tc} (dataset changed during fetch)")
                results = doc.get("results")
                if not isinstance(results, list):
                    raise ValueError(f"E-REDES records page has no results list: {where!r}")
                chunk.extend((rec, resp_index[id(resp)]) for rec in results)
            if len(chunk) != total:
                raise ValueError(f"E-REDES window {where!r} is incomplete: {len(chunk)} "
                                 f"records for total_count {total} (an unhandled page cap or "
                                 "a lost page - fail closed, never truncate silently)")
            day = _day_of(where)
            prev = None
            for rec, i in chunk:
                if not isinstance(rec, dict) or set(rec) != RECORD_KEYS:
                    raise ValueError(f"E-REDES record keys drifted: {sorted(rec or {})!r}")
                t_raw = _text(rec["datahora"], "datahora")
                if not _DATAHORA.fullmatch(t_raw):
                    raise ValueError(f"E-REDES datahora is not the canonical UTC "
                                     f"quarter-hour spelling: {t_raw!r}")
                # echo-column consistency: dia/mes/ano/date/time must repeat datahora exactly
                if (_text(rec["date"], "date") != t_raw[:10]
                        or _text(rec["time"], "time") != t_raw[11:16]
                        or _text(rec["dia"], "dia") != t_raw[8:10]
                        or _text(rec["mes"], "mes") != t_raw[5:7]
                        or _text(rec["ano"], "ano") != t_raw[:4]):
                    raise ValueError(f"E-REDES record's dia/mes/ano/date/time echo columns "
                                     f"disagree with datahora {t_raw!r}")
                if date.fromisoformat(t_raw[:10]) != day:
                    raise ValueError(f"E-REDES record {t_raw!r} sits outside its requested "
                                     f"day window {where!r}")
                if prev is not None and t_raw <= prev:
                    raise ValueError(f"E-REDES records not strictly ascending/unique at "
                                     f"{t_raw!r} (duplicate or out-of-order timestamp)")
                prev = t_raw
                for field in FIELD_LABELS:
                    spec = wanted.get((dataset, field))
                    if spec is None:
                        continue  # an unselected but reviewed field: skipped, never rejected
                    rows[spec.id].append(
                        RawRow(period_raw=t_raw,
                               value_raw=_token(rec[field], field),
                               unit_raw=None, flag_raw=None, response_index=i))
        return rows
