"""Entrypoint run by the independence guard (a subprocess with ingest.sources.* and
ingest.flags blocked): exercises the real BPstat verifier on blinded items over the recorded
portal-API fixtures. Imports nothing from the collector side."""
from ingest.verifiers import BlindItem
from ingest.verifiers.bportugal import BPortugalVerifier
from tests.ingest.bportugal_fixtures import registry_specs
from tests.ingest.bportugal_verifier_fixtures import VerifyFixtureHttp

# (series, period, observed_text, observed_unit) — the portal's own published rendering,
# every case recorded live 2026-11-11 and cross-checked against the collector's JSON-stat token
# (fixtures/bportugal/verify/MANIFEST.json).
CASES = [
    ("bportugal.euribor_1m.EA", "1994-01", "7.1200", "%"),
    ("bportugal.euribor_3m.EA", "1994-01", "6.9100", "%"),
    ("bportugal.euribor_12m.EA", "2020-04", "-0.1082", "%"),   # negative value
    ("bportugal.pt_10y.PT", "2023-08", "3.31", "%"),           # revision vintage (was 3.30)
    ("bportugal.pt_10y.PT", "1993-07", "10.67", "%"),
    ("bportugal.de_10y.DE", "2000-01", "5.52", "%"),           # first valued DE month
    ("bportugal.credit_housing.PT", "1982-08", "908.1", "MEUR"),
    ("bportugal.credit_consumer.PT", "2012-11", "13411.7", "MEUR"),
    ("bportugal.deposits_households.PT", "1999-12", "77865.3", "MEUR"),
    ("bportugal.eur_usd.EA", "2000-10", "0.8552", "USD/EUR"),
    ("bportugal.eur_usd.EA", "2026-10", "1.1202", "USD/EUR"),
]


def run():
    reg = registry_specs()
    items = [BlindItem(sid, period, reg[sid]) for sid, period, _, _ in CASES]
    http = VerifyFixtureHttp()
    results = BPortugalVerifier().check(items, http)
    got = [(r.series_id, r.period, r.observed_text, r.observed_unit) for r in results]
    assert got == [(s, p, v, u) for s, p, v, u in CASES], got
    assert all(r.observed_decimal == "." and r.evidence and r.observed_flag is None
               for r in results)
    n_meta = sum(1 for kind, _ in http.calls if kind == "meta")
    assert n_meta == 9, http.calls  # one series-metadata fetch per distinct series (eur_usd x2)
    assert len(http.calls) == n_meta + len(CASES)
