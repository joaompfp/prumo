"""REN (Redes Energéticas Nacionais) DataHub source adapter: the servicebus JSON API.

    GET https://servicebus.ren.pt/datahubapi/electricity/ElectricityConsumptionSupplyMonthly
        ?culture=pt-PT&year=<YYYY>&month=<MM>     (monthly energy balance, GWh series)
    GET https://servicebus.ren.pt/datahubapi/electricity/ElectricityMarketPricesMonthly
        ?culture=pt-PT&year=<YYYY>&month=<MM>     (monthly market prices, EUR/MWh series)

Unauthenticated JSON API (culture MUST be pt-PT or en-US; anything else is HTTP 400). `year` and
`month` are always passed explicitly: the endpoint silently serves a different vintage when they
are omitted (observed 2026-11-11: no params answered previous-year-column semantics, not the
latest month). Recorded evidence in tests/ingest/fixtures/ren/ (2026-11-11).

Registry contract (`SeriesSpec.native_code`):

    ElectricityConsumptionSupplyMonthly:<TYPE>       e.g. ...:CONSUMO, ...:EOLICA
    ElectricityMarketPricesMonthly:PT.Preço Médio    (the price series)

`SeriesSpec.url` is the series' public portal page. One request per (endpoint, month); the
default period range is the last 13 COMPLETED months (the running month is never requested —
it is partial and unpublished months answer 404). REN's terms are restrictive (registry: the
source stays redistribution_ok=false): this adapter collects for internal verification only and
the 0005 serving licence gate keeps verified data withheld.

Response shapes (fail-closed):
  balance: a bare JSON array of {"monthly_Accumulation": <number>, "type": "<TOKEN>"}; NO unit,
    period or status field anywhere (the three surfaces are absent, not guessed): the period is
    taken from the validated request, the unit from the registry (publisher unit evidence: the
    portal page and CSV header "[GWh]"), and every row's flag is 'normal' by declaration.
    Values are preserved as publisher tokens via json.loads with parse_int/parse_float TAGGING
    JSON numbers as _Num (a str subclass internal to this module): a JSON string is NEVER a
    number token ('"04442"' would otherwise parse as '04442' and even Decimal-verify against
    the independent channel). Balance 'type' labels must be genuine JSON strings, and tokens
    leave this module only as plain str. The selected types must each appear exactly once;
    UNSELECTED type rows (e.g. retired CARVAO in 2010) are skipped, never rejected for not
    being in our map.
  prices: a JSON object with exactly one key — the lowercase Portuguese month name ("setembro")
    cross-checked against the requested month — whose block holds per-country dicts
    {"PT": {"Fora Vazio": ..., "Preço Médio": ..., "Vazio": ...}, "ES": {...}} plus the observed
    sibling surfaces 'Separação de mercados [%]' and 'Capacidade [MW]' (Importação/Exportação).
  unpublished month: HTTP 404 {"message":"No data available"} — fail closed like every non-2xx.

Raises on: markup/invalid JSON, duplicate JSON keys, wrong top-level structure, missing/unknown
entry fields, quoted (JSON string) or non-numeric value tokens, numeric or duplicate type
labels, a missing selected type, month-key/request mismatch, unknown block surfaces and any
non-2xx response handed to parse.
"""
import json
import re
from collections.abc import Iterable, Iterator
from datetime import date

from ingest.http import Http
from ingest.models import SeriesSpec
from ingest.sources import RawResponse
from ingest.validate import RawRow

API_BASE = "https://servicebus.ren.pt/datahubapi/electricity"
BALANCE_ENDPOINT = "ElectricityConsumptionSupplyMonthly"
PRICES_ENDPOINT = "ElectricityMarketPricesMonthly"
PRICE_SELECTOR = "PT.Preço Médio"
DEFAULT_MONTHS = 13

# Lowercase Portuguese month names under culture=pt-PT (archived evidence: 'setembro').
PT_MONTHS = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
             "setembro", "outubro", "novembro", "dezembro")

_TYPE_TOKEN = re.compile(r"[A-Z][A-Z0-9_]*")
_YEAR = re.compile(r"\d{4}")
_MONTH = re.compile(r"(0[1-9]|1[0-2])")
_NUMBER = re.compile(r"-?\d+(\.\d+)?")  # observed API/CSV token grammar (decimal '.', ints/floats)

