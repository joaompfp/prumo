"""FRED (Federal Reserve Bank of St. Louis) source adapter: the API JSON channel.

    GET https://api.stlouisfed.org/fred/series?series_id=<CODE>&file_type=json&api_key=<KEY>
    GET https://api.stlouisfed.org/fred/series/observations?series_id=<CODE>&file_type=json
        &limit=100000[&offset=<N>]&api_key=<KEY>

(units=lin / output_type=1 / order_by=observation_date / sort_order=asc are the FRED defaults and
are ASSERTED in the payload — no aggregation or transformation is ever requested.)

Recorded evidence in tests/ingest/fixtures/fred/ (2026-11-12, sha256-pinned by MANIFEST.json;
byte copies of the Task-14 preflight originals): 12 active IMF Primary Commodity Prices globals,
monthly, NSA, decimal '.', geography WORLD (registry bindings and the 8 inactivated series are
documented in registry/unmapped-fred.md). The fredgraph.csv export channel is REJECTED as the
independent verifier (binary-float tails on 10/12 series, e.g. 70.51 vs 70.51000000000001 —
docs/superpowers/handoff/evidence/task-14-fred/csv-decimal-mismatches.json); Part B verifies
against the server-rendered https://fred.stlouisfed.org/data/<CODE> data table instead.

Credentials: FRED requires the key as a QUERY parameter. The key is passed explicitly
(`FredSource(api_key=...)`) or read from the FRED_API_KEY environment variable; the legacy
.fred_api_key file is NEVER read by this module. The key goes only into the outgoing wire
request. The YIELDED RawResponse is the archived identity that lands in the raw store, the DB
and events, so it is deliberately key-free: `api_key` is stripped from the final URL and
OMITTED from the archived params (documented in the fixture MANIFEST). A response whose body
contains the credential is refused BEFORE yield (raw bytes never archived, never mutated), and
http.get exceptions — which typically embed the full request URL including the key — are
re-raised as FredRequestError carrying only the exception type, the endpoint family and the
series id.

Metadata (GET /fred/series) is fetched and archived per series: the runtime unit comes from the
metadata's actual `units` label and is asserted against the registry unit (exact publisher
labels, e.g. 'U.S. Dollars per Metric Ton'); frequency must be Monthly/M and seasonal adjustment
NSA. `last_updated` stays metadata (shape-checked only) — it is NOT a per-observation release
date and is never copied onto rows. Observation values are JSON STRINGS here (unlike the
WorldBank/REN JSON-number payloads): the token is preserved verbatim as a plain str, FRED's '.'
missing marker becomes value_raw=None (quarantined non_numeric downstream; the 144 pre-1992
cells are kept, never truncated), and a JSON-number value would be an unknown primitive and
fails closed. FRED exposes NO per-observation status surface — flag_raw='normal' by explicit
declaration of the reviewed shape; any new per-observation field raises.

Fail-closed on: markup/invalid JSON, duplicate JSON keys, the API error shape, unknown
top-level/series/row fields, identity drift (requested vs payload series id, per-observation
realtime identical to its response envelope), duplicate dates, non month-first dates
(day != 01), count/offset/limit truncation, and page-order drift. parse() needs no HTTP or DB:
identity comes from the archived url/params (which must never carry an api_key).
"""
import json
import os
import re
from collections.abc import Iterator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from ingest.http import Http
from ingest.models import SeriesSpec
from ingest.sources import RawResponse
from ingest.validate import RawRow

API_BASE = "https://api.stlouisfed.org/fred"
OBS_LIMIT = 100000
ENV_VAR = "FRED_API_KEY"
MISSING = "."

_CODE = re.compile(r"[A-Z0-9]+")
_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_LAST_UPDATED = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[+-]\d{2}")

_META_TOP_KEYS = {"realtime_start", "realtime_end", "seriess"}
_META_SERIES_KEYS = {"id", "realtime_start", "realtime_end", "title", "observation_start",
                     "observation_end", "frequency", "frequency_short", "units", "units_short",
                     "seasonal_adjustment", "seasonal_adjustment_short", "last_updated",
                     "popularity", "notes"}
_META_SERIES_STR_KEYS = {"id", "realtime_start", "realtime_end", "title", "observation_start",
                         "observation_end", "frequency", "frequency_short", "units",
                         "units_short", "seasonal_adjustment", "seasonal_adjustment_short",
                         "last_updated", "notes"}
