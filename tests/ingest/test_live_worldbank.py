"""Live end-to-end check against the World Bank API v2 — network. Deselected by default
(pytest.ini adds -m "not live"); run with:

    .venv-ci/bin/python -m pytest tests/ingest/test_live_worldbank.py -m live -s

Runs the real pipeline end to end over ALL 930 active worldbank core series (the 52
gdp_per_capita_ppp series are registry-inactive over a proven unit-definition conflict, see
registry/unmapped-worldbank.md): one JSON request per indicator with the indicator's full
registry geography set (19 requests, each single-page at per_page=20000), then the registered
WorldBankVerifier re-reads a fresh random sample (latest period per populated series, so the
sample can exceed 50) through the independent bulk CSV ZIP channel. CC BY 4.0 with
redistribution_ok=true, so verified rows are SERVED here. RequestsHttp throttles to
<=1 req/s, 60 s timeout, polite UA.
"""
from collections import Counter

import pytest

from ingest.db import open_db
from ingest.http import RequestsHttp
from ingest.rawstore import RawStore
from ingest.registry import load_registry, sync_registry
from ingest.sources.worldbank import WorldBankSource
from ingest.verifiers import register_verifier
from ingest.verifiers.worldbank import WorldBankVerifier
from ingest.verify import run_with_refetch
from tests.ingest.worldbank_fixtures import ROOT
from tests.ingest.worldbank_verifier_fixtures import decode_evidence


@pytest.mark.live
def test_live_run_with_refetch_verifies_and_serves_cc_by(tmp_path, monkeypatch, capsys):
    from ingest import verifiers
    monkeypatch.setattr(verifiers, "_REGISTRY", {})
    verifier = WorldBankVerifier()
    register_verifier(verifier)

    specs = [s for s in load_registry(ROOT / "registry" / "core.yaml")
             if s.source.name == "worldbank" and s.active]
    assert len(specs) == 930
    concepts = Counter(s.id.split(".")[1] for s in specs)
    print(f"\nactive worldbank series: {len(specs)} over {len(concepts)} indicators")
    db = open_db(tmp_path / "live-wb.db")
    try:
        sync_registry(db, specs)
        assert db.conn.execute(
            "SELECT redistribution_ok FROM source WHERE name='worldbank'").fetchone()[0] == 1
        http = RequestsHttp(throttle_rps=1.0, timeout=60.0)
        result = run_with_refetch(db, RawStore(tmp_path / "raw"), WorldBankSource(), verifier,
                                  specs, http)
        per_series = db.conn.execute(
            "SELECT series_id, COUNT(*), MAX(period) FROM observation WHERE dataset_run_id=? "
            "GROUP BY series_id", (result.run_id,)).fetchall()
        latest = Counter(hi for _, _, hi in per_series)
        empty = [s.id for s in specs if s.id not in {r[0] for r in per_series}]
        quar = db.conn.execute(
            "SELECT reason, COUNT(*) FROM quarantine WHERE dataset_run_id=? GROUP BY reason",
            (result.run_id,)).fetchall()
        events = db.conn.execute(
            "SELECT kind, json_extract(detail_json,'$.series_id') FROM event "
            "WHERE dataset_run_id=? ORDER BY id", (result.run_id,)).fetchall()
        verifs = db.conn.execute(
            "SELECT seed, sample_size, passed FROM verification WHERE dataset_run_id=?",
            (result.run_id,)).fetchall()
        flags = db.conn.execute(
            "SELECT status_flag, COUNT(*) FROM observation WHERE dataset_run_id=? "
            "GROUP BY status_flag", (result.run_id,)).fetchall()
        served = db.conn.execute("SELECT COUNT(*) FROM served_observation").fetchone()[0]
        n_raw = db.conn.execute(
            "SELECT COUNT(*) FROM raw_fetch WHERE dataset_run_id=? AND ok=1",
            (result.run_id,)).fetchone()[0]
        print(f"final state: {result.state}  run_id={result.run_id}  written={result.n_written}"
              f"  quarantined={result.n_quarantined}  served={served}  raw_responses={n_raw}")
        print(f"populated series: {len(per_series)}; empty series ({len(empty)}): "
              f"{sorted(empty)[:20]}")
        print(f"latest-period distribution (top): {latest.most_common(8)}")
        print(f"quarantine by reason: {sorted(quar)}  flags: {sorted(flags)}")
        print(f"verification rows (seed, sample_size, passed): {verifs}")
        for t, sid in events[:30]:
            print(f"  event {t}: {sid}")
        bad = db.conn.execute(
            "SELECT series_id, period, note FROM verification_item WHERE match=0 LIMIT 10"
        ).fetchall()
        if bad:
            print("first failing verification items:", *["  " + str(b) for b in bad], sep="\n")
        assert result.state == "verified"
        assert verifs and all(p == 1 for _, _, p in verifs)
        assert n_raw == 18  # one JSON page per active indicator (PPP indicator is inactive)
        # served: CC BY 4.0 redistribution_ok=1 gates nothing
        assert served == result.n_written > 0
        # archived verifier evidence recovers offline (no HTTP), exact deciding-ZIP bytes
        rows = db.conn.execute(
            "SELECT id, evidence_url, evidence_sha256 FROM verification_item "
            "WHERE evidence_sha256 IS NOT NULL").fetchall()
        store = RawStore(tmp_path / "raw")
        for _, url, sha in rows:
            blob = store.load(store.root / "verify-worldbank" / sha[:2] / sha)
            (rec,) = decode_evidence(blob)
            assert rec["url"] == url and 200 <= rec["status"] < 300 and rec["body"]
        print(f"all {len(rows)} verification items' evidence recovered offline + integrity OK")
    finally:
        db.close()
