"""Independent verifier for REN DataHub (spec 6b):

    collector: servicebus JSON API
        servicebus.ren.pt/datahubapi/electricity/<ElectricityConsumptionSupplyMonthly |
        ElectricityMarketPricesMonthly>?culture=pt-PT&year=...&month=...
    verifier:  the DataHub portal's chart CSV EXPORT service, a different endpoint family AND a
        different (CSV table) serialization of the same published data — comparable to the
        accepted BPstat portal-API / INE bddXplorer precedents:
        GET https://datahub.ren.pt/service/exports/csv
            ?startDateString=<YYYY-MM-DD>&endDateString=<YYYY-MM-DD>&culture=pt-PT&country=PT
            &modelId=<1550 for the balance chart | 2649 for the market chart>

Channel mechanics (recorded live 2026-11-11 in tests/ingest/fixtures/ren/verify/):

- Balance (modelId 1550): UTF-8-BOM CSV, CRLF, '.'-decimal; header
  ",Ponta [MW],<mon> <yy> [GWh],Acumulado [GWh],<mon> <yy-1> [GWh],Acumulado [GWh],
   Mês [Variação %],Acumulado [Variação %]" then one row per balance line, monthly value at
  column 2. The requested month is read FROM THE HEADER ('set 26' -> 2026-09) and must equal the
  item's period — never echoed from the request. A single day inside the month pins the month
  (archived requests use start=end=month last day). Unmapped rows duplicate labels (Cogeração
  x3, Outros x2, footnote digits inside labels); every MAPPED label must be unique. observed_unit
  is read from the monthly column's bracket ('GWh' in evidence); the CSV carries no status
  surface -> observed_flag=None honestly.
- Market (modelId 2649): 8-row CSV ",setembro,,2026," / ",PT,ES,PT,ES", then 'Preço Médio'
  (unique), Vazio, Fora Vazio, 'Separação de mercados [%]', Importação, Exportação; columns 1/2
  are the CURRENT period PT/ES, 3/4 the previous year's (by archived shape). The period is read
  from the header (full month name + 4-digit year), geographies from the 'PT,ES,PT,ES' row;
  observed row: current-period PT value (column 1). The market CSV exposes NO unit annotation ->
  observed_unit=None (honest; price unit evidence is the market page narrative, recorded in the
  unit table). No status surface -> observed_flag=None.

EVIDENCE (Ruling R/AC/G7): ONE response decides each item (the CSV export of its chart+month),
so ItemResult.evidence is that response's exact body and evidence_url its final URL — no
envelope needed. Requests are one GET per (endpoint, month), cached inside a single check()
call; the verifier adds no sleeping (the injected Http throttles).

INDEPENDENCE: this module shares NO code with the collector (enforced by register_verifier and
assert_verifier_independent). The TYPE<->CSV-label and selector maps are DUPLICATED ON PURPOSE:
if the two copies ever disagree, verification fails loudly.
"""
import csv
import io
import re
from datetime import date

from ingest.http import Http
from ingest.verifiers import BlindItem, ItemResult

EXPORT_URL = "https://datahub.ren.pt/service/exports/csv"
BALANCE_ENDPOINT = "ElectricityConsumptionSupplyMonthly"
PRICES_ENDPOINT = "ElectricityMarketPricesMonthly"
PRICE_SELECTOR = "PT.Preço Médio"
_BALANCE_MODEL = "1550"
_MARKET_MODEL = "2649"

_PT_MONTHS = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
              "setembro", "outubro", "novembro", "dezembro")
_MONTH_ABBR = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6, "jul": 7, "ago": 8,
               "set": 9, "out": 10, "nov": 11, "dez": 12}
_NUMBER = re.compile(r"-?\d+(\.\d+)?")
_PERIOD = re.compile(r"(\d{4})-(\d{2})")

# DUPLICATE of the collector's reviewed TYPE<->label mapping, ON PURPOSE (module docstring):
# the CSV row labels as published, footnote digits included ('Hídrica 1', 'Biomassa 2').
_BALANCE_LABEL = {
    "CONSUMO": "CONSUMO",
    "PRODUCAO_TOTAL": "PRODUÇÃO TOTAL",
    "PRODUCAO_RENOVAVEL": "Produção Renovável",
    "PRODUCAO_NAO_RENOVAVEL": "Produção não Renovável",
    "HIDRICA": "Hídrica 1",
    "EOLICA": "Eólica",
    "SOLAR": "Solar",
    "BIOMASSA": "Biomassa 2",
    "GAS_NATURAL": "Gás Natural",
    "GAS_NATURAL_CICLO_COMBINADO": "Ciclo Combinado",
    "IMPORTACAO": "Importação (valor comercial)",
    "EXPORTACAO": "Exportação (valor comercial)",
    "SALDO_IMPORTADOR": "SALDO IMPORTADOR",
}
_MARKET_LABEL = "Preço Médio"
_MARKET_KNOWN_LABELS = frozenset(
    {"Preço Médio", "Vazio", "Fora Vazio", "Separação de mercados [%]", "Importação",
     "Exportação"})