_OBS_TOP_KEYS = {"realtime_start", "realtime_end", "observation_start", "observation_end",
                 "units", "output_type", "file_type", "order_by", "sort_order", "count",
                 "offset", "limit", "observations"}
_OBS_ROW_KEYS = {"realtime_start", "realtime_end", "date", "value"}
_META_PARAMS = {"series_id", "file_type"}
_OBS_PARAMS = {"series_id", "file_type", "limit", "offset"}


class FredRequestError(ValueError):
    """A FRED request or response could not be completed/accepted. Messages never carry the
    credential, a request URL with query, or response body excerpts."""


def parse_native_code(code: str | None) -> str:
    """The FRED series id (e.g. 'PALUMUSDM') is the full publisher identity of a series."""
    if not isinstance(code, str) or not _CODE.fullmatch(code):
        raise ValueError(f"FRED native_code must be an uppercase FRED series id, got {code!r}")
    return code


def _no_duplicate_keys(pairs: list) -> dict:
    keys = [k for k, _ in pairs]
    if len(set(keys)) != len(keys):
        raise ValueError(f"FRED payload has duplicate keys {sorted(set(keys))[:5]}")
    return dict(pairs)


def _reject_constant(x: str):
    raise ValueError(f"FRED payload carries a non-JSON constant {x!r}")


def _loads(body: bytes, what: str):
    head = body[:64].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    if head.startswith(b"<"):
        raise ValueError(f"FRED {what} answered markup/HTML, not JSON: {body[:80]!r}")
    try:
        return json.loads(body, parse_constant=_reject_constant,
                          object_pairs_hook=_no_duplicate_keys)
    except (ValueError, UnicodeDecodeError) as e:
        raise ValueError(f"FRED {what} is not valid JSON: {e}") from e


def _is_int(v) -> bool:
    return type(v) is int


def _str(v, what: str) -> str:
    if type(v) is not str or not v.strip():
        raise ValueError(f"FRED {what} must be a non-empty JSON string, got {v!r}")
    return v


def _date(v, what: str, *, month_first: bool) -> str:
    s = _str(v, what)
    m = _DATE.fullmatch(s)
    if not m or not (1 <= int(m.group(2)) <= 12) or not (1 <= int(m.group(3)) <= 31):
        raise ValueError(f"FRED {what} is not a YYYY-MM-DD date, got {s!r}")
    if month_first and m.group(3) != "01":
        raise ValueError(f"FRED {what} must be a month-first date (day 01), got {s!r}")
    return s


def _metadata(body: bytes, code: str, what: str) -> dict:
    """The /fred/series payload of ONE series, strictly shaped; returns the checked metadata."""
    doc = _loads(body, f"{what} metadata")
    if isinstance(doc, dict) and "error_code" in doc:
        raise ValueError(f"FRED {what} metadata is an API error response")
    if not isinstance(doc, dict) or set(doc) != _META_TOP_KEYS:
        raise ValueError(f"FRED {what} metadata top-level keys drifted: "
                         f"{sorted(doc) if isinstance(doc, dict) else doc!r}")
    if not isinstance(doc["seriess"], list) or len(doc["seriess"]) != 1:
        raise ValueError(f"FRED {what} metadata must hold exactly one series entry")
    s = doc["seriess"][0]
    if not isinstance(s, dict) or not set(s) <= _META_SERIES_KEYS:
        raise ValueError(f"FRED {what} metadata series fields drifted: {sorted(s)!r}")
    for k in _META_SERIES_STR_KEYS & set(s):
        _str(s[k], f"{what} metadata {k}")
    if not _is_int(s.get("popularity")):
        raise ValueError(f"FRED {what} metadata popularity must be an int")
    sid = _str(s.get("id"), f"{what} metadata id")
    if sid != code:
        raise ValueError(f"FRED {what} metadata identity drift: payload id {sid!r} != the "
                         f"requested series {code!r}")
    if (s.get("frequency_short"), s.get("frequency")) != ("M", "Monthly"):
        raise ValueError(f"FRED {what} metadata frequency drifted: "
                         f"{s.get('frequency')!r}/{s.get('frequency_short')!r}")
    if (s.get("seasonal_adjustment_short"), s.get("seasonal_adjustment")) != \
            ("NSA", "Not Seasonally Adjusted"):
        raise ValueError(f"FRED {what} metadata seasonal adjustment drifted: "
                         f"{s.get('seasonal_adjustment')!r}")
    _date(str(s.get("observation_start")), f"{what} metadata observation_start",
          month_first=True)
    _date(str(s.get("observation_end")), f"{what} metadata observation_end", month_first=True)
    _date(str(s.get("realtime_start")), f"{what} metadata realtime_start", month_first=False)
    _date(str(s.get("realtime_end")), f"{what} metadata realtime_end", month_first=False)
    if s.get("realtime_start") != doc["realtime_start"] or \
            s.get("realtime_end") != doc["realtime_end"]:
        raise ValueError(f"FRED {what} metadata realtime identity drift between envelope and "
                         "series entry")
    if not _LAST_UPDATED.fullmatch(str(s.get("last_updated"))):
        raise ValueError(f"FRED {what} metadata last_updated drifted: "
                         f"{s.get('last_updated')!r}")  # shape-checked only; never a row datum
    return {"id": sid, "units": s["units"], "units_short": s["units_short"],
            "observation_start": s["observation_start"], "observation_end": s["observation_end"]}


