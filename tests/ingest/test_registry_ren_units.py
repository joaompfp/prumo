"""Registry unit label <-> REN publisher unit evidence pairing (same pattern as
test_registry_bportugal_units.py).

The REN servicebus JSON API exposes NO unit field; publisher unit evidence is the independent
portal surface, read live 2026-11-11 and archived in the Task 12 discovery package:
  - balance page https://datahub.ren.pt/pt/eletricidade/balanco-mensal/ narrative "(...) o
    consumo totalizou 4 362 GWh (...)" and the chart CSV export header 'set 26 [GWh]' -> GWh;
  - market page https://datahub.ren.pt/pt/eletricidade/mercado/ narrative "(...) situou-se em
    199.82€/MWh" -> EUR/MWh (the market CSV export carries no unit annotation).
REN_PUBLISHER_UNIT records, per native_code, the unit read from that evidence; it is not echoed
from the registry.
"""
from pathlib import Path

from ingest.registry import load_registry
from ingest.sources.ren import BALANCE_ENDPOINT, PRICES_ENDPOINT, parse_native_code

REGISTRY = Path(__file__).resolve().parents[2] / "registry" / "core.yaml"

# native_code -> unit read from the publisher's own pages/CSV export on 2026-11-11 (fixtures in
# tests/ingest/fixtures/ren/, archive /home/joao/.hermes/cache/scratch/prumo-task12-ren-discovery).
REN_PUBLISHER_UNIT = {
    "ElectricityConsumptionSupplyMonthly:BIOMASSA": "GWh",
    "ElectricityConsumptionSupplyMonthly:CONSUMO": "GWh",
    "ElectricityConsumptionSupplyMonthly:EOLICA": "GWh",
    "ElectricityConsumptionSupplyMonthly:EXPORTACAO": "GWh",
    "ElectricityConsumptionSupplyMonthly:GAS_NATURAL": "GWh",
    "ElectricityConsumptionSupplyMonthly:GAS_NATURAL_CICLO_COMBINADO": "GWh",
    "ElectricityConsumptionSupplyMonthly:HIDRICA": "GWh",
    "ElectricityConsumptionSupplyMonthly:IMPORTACAO": "GWh",
    "ElectricityConsumptionSupplyMonthly:PRODUCAO_NAO_RENOVAVEL": "GWh",
    "ElectricityConsumptionSupplyMonthly:PRODUCAO_RENOVAVEL": "GWh",
    "ElectricityConsumptionSupplyMonthly:PRODUCAO_TOTAL": "GWh",
    "ElectricityConsumptionSupplyMonthly:SALDO_IMPORTADOR": "GWh",
    "ElectricityConsumptionSupplyMonthly:SOLAR": "GWh",
    "ElectricityMarketPricesMonthly:PT.Preço Médio": "EUR/MWh",
}

_BALANCE_LABELS = {  # TYPE token -> the portal CSV export row label (archived 2026-11-11)
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


def _pairs():
    for s in load_registry(REGISTRY):
        if s.source.name == "ren":
            yield s, parse_native_code(s.native_code)


def test_every_active_ren_series_is_in_the_table_with_matching_unit():
    active = [(s, key) for s, key in _pairs() if s.active]
    assert len(active) == 14
    bad = [(s.id, s.unit, REN_PUBLISHER_UNIT.get(s.native_code))
           for s, _ in active if REN_PUBLISHER_UNIT.get(s.native_code) != s.unit]
    assert not bad, bad


def test_table_has_no_stale_entries():
    used = {s.native_code for s, _ in _pairs() if s.active}
    assert used == set(REN_PUBLISHER_UNIT)


def test_endpoints_and_units_consistent():
    for s, (endpoint, _) in _pairs():
        assert REN_PUBLISHER_UNIT[s.native_code] == \
            ("GWh" if endpoint == BALANCE_ENDPOINT else "EUR/MWh")
        assert endpoint in (BALANCE_ENDPOINT, PRICES_ENDPOINT)


def test_mapped_balance_labels_are_present_in_the_archived_csv():
    """Every reviewed TYPE<->label mapping is exercised by the recorded 2026-09 CSV export
    (unique mapped labels; duplicate labels exist only among unmapped rows)."""
    import csv
    import io
    body = (Path(__file__).parent / "fixtures" / "ren" / "verify" /
            "balance_2026-09.csv").read_bytes()
    labels = [row[0] for row in csv.reader(io.StringIO(body.decode("utf-8-sig"))) if row]
    assert set(_BALANCE_LABELS) == {
        parse_native_code(code)[1] for code in REN_PUBLISHER_UNIT
        if code.startswith(BALANCE_ENDPOINT)}
    for label in _BALANCE_LABELS.values():
        assert labels.count(label) == 1