def _endpoint_and_selector(code: str | None) -> tuple[str, str]:
    """'<endpoint>:<selector>' -> for the balance the TYPE token, for the market the only
    reviewed selector. DUPLICATE of the collector's parse_native_code, ON PURPOSE."""
    endpoint, sep, selector = (code or "").partition(":")
    if not sep or not selector:
        raise ValueError(f"REN native_code must be '<endpoint>:<selector>', got {code!r}")
    if endpoint == BALANCE_ENDPOINT:
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", selector):
            raise ValueError(f"REN balance TYPE token must be uppercase ASCII, got {selector!r}")
        if selector not in _BALANCE_LABEL:
            raise ValueError(f"REN balance TYPE {selector!r} is not in the reviewed label map")
        return endpoint, selector
    if endpoint == PRICES_ENDPOINT and selector == PRICE_SELECTOR:
        return endpoint, selector
    raise ValueError(f"unknown REN endpoint/selector in native_code {code!r}")


def _year_month(period: str) -> tuple[int, int]:
    m = _PERIOD.fullmatch(period)
    if not m:
        raise ValueError(f"verifier reviewed canonical monthly periods only, got {period!r}")
    y, mm = int(m.group(1)), int(m.group(2))
    if not 1 <= mm <= 12:
        raise ValueError(f"bad month in period {period!r}")
    return y, mm


def _last_day(y: int, m: int) -> date:
    n = date(y + (m == 12), m % 12 + 1, 1)
    return date.fromordinal(n.toordinal() - 1)


def _rows(body: bytes, what: str) -> list[list[str]]:
    head = body[:64].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    if head.startswith(b"<"):
        raise ValueError(f"REN portal CSV export for {what} answered markup: {body[:80]!r}")
    try:
        text = body.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ValueError(f"REN portal CSV export for {what} is not UTF-8: {e}") from e
    rows = [row for row in csv.reader(io.StringIO(text)) if row]
    # blank rows are only tolerated at the very end (archived shape); an interior blank row is
    # an unreviewed table break
    seen = [i for i, row in enumerate(rows) if all(not c.strip() for c in row)]
    if seen and seen != list(range(seen[0], len(rows))):
        raise ValueError(f"REN portal CSV export for {what} has an interior blank row")
    rows = [row for row in rows if any(c.strip() for c in row)]
    if len(rows) < 2:
        raise ValueError(f"REN portal CSV export for {what} has no data rows: {body[:80]!r}")
    return rows


def _parse_balance_csv(body: bytes, label: str, period: str) -> tuple[str, str]:
    """(token, observed_unit) of the mapped row label, with period and unit read from the CSV
    header (never echoed from the request)."""
    rows = _rows(body, f"balance {period}")
    header, data = rows[0], rows[1:]
    if len(header) != 8 or header[0].strip() or header[1] != "Ponta [MW]":
        raise ValueError(f"REN balance export header drifted: {header!r}")
    m = re.fullmatch(r"([a-z]{3}) (\d{2}) \[([^\]]+)\]", header[2])
    if not m:
        raise ValueError(f"REN balance monthly column header not '<mon> <yy> [<unit>]': "
                         f"{header[2]!r}")
    abbr, yy, unit = m.group(1), m.group(2), m.group(3)
    y, mm = _year_month(period)
    if _MONTH_ABBR.get(abbr) != mm or int(yy) != y % 100:
        raise ValueError(f"REN balance export answers '{header[2]}' for the requested month "
                         f"{period}: refusing to trust a response whose header disagrees with "
                         "the request")
    prev = re.fullmatch(r"([a-z]{3}) (\d{2}) \[([^\]]+)\]", header[4])
    if prev is None or _MONTH_ABBR.get(prev.group(1)) != mm or int(prev.group(2)) != (y - 1) % 100:
        raise ValueError(f"REN balance reference column header drifted: {header[4]!r}")
    if header[3] != f"Acumulado [{unit}]" or header[5] != f"Acumulado [{unit}]" or \
            header[6] != "Mês [Variação %]" or header[7] != "Acumulado [Variação %]":
        raise ValueError(f"REN balance export header drifted: {header!r}")
    labels = [row[0] for row in data]
    for mapped in _BALANCE_LABEL.values():
        if labels.count(mapped) > 1:
            raise ValueError(f"REN balance export repeats the mapped label {mapped!r}")
    if labels.count(label) != 1:
        raise ValueError(f"REN balance export holds {labels.count(label)} rows labelled "
                         f"{label!r} for {period}")
    row = data[labels.index(label)]
    if len(row) != 8:
        raise ValueError(f"REN balance export row for {label!r} has {len(row)} cells, "
                         f"expected 8: {row!r}")
    token = row[2].strip()
    if not _NUMBER.fullmatch(token):
        raise ValueError(f"REN balance export value for {label!r} @ {period} is not a number "
                         f"token: {row[2]!r}")
    return token, unit