def _observations(body: bytes, code: str, what: str) -> dict:
    """One /fred/series/observations page, strictly shaped; returns {count, offset, limit,
    realtime, rows[(date, token_or_None)]}."""
    doc = _loads(body, f"{what} observations")
    if isinstance(doc, dict) and "error_code" in doc:
        raise ValueError(f"FRED {what} observations is an API error response")
    if not isinstance(doc, dict) or set(doc) != _OBS_TOP_KEYS:
        raise ValueError(f"FRED {what} observations top-level keys drifted: "
                         f"{sorted(doc) if isinstance(doc, dict) else doc!r}")
    rts, rte = _str(doc["realtime_start"], f"{what} realtime_start"), \
        _str(doc["realtime_end"], f"{what} realtime_end")
    if (doc["units"], doc["file_type"], doc["order_by"], doc["sort_order"]) != \
            ("lin", "json", "observation_date", "asc"):
        raise ValueError(f"FRED {what} observations envelope drifted (units/file_type/order_by/"
                         f"sort_order): no aggregation or transform is ever requested")
    if not _is_int(doc["output_type"]) or doc["output_type"] != 1:
        raise ValueError(f"FRED {what} observations output_type drifted: {doc['output_type']!r}")
    for k in ("count", "offset", "limit"):
        if not _is_int(doc[k]) or doc[k] < 0:
            raise ValueError(f"FRED {what} observations {k} must be an int >= 0, got {doc[k]!r}")
    if doc["limit"] < 1:
        raise ValueError(f"FRED {what} observations limit must be positive")
    if not isinstance(doc["observations"], list):
        raise ValueError(f"FRED {what} observations must be a list")
    rows = []
    for row in doc["observations"]:
        if not isinstance(row, dict) or set(row) != _OBS_ROW_KEYS:
            raise ValueError(f"FRED {what} observation row fields drifted (a per-observation "
                             f"status surface would be unreviewed): {sorted(row)!r}")
        if (row["realtime_start"], row["realtime_end"]) != (rts, rte):
            raise ValueError(f"FRED {what} observation realtime identity drift within the page")
        d = _date(row["date"], f"{what} observation date", month_first=True)
        v = row["value"]
        if not isinstance(v, str):  # FRED value tokens are JSON STRINGS; a number is unknown
            raise ValueError(f"FRED {what} observation value must be a JSON string token, got "
                             f"{type(v).__name__} {v!r}")
        if v == "":
            raise ValueError(f"FRED {what} observation empty value token is not the reviewed "
                             "missing marker '.'")
        rows.append((d, None if v == MISSING else v))
    if len(rows) > doc["limit"]:
        raise ValueError(f"FRED {what} observations page holds {len(rows)} rows > limit "
                         f"{doc['limit']} (count drift)")
    if doc["offset"] < 0 or doc["offset"] > doc["count"] or \
            doc["offset"] + len(rows) > doc["count"]:
        raise ValueError(f"FRED {what} observations count/offset drift: offset "
                         f"{doc['offset']} + {len(rows)} rows > count {doc['count']} "
                         "(truncation)")
    return {"count": doc["count"], "offset": doc["offset"], "limit": doc["limit"],
            "realtime": (rts, rte), "rows": rows}


