"""Entrypoint run by the independence guard (a subprocess with ingest.sources.* blocked):
exercises the real INE verifier on blinded items over the recorded bddXplorer fixtures.
Imports nothing from the collector side."""
from ingest.verifiers import BlindItem
from ingest.verifiers.ine import INEVerifier
from tests.ingest.ine_fixtures import registry_specs
from tests.ingest.ine_verifier_fixtures import VerifyFixtureHttp

# (series, period, observed_text, observed_flag) — INE's published rendering (',' decimal);
# every tuple is a recorded fixture cross-checked against the JSON channel or Eurostat.
CASES = [
    ("ine.live_births.PT", "2024", "84 642", "normal"),
    ("ine.unemployment_monthly.PT", "2026-09", "5,6", "provisional"),
    ("ine.exports_monthly.PT", "2018-09", "4 694 752 793", "normal"),
    ("ine.ipi_seasonal_cae_C.PT", "2005-01", "140,30", "normal"),   # trailing zero kept
    ("ine.ipi_seasonal_cae_10.PT", "2026-08", "105,46", "normal"),  # deep CAE division (injected)
    ("ine.deaths.PT", "2024", "118 396", "normal"),
    ("ine.conf_manufacturing.PT", "2020-04", "-31,0", "normal"),    # negative
    ("ine.ipc_yoy.Continente", "2025-10", "2,32", "normal"),        # geo code '1', period column
]


def run():
    reg = registry_specs()
    items = [BlindItem(sid, period, reg[sid]) for sid, period, _, _ in CASES]
    http = VerifyFixtureHttp()
    results = INEVerifier().check(items, http)
    got = [(r.series_id, r.period, r.observed_text, r.observed_flag) for r in results]
    assert got == [(s, p, v, f) for s, p, v, f in CASES], got
    units = {(r.series_id, r.observed_unit) for r in results}
    assert ("ine.exports_monthly.PT", "EUR") in units
    assert ("ine.ipi_seasonal_cae_C.PT", "index_2021=100") in units
    assert all(r.observed_decimal == "," and r.evidence for r in results)
    pages = sum(1 for c in http.calls if c[0] == "page")
    assert pages == 7, pages  # one page fetch per distinct indicator
    assert len(http.calls) == pages + len(CASES)