# Price block surfaces seen in every archived response (2026-09): per-country metric dicts plus
# two scalar blocks. Any other surface is a format change, never guessed at.
_PRICE_COUNTRY_KEYS = frozenset({"Fora Vazio", "Preço Médio", "Vazio"})
_PRICE_SCALAR_KEYS = frozenset({"Separação de mercados [%]"})
_PRICE_BLOCK_KEYS = frozenset({"Capacidade [MW]"})
_PRICE_CAPACITY_KEYS = frozenset({"Importação", "Exportação"})

# (endpoint, selector): selector = balance TYPE token or PRICE_SELECTOR.
Key = tuple[str, str]


def parse_native_code(code: str | None) -> Key:
    """'ElectricityConsumptionSupplyMonthly:<TYPE>' | 'ElectricityMarketPricesMonthly:PT.Preço
    Médio' -> (endpoint, selector); ValueError if malformed. 'PT.Preço Médio' is the only
    reviewed price selector: adding another needs its own review, not a guess."""
    endpoint, sep, selector = (code or "").partition(":")
    if not sep or not selector:
        raise ValueError(f"REN native_code must be '<endpoint>:<selector>', got {code!r}")
    if endpoint == BALANCE_ENDPOINT:
        if not _TYPE_TOKEN.fullmatch(selector):
            raise ValueError(f"REN balance TYPE token must be uppercase ASCII, got {selector!r}")
        return endpoint, selector
    if endpoint == PRICES_ENDPOINT and selector == PRICE_SELECTOR:
        return endpoint, selector
    raise ValueError(f"unknown REN endpoint/selector in native_code {code!r}")


def completed_months(today: date, count: int = DEFAULT_MONTHS) -> list[str]:
    """The `count` most recent COMPLETED months, ascending 'YYYY-MM'; the running month is
    excluded (it is partial). 2026-11-11 -> ['2025-10', ..., '2026-10'] (13 completed months)."""
    if count < 1:
        raise ValueError(f"count must be >= 1, got {count}")
    out = []
    for i in range(count, 0, -1):
        y, m = today.year, today.month - i
        y, m = y + (m - 1) // 12, (m - 1) % 12 + 1
        out.append(f"{y}-{m:02d}")
    return out


def _period_of(params: dict | None, url: str) -> str:
    """The month a response answers for, from the request that produced it (the balance/price
    payloads carry NO period surface of their own — REN pins the month only in the request, so
    the period is the validated request, never a guess from the payload)."""
    if not isinstance(params, dict):
        raise ValueError(f"REN response for {url!r} carries no request params: the period is "
                         "unidentifiable")
    if params.get("culture") != "pt-PT":
        raise ValueError(f"REN request params must ask culture=pt-PT, got {params!r}")
    year, month = str(params.get("year", "")), str(params.get("month", ""))
    if not _YEAR.fullmatch(year) or not _MONTH.fullmatch(month):
        raise ValueError(f"REN request params must pin an explicit year and month, got {params!r}")
    return f"{year}-{month}"


def _endpoint_of_url(url: str) -> str:
    for endpoint in (BALANCE_ENDPOINT, PRICES_ENDPOINT):
        if url == f"{API_BASE}/{endpoint}" or url.startswith(f"{API_BASE}/{endpoint}?"):
            return endpoint
    raise ValueError(f"REN response URL is not a known endpoint: {url!r}")


def _no_duplicate_keys(pairs: list) -> dict:
    keys = [k for k, _ in pairs]
    if len(set(keys)) != len(keys):
        raise ValueError(f"REN payload has duplicate keys {sorted(set(keys))[:5]}")
    return dict(pairs)


class _Num(str):
    """Internal JSON-number tag: json.loads(parse_int=parse_float=_Num) marks real JSON number
    tokens so a quoted string can never be confused with a publisher number. Never leaves this
    module as a subclass: _token coerces to plain str before any RawRow is built."""


def _loads(body: bytes, what: str):
    head = body[:64].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    if head.startswith(b"<"):
        raise ValueError(f"REN {what} answered markup, not JSON: {body[:80]!r}")
    try:
        return json.loads(body, parse_int=_Num, parse_float=_Num,
                          object_pairs_hook=_no_duplicate_keys)
    except (ValueError, UnicodeDecodeError) as e:
        raise ValueError(f"REN {what} is not valid JSON: {e}") from e


