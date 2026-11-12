"""Entrypoint run by the independence guard (a subprocess with collectors/, ingest.flags and
ingest.sources blocked by module name AND file origin): exercises the real FredVerifier on
blinded items over the recorded /data/<CODE> table pages. Imports nothing collector-side.
"""
from ingest.verifiers import BlindItem
from ingest.verifiers.fred import FredVerifier
from tests.ingest.fred_fixtures import active_specs, table_values
from tests.ingest.fred_verifier_fixtures import TableFixtureHttp

# (registry id, period) — every run() assertion re-derives the expected token from the
# archived table bytes via the test-only extractor; nothing is hardcoded from the collector.
CASES = [
    ("fred.aluminum.WORLD", "1992-01"),          # first published month
    ("fred.aluminum.WORLD", "2026-09"),          # latest month
    ("fred.brent_oil.WORLD", "1992-01"),
    ("fred.coffee.WORLD", "1992-01"),            # U.S. Cents per Pound unit family
    ("fred.cotton.WORLD", "1992-01"),
    ("fred.commodity_soybean.WORLD", "2026-09"),
    ("fred.commodity_zinc.WORLD", "2026-09"),
]


def run():
    specs = {s.id: s for s in active_specs()}
    items = [BlindItem(sid, period, specs[sid]) for sid, period in CASES]
    http = TableFixtureHttp()
    results = FredVerifier().check(items, http)
    for (sid, period), r in zip(CASES, results):
        code = specs[sid].native_code
        assert (r.series_id, r.period) == (sid, period)
        assert r.observed_text == table_values(code)[f"{period}-01"]  # exact cell token
        assert r.observed_unit == specs[sid].unit and r.observed_decimal == "."
        assert r.observed_flag is None and r.evidence
        assert r.evidence_url == f"https://fred.stlouisfed.org/data/{code}"
    assert len(http.calls) == 6  # one page fetch per distinct series (aluminum twice -> 1)