def _identify(resp: RawResponse, what: str) -> tuple[str, str, dict]:
    """(endpoint, series_id, key-free params) of an archived response from its url/params
    identity; any archived credential (`api_key` in params or URL query) is an archival leak
    and fails closed."""
    if not isinstance(resp.params, dict):
        raise ValueError(f"FRED {what} carries no archived params: the series identity is "
                         "unidentifiable")
    if "api_key" in resp.params or "api_key=" in resp.url:
        raise ValueError(f"FRED {what} url/params carry an api_key: credential leak in archived "
                         "identity")
    path = urlsplit(resp.url).path
    if path == "/fred/series":
        endpoint, allowed = "meta", _META_PARAMS
    elif path == "/fred/series/observations":
        endpoint, allowed = "obs", _OBS_PARAMS
    else:
        raise ValueError(f"FRED {what} URL is not a known endpoint: {resp.url!r}")
    if urlsplit(resp.url).netloc != "api.stlouisfed.org":
        raise ValueError(f"FRED {what} URL is not api.stlouisfed.org: {resp.url!r}")
    params = {k: str(v) for k, v in resp.params.items()}
    if set(params) > allowed or "series_id" not in params:
        raise ValueError(f"FRED {what} archived params drifted: {params!r}")
    q = dict(parse_qsl(urlsplit(resp.url).query))
    if any(q.get(k) != params[k] for k in params if k in q):
        raise ValueError(f"FRED {what} URL query disagrees with archived params: {resp.url!r} "
                         f"vs {params!r}")
    for k in ("limit", "offset"):
        if k in params and not re.fullmatch(r"[0-9]+", params[k]):
            raise ValueError(f"FRED {what} archived param {k!r} is not a non-negative int: "
                             f"{params[k]!r}")
    return endpoint, parse_native_code(params["series_id"]), params