def _token(v, what: str) -> str:
    """A publisher number token: a JSON NUMBER (tagged _Num by _loads; a raw JSON string is
    rejected even when numeric-shaped), strict decimal-'.' grammar (evidence: integers,
    '143.9', negative '-263'). Returned as a plain str (the subclass must not leak: only
    genuine str values reach RawRow/validation)."""
    if type(v) is not _Num or not _NUMBER.fullmatch(v):
        raise ValueError(f"{what} must be a number token, got {v!r}")
    return str(v)


def _check_non2xx(resp: RawResponse) -> None:
    if not 200 <= resp.status < 300:
        raise ValueError(f"REN response for {resp.url!r} answered HTTP {resp.status} "
                         "(fail closed on every non-2xx, incl. the unpublished-month 404)")


def parse_balance_body(body: bytes) -> list[tuple[str, str]]:
    """The balance payload as (type, token) pairs in payload order, strictly checked."""
    doc = _loads(body, "balance")
    if not isinstance(doc, list):
        raise ValueError(f"REN balance payload must be a JSON array, got {type(doc).__name__}")
    seen: set[str] = set()
    out = []
    for entry in doc:
        if not isinstance(entry, dict) or set(entry) != {"monthly_Accumulation", "type"}:
            raise ValueError(f"REN balance entry must be exactly "
                             f"{{'monthly_Accumulation', 'type'}}, got {entry!r}")
        token = _token(entry["monthly_Accumulation"], "monthly_Accumulation")
        rtype = entry["type"]
        if type(rtype) is not str or not rtype.strip():  # a JSON number is not a label
            raise ValueError(f"REN balance type must be a non-empty JSON string, got {rtype!r}")
        if rtype in seen:
            raise ValueError(f"REN balance payload repeats type {rtype!r}")
        seen.add(rtype)
        out.append((rtype, token))
    return out


def parse_prices_body(body: bytes, period: str) -> str:
    """The PT 'Preço Médio' token of the prices payload; the single month key must equal the
    Portuguese month name of the requested period (cross-check against the request)."""
    doc = _loads(body, "prices")
    if not isinstance(doc, dict) or len(doc) != 1:
        raise ValueError(f"REN prices payload must be an object with one month key, got {doc!r}")
    (month_key, block), = doc.items()
    y, m = period.split("-")
    if month_key != PT_MONTHS[int(m) - 1]:
        raise ValueError(f"REN prices month key {month_key!r} != the requested {period} "
                         f"({PT_MONTHS[int(m) - 1]!r})")
    if not isinstance(block, dict) or not {"PT", "ES"} <= set(block):
        raise ValueError(f"REN prices block lacks PT/ES: {block!r}")
    unknown = set(block) - {"PT", "ES"} - _PRICE_SCALAR_KEYS - _PRICE_BLOCK_KEYS
    if unknown:
        raise ValueError(f"REN prices block carries unreviewed surfaces {sorted(unknown)}")
    for country in ("PT", "ES"):
        metrics = block[country]
        if not isinstance(metrics, dict) or set(metrics) != _PRICE_COUNTRY_KEYS:
            raise ValueError(f"REN prices {country} block must hold {_PRICE_COUNTRY_KEYS}, "
                             f"got {metrics!r}")
        for name, value in metrics.items():
            _token(value, f"{country}.{name}")
    if "Capacidade [MW]" in block:
        cap = block["Capacidade [MW]"]
        if not isinstance(cap, dict) or set(cap) != _PRICE_CAPACITY_KEYS:
            raise ValueError(f"REN prices capacity block must hold {_PRICE_CAPACITY_KEYS}, "
                             f"got {cap!r}")
        for name, value in cap.items():
            _token(value, f"Capacidade [MW].{name}")
    for name in _PRICE_SCALAR_KEYS & set(block):
        _token(block[name], name)
    return _token(block["PT"]["Preço Médio"], "PT.Preço Médio")  # plain str; y is echoed in
    # neither payload nor answer; see docstring