def _parse_market_csv(body: bytes, period: str) -> str:
    """The current-period PT 'Preço Médio' token; period and geography read from the CSV
    header rows (never echoed from the request)."""
    rows = _rows(body, f"market {period}")
    y, mm = _year_month(period)
    head = rows[0]
    if len(head) != 5 or head[0].strip() or head[2].strip() or head[4].strip() or \
            head[1] != _PT_MONTHS[mm - 1] or head[3] != str(y):
        raise ValueError(f"REN market export header must be ',{_PT_MONTHS[mm - 1]},,{y},' for "
                         f"the requested month {period}, got {head!r}")
    if rows[1] != ["", "PT", "ES", "PT", "ES"]:
        raise ValueError(f"REN market export geography row must be ',PT,ES,PT,ES', got "
                         f"{rows[1]!r}")
    labels = [row[0] for row in rows[2:]]
    unknown = [lab for lab in labels if lab not in _MARKET_KNOWN_LABELS]
    if unknown:
        raise ValueError(f"REN market export carries unreviewed rows {unknown}")
    if labels.count(_MARKET_LABEL) != 1:
        raise ValueError(f"REN market export holds {labels.count(_MARKET_LABEL)} 'Preço Médio' "
                         f"rows for {period}")
    row = rows[2:][labels.index(_MARKET_LABEL)]
    if len(row) != 5:
        raise ValueError(f"REN market export 'Preço Médio' row has {len(row)} cells: {row!r}")
    token = row[1].strip()
    if not _NUMBER.fullmatch(token):
        raise ValueError(f"REN market export PT 'Preço Médio' @ {period} is not a number token: "
                         f"{row[1]!r}")
    return token


class RenVerifier:
    """See the module docstring: one CSV export request per (chart endpoint, month), period/
    unit/geography read from the evidence, observed_flag honestly None (no status surface)."""
    source_name = "ren"

    def check(self, items: list[BlindItem], http: Http) -> list[ItemResult]:
        cache: dict[tuple[str, str], tuple[bytes, str]] = {}  # per (chart model, month)
        results: list[ItemResult] = []
        for item in items:
            endpoint, selector = _endpoint_and_selector(item.spec.native_code)
            y, mm = _year_month(item.period)
            first, last = date(y, mm, 1).isoformat(), _last_day(y, mm).isoformat()
            if endpoint == BALANCE_ENDPOINT:
                # a single point inside the month pins it (archived: start=end=month last day)
                params = {"startDateString": last, "endDateString": last, "culture": "pt-PT",
                          "country": "PT", "modelId": _BALANCE_MODEL}
            else:
                params = {"startDateString": first, "endDateString": last, "culture": "pt-PT",
                          "country": "PT", "modelId": _MARKET_MODEL}
            cache_key = (params["modelId"], item.period)
            if cache_key not in cache:
                r = http.get(EXPORT_URL, params=params)
                if not 200 <= r.status < 300:
                    raise ValueError(f"REN portal CSV export for {item.spec.id} {item.period} "
                                     f"answered HTTP {r.status} (fail closed on every non-2xx)")
                cache[cache_key] = (r.body, r.url)
            body, url = cache[cache_key]
            if endpoint == BALANCE_ENDPOINT:
                token, unit = _parse_balance_csv(body, _BALANCE_LABEL[selector], item.period)
            else:
                token, unit = _parse_market_csv(body, item.period), None
            results.append(ItemResult(
                series_id=item.series_id, period=item.period, observed_text=token,
                evidence_url=url, observed_decimal=".", observed_unit=unit,
                observed_flag=None, evidence=body))
        return results