class FredSource:
    """FRED JSON source. Full monthly history per unique series: one metadata response plus one
    (or, past OBS_LIMIT, several offset-paginated) observations responses, in sorted code order.
    """

    name = "fred"
    expected_format = "json"

    def __init__(self, api_key: str | None = None):
        """api_key explicitly, else the FRED_API_KEY environment variable. The legacy
        .fred_api_key file is never read here. The key is stored privately and never rendered
        into repr/logs/archived identity."""
        key = api_key if api_key is not None else os.environ.get(ENV_VAR)
        if not isinstance(key, str) or not key.strip():
            raise ValueError(
                f"FRED needs an API key: pass api_key=... or set the {ENV_VAR} environment "
                "variable (this module never reads .fred_api_key)")
        self._api_key = key

    def _get(self, http: Http, endpoint: str, params: dict, timeout: float | None,
             code: str) -> RawResponse:
        """One request with the credential on the wire, yielding a key-free RawResponse. Raises
        FredRequestError (sanitized) on network failure or a response echoing the credential."""
        wire = {**params, "api_key": self._api_key}
        url = f"{API_BASE}/{endpoint}"
        try:
            r = http.get(url, params=wire) if timeout is None else \
                http.get(url, params=wire, timeout=timeout)
        except Exception as e:
            raise FredRequestError(f"FRED {endpoint} request for series {code} failed: "
                                   f"{type(e).__name__}") from None
        if self._api_key.encode() in r.body:
            raise FredRequestError(f"FRED {endpoint} response for series {code} echoes the API "
                                   "credential: refusing to archive the raw bytes")
        final = self._strip_key(r.url)
        return RawResponse(url=final, params=dict(params), status=r.status, body=r.body)

    def _strip_key(self, url: str) -> str:
        """The final URL without the api_key query parameter; a key that survives removal is an
        archival-leak error, never a rewrite of the publisher bytes."""
        parts = urlsplit(url)
        q = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if k != "api_key"]
        out = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q),
                          parts.fragment))
        if self._api_key in out:
            raise FredRequestError("FRED final URL still contains the credential after api_key "
                                   "removal: refusing to archive it")
        return out

    def fetch(self, specs: list[SeriesSpec], http: Http) -> Iterator[RawResponse]:
        timeouts = {s.source.timeout_s for s in specs}
        if len(timeouts) != 1:
            raise ValueError(f"FRED fetch over mixed source timeouts: {timeouts!r}")
        (timeout,) = timeouts
        for code in sorted({parse_native_code(s.native_code) for s in specs}):
            yield self._get(http, "series", {"series_id": code, "file_type": "json"}, timeout,
                            code)
            offset = 0
            while True:
                params = {"series_id": code, "file_type": "json", "limit": str(OBS_LIMIT)}
                if offset:
                    params["offset"] = str(offset)
                resp = self._get(http, "series/observations", params, timeout, code)
                yield resp  # archived the moment it arrives; a later failure keeps the evidence
                if not 200 <= resp.status < 300:
                    break  # the pipeline classifies it; never retry/filter here
                page = _observations(resp.body, code, f"fetch ({code})")
                offset += len(page["rows"])
                if offset >= page["count"]:
                    break
                if not page["rows"]:
                    raise FredRequestError(f"FRED observations for {code}: pagination makes no "
                                           "progress (empty page before count is reached)")

    def parse(self, specs: list[SeriesSpec],
              responses: list[RawResponse]) -> dict[str, list[RawRow]]:
        """Map archived responses to per-series rows. Metadata is mandatory: unit_raw is the
        metadata's ACTUAL units label and must equal the registry unit (fail closed otherwise).
        RawRow.response_index points at the OBSERVATIONS response the row came from; metadata
        responses stay archived but carry no rows. See the module docstring for the contract."""
        wanted: dict[str, list[SeriesSpec]] = {}
        for s in specs:
            wanted.setdefault(parse_native_code(s.native_code), []).append(s)
        rows: dict[str, list[RawRow]] = {s.id: [] for s in specs}
        metas: dict[str, dict] = {}
        pages: dict[str, list[tuple[int, list, int, tuple]]] = {}
        for i, resp in enumerate(responses):
            what = f"response[{i}]"
            if not 200 <= resp.status < 300:
                raise ValueError(f"FRED {what} for {resp.url!r} answered HTTP {resp.status} "
                                 "(fail closed on every non-2xx)")
            endpoint, code, params = _identify(resp, what)
            if code not in wanted:
                raise ValueError(f"FRED {what} answered unrequested series {code!r}")
            if endpoint == "meta":
                if code in metas:
                    raise ValueError(f"FRED metadata for {code} arrived twice")
                metas[code] = _metadata(resp.body, code, what)
            else:
                page = _observations(resp.body, code, what)
                # request/payload identity: the archived params must declare the same
                # limit/offset the payload reports
                if params.get("limit") != str(page["limit"]) or \
                        params.get("offset", "0") != str(page["offset"]):
                    raise ValueError(f"FRED {what} archived limit/offset drift: params "
                                     f"{resp.params!r} vs payload limit {page['limit']} offset "
                                     f"{page['offset']}")
                pages.setdefault(code, []).append(
                    (page["offset"], page["rows"], i, page["realtime"]))
        for code, spec_list in wanted.items():
            if code not in metas:
                raise ValueError(f"FRED series {code}: no metadata response archived (the "
                                 "runtime unit comes from the metadata)")
            meta = metas[code]
            for s in spec_list:
                if meta["units"] != s.unit:
                    raise ValueError(f"FRED series {code} metadata units {meta['units']!r} != "
                                     f"registry unit of {s.id} {s.unit!r} (fail closed, never "
                                     "relabel fresh data)")
            seen_dates: set[tuple[str, str]] = set()
            expected_offset = 0
            realtime = None
            for offset, page_rows, i, rt in pages.get(code, []):
                if offset != expected_offset:
                    raise ValueError(f"FRED {code} pages are not contiguous: expected offset "
                                     f"{expected_offset}, got {offset}")
                if realtime is not None and rt != realtime:
                    raise ValueError(f"FRED {code} realtime identity drifts across pages")
                realtime = rt
                expected_offset += len(page_rows)
                for d, token in page_rows:
                    period = d[:7]  # month-first date, asserted day==01 -> canonical YYYY-MM
                    for s in spec_list:
                        key = (s.id, period)
                        if key in seen_dates:
                            raise ValueError(f"FRED duplicate row for {s.id} date {period}")
                        seen_dates.add(key)
                        rows[s.id].append(RawRow(period_raw=period, value_raw=token,
                                                 unit_raw=meta["units"], flag_raw="normal",
                                                 response_index=i))
        return rows