class RenSource:
    """REN servicebus JSON source. `periods` (constructor) makes the requested month range
    explicit and reproducible; the default is the last 13 COMPLETED months at construction —
    the running month is never requested (partial/unpublished data answers 404)."""

    name = "ren"
    expected_format = "json"

    def __init__(self, periods: Iterable[str] | None = None, *, today: date | None = None):
        if periods is None:
            periods = completed_months(today or date.today(), DEFAULT_MONTHS)
        self.periods = tuple(sorted(self._validate_periods(periods)))

    @staticmethod
    def _validate_periods(periods: Iterable[str]) -> list[str]:
        out = []
        for p in periods:
            y, sep, m = str(p).partition("-")
            if not sep or not _YEAR.fullmatch(y) or not _MONTH.fullmatch(m):
                raise ValueError(f"REN periods must be 'YYYY-MM' with a valid month, got {p!r}")
            out.append(f"{y}-{m}")
        if len(set(out)) != len(out):
            raise ValueError(f"REN periods contain duplicates: {sorted(out)}")
        if not out:
            raise ValueError("REN source needs at least one requested month")
        return out

    def fetch(self, specs: list[SeriesSpec], http: Http) -> Iterator[RawResponse]:
        timeouts = {s.source.timeout_s for s in specs}
        if len(timeouts) != 1:
            raise ValueError(f"REN fetch over mixed source timeouts: {timeouts!r}")
        (timeout,) = timeouts
        endpoints = sorted({parse_native_code(s.native_code)[0] for s in specs})
        for period in self.periods:
            year, month = period.split("-")
            for endpoint in endpoints:
                params = {"culture": "pt-PT", "year": year, "month": month}
                url = f"{API_BASE}/{endpoint}"
                # no timeout kwarg when the registry declares none: older Http doubles keep
                # working (the INE/BPstat pattern).
                r = http.get(url, params=params) if timeout is None else \
                    http.get(url, params=params, timeout=timeout)
                yield RawResponse(url=r.url, params=params, status=r.status, body=r.body)

    def parse(self, specs: list[SeriesSpec],
              responses: list[RawResponse]) -> dict[str, list[RawRow]]:
        """Parse archived responses. Each response's period is reconstructed from its VALIDATED
        REQUEST params (the payloads carry no period surface) and deliberately NOT re-checked
        against self.periods: parse() must also replay recorded/archived response sets, while
        requested-range coverage is guaranteed by fetch() (exactly one response per
        (endpoint, requested month)) plus the pipeline's failed-fetch on any mid-stream
        exception. Ambiguity still fails closed: two responses for the same (endpoint, month)
        raise."""
        wanted = {parse_native_code(s.native_code): s for s in specs}
        if len(wanted) != len(specs):
            raise ValueError("duplicate native_code among REN specs")
        rows: dict[str, list[RawRow]] = {s.id: [] for s in specs}
        balance_types = {t for (e, t) in wanted if e == BALANCE_ENDPOINT}
        seen_periods: dict[str, set[str]] = {BALANCE_ENDPOINT: set(), PRICES_ENDPOINT: set()}
        for i, resp in enumerate(responses):
            _check_non2xx(resp)
            endpoint = _endpoint_of_url(resp.url)
            period = _period_of(resp.params, resp.url)
            if period in seen_periods[endpoint]:
                raise ValueError(f"two REN {endpoint} responses for the same month {period}")
            seen_periods[endpoint].add(period)
            if endpoint == BALANCE_ENDPOINT:
                if not balance_types:
                    raise ValueError("balance response but no REN balance series requested")
                found = {}
                for rtype, token in parse_balance_body(resp.body):
                    key = (endpoint, rtype)
                    if key in wanted:
                        found[rtype] = token
                    # unselected type rows (historically valid or retired) are skipped,
                    # never rejected for not being in our map
                missing = balance_types - set(found)
                if missing:
                    raise ValueError(f"REN balance {period} lacks selected type(s) "
                                     f"{sorted(missing)}")
                for rtype, token in found.items():
                    rows[wanted[(endpoint, rtype)].id].append(
                        RawRow(period_raw=period, value_raw=token, unit_raw=None,
                               flag_raw="normal", response_index=i))
            else:
                price_specs = [s for (e, _), s in wanted.items() if e == PRICES_ENDPOINT]
                if not price_specs:
                    raise ValueError("prices response but no REN price series requested")
                token = parse_prices_body(resp.body, period)
                for spec in price_specs:
                    rows[spec.id].append(RawRow(period_raw=period, value_raw=token,
                                                unit_raw=None, flag_raw="normal",
                                                response_index=i))
        return rows
