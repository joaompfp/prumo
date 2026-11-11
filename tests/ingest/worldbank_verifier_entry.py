"""Entrypoint run by the independence guard (a subprocess with ingest.sources.* blocked):
exercises the real WorldBankVerifier on blinded items over the recorded CSV ZIP fixtures.
Imports nothing from the collector side."""
from ingest.verifiers import BlindItem
from ingest.verifiers.worldbank import WorldBankVerifier
from tests.ingest.worldbank_fixtures import registry_specs
from tests.ingest.worldbank_verifier_fixtures import (
    CSV_URL,
    VerifyFixtureHttp,
    decode_evidence,
    zip_bytes,
)

# (series, period, observed_text) — every token read from the archived full-ZIP bytes at
# recording time (2026-11-11) and cross-checked against the API v2 JSON channel where both
# exist (PT GDP 2021..2025 5/5; DE/ES GDP pins; EU/GR aggregates on the population channel).
CASES = [
    ("worldbank.gdp_usd.PT", "2025", "346639825141.821"),
    ("worldbank.gdp_usd.PT", "2021", "256055879091.139"),
    ("worldbank.gdp_usd.DE", "1961", "96558204043.1028"),
    ("worldbank.gdp_usd.ES", "2020", "1289783836971.21"),
    ("worldbank.population.EU", "2025", "451127411"),
    ("worldbank.population.GR", "1960", "8331725"),
    ("worldbank.unemployment_wb.PT", "2025", "6.164"),
    ("worldbank.unemployment_wb.GR", "2024", "10.02"),
    ("worldbank.unemployment_wb.PT", "1960", None),  # empty CSV cell: honestly "not found"
]


def run():
    reg = registry_specs()
    items = [BlindItem(sid, period, reg[sid]) for sid, period, _ in CASES]
    http = VerifyFixtureHttp()
    results = WorldBankVerifier().check(items, http)
    got = [(r.series_id, r.period, r.observed_text) for r in results]
    assert got == list(CASES), got
    assert all(r.observed_decimal == "." and r.observed_unit is None
               and r.observed_flag is None and r.evidence for r in results)
    for r in results:
        code = reg[r.series_id].native_code.split(":")[0]
        (rec,) = decode_evidence(r.evidence)
        assert rec == {"url": CSV_URL.format(code=code), "status": 200, "body": zip_bytes(code)}
        assert r.evidence_url == CSV_URL.format(code=code)
    # one ZIP fetch per indicator, cached inside check()
    assert sorted(http.calls) == ["NY.GDP.MKTP.CD", "SL.UEM.TOTL.ZS", "SP.POP.TOTL"]
