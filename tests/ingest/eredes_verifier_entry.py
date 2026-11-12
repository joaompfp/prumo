"""Entrypoint run by the independence guard (a subprocess with ingest.sources.* blocked):
exercises the real E-REDES verifier on blinded items over the recorded CSV/metadata fixtures.
Imports nothing from the collector side."""
from ingest.verifiers import BlindItem
from ingest.verifiers.eredes import EredesVerifier
from tests.ingest.eredes_fixtures import registry_specs
from tests.ingest.eredes_verifier_fixtures import (
    VMANIFEST,
    VerifyFixtureHttp,
    decode_evidence,
    vbody,
)

# (series, period, observed_text) - every token read from the genuine archived CSV bytes
# (fixtures/eredes/window_csv.body) and byte-checked against the JSON records channel of the
# same window at recording time (2026-11-12, MANIFEST.json).
CASES = [
    ("eredes.production_market.PT", "2026-11-10T00:00:00+00:00", "925741.0"),
    ("eredes.production_special.PT", "2026-11-10T00:15:00+00:00", "523992.0"),
    ("eredes.production_total.PT", "2026-11-10T06:30:00+00:00", "1340285.0"),
    ("eredes.production_market.PT", "2026-11-10T12:00:00+00:00", "1393848.0"),
    ("eredes.production_total.PT", "2026-11-10T18:45:00+00:00", "1971562.0"),
    ("eredes.production_total.PT", "2026-11-10T23:30:00+00:00", "1551219.0"),
    ("eredes.production_market.PT", "2026-11-10T23:45:00+00:00", "1097652.0"),
]


def run():
    reg = registry_specs()
    items = [BlindItem(sid, period, reg[sid]) for sid, period, _ in CASES]
    http = VerifyFixtureHttp()
    results = EredesVerifier().check(items, http)
    got = [(r.series_id, r.period, r.observed_text, r.observed_unit) for r in results]
    assert got == [(s, p, v, "kWh") for s, p, v in CASES], got
    assert all(r.observed_decimal == "." and r.observed_flag is None and r.evidence
               for r in results)
    for r in results:
        rec_csv, rec_meta = decode_evidence(r.evidence)  # exactly the 2 deciding responses
        assert rec_csv == {"url": VMANIFEST["window_csv"]["url"],
                           "status": VMANIFEST["window_csv"]["status"],
                           "body": vbody("window_csv")}
        assert rec_meta == {"url": VMANIFEST["metadata"]["url"],
                            "status": VMANIFEST["metadata"]["status"],
                            "body": vbody("metadata")}
        assert r.evidence_url == VMANIFEST["window_csv"]["url"]
    # cache: one CSV export + one metadata response for the whole 7-item batch
    assert http.calls == ["window_csv", "metadata"]
