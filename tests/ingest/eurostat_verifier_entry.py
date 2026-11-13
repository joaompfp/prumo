"""Entrypoint run by the independence guard (a subprocess with ingest.sources.* blocked):
exercises the real Eurostat verifier on blinded items over the recorded SDMX TSV fixtures.
Imports nothing from the collector side."""
from ingest.verifiers import BlindItem
from ingest.verifiers.eurostat import EurostatVerifier
from tests.ingest.eurostat_fixtures import FixtureHttp, registry_specs

# Same observations as the adapter test, read here from the TSV channel.
CASES = [
    ("eurostat.STS_INPR_M_BD.PT", "2026-09", "97.1", "normal"),
    ("eurostat.ipi_total.EU27", "1991-01", "74.8", "estimated"),
    ("eurostat.gdp_per_capita_eur.PT", "2025", "28560", "provisional"),
    ("eurostat.gdp_per_capita_eur.EU27_2020", "2020", "30560", "break"),
    ("eurostat.gdp_quarterly.EU27", "2026-Q3", "3471512.8", "normal"),
    ("eurostat.electricity_price_household.PT", "2019-S1", "0.2150", "normal"),
    ("eurostat.electricity_price_household.GR", "2021-S1", "0.1680", "normal"),
]


def run():
    reg = registry_specs()
    items = [BlindItem(sid, period, reg[sid]) for sid, period, _, _ in CASES]
    http = FixtureHttp()
    results = EurostatVerifier().check(items, http)
    got = [(r.series_id, r.period, r.observed_text, r.observed_flag) for r in results]
    assert got == [(s, p, v, f) for s, p, v, f in CASES], got
    assert len(http.calls) == 4  # one request per dataset key group
