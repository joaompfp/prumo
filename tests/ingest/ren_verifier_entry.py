"""Entrypoint run by the independence guard (a subprocess with ingest.sources.* blocked):
exercises the real REN verifier on blinded items over the recorded CSV-export fixtures.
Imports nothing from the collector side."""
from ingest.verifiers import BlindItem
from ingest.verifiers.ren import RenVerifier
from tests.ingest.ren_fixtures import registry_specs
from tests.ingest.ren_verifier_fixtures import VMANIFEST, VerifyFixtureHttp, decode_evidence, vbody

# (series, period, observed_text, observed_unit) — every token read from the archived CSV bytes
# fixtures/ren/verify/ and cross-checked against the servicebus JSON payload at recording time
# (2026-11-11): CONSUMO 4442 == API 4442; PT Preço Médio 143.9 == API 143.9.
CASES = [
    ("ren.electricity_consumption.PT", "2026-09", "4442", "GWh"),
    ("ren.electricity_production_total.PT", "2026-09", "3360", "GWh"),
    ("ren.electricity_production_renewable.PT", "2026-09", "2327", "GWh"),
    ("ren.electricity_production_non_renewable.PT", "2026-09", "599", "GWh"),
    ("ren.electricity_hydro.PT", "2026-09", "645", "GWh"),  # footnote label 'Hídrica 1'
    ("ren.electricity_wind.PT", "2026-09", "727", "GWh"),
    ("ren.electricity_solar.PT", "2026-09", "725", "GWh"),
    ("ren.electricity_biomass.PT", "2026-09", "230", "GWh"),  # footnote label 'Biomassa 2'
    ("ren.electricity_natural_gas.PT", "2026-09", "579", "GWh"),
    ("ren.electricity_natural_gas_ccgt.PT", "2026-09", "510", "GWh"),
    ("ren.electricity_imports.PT", "2026-09", "1697", "GWh"),
    ("ren.electricity_exports.PT", "2026-09", "87", "GWh"),
    ("ren.electricity_net_imports.PT", "2026-09", "1616", "GWh"),
    ("ren.electricity_consumption.PT", "2020-06", "3604", "GWh"),  # 'jun 20' header, other year
    ("ren.electricity_price_mibel.PT", "2026-09", "143.9", None),  # market CSV: no unit surface
]


def run():
    reg = registry_specs()
    items = [BlindItem(sid, period, reg[sid]) for sid, period, _, _ in CASES]
    http = VerifyFixtureHttp()
    results = RenVerifier().check(items, http)
    got = [(r.series_id, r.period, r.observed_text, r.observed_unit) for r in results]
    assert got == [(s, p, v, u) for s, p, v, u in CASES], got
    assert all(r.observed_decimal == "." and r.evidence and r.observed_flag is None
               for r in results)
    # every evidence envelope decodes offline: exact deciding-response bytes, final URL and
    # the ACTUAL archived HTTP status
    for r in results:
        key = ("market_2026-09" if "price" in r.series_id else
               "balance_2020-06" if r.period == "2020-06" else "balance_2026-09")
        assert r.evidence is not None
        (rec,) = decode_evidence(r.evidence)
        assert rec == {"url": VMANIFEST[key]["url"], "status": VMANIFEST[key]["status"],
                       "body": vbody(VMANIFEST[key]["file"])}
        assert r.evidence_url == VMANIFEST[key]["url"]
    # cache: one fetch per (chart, month) — 13 2026-09 balance items share one response
    assert http.calls == ["balance_2026-09", "balance_2020-06", "market_2026-09"]
