"""Live end-to-end check against REN DataHub — network. Deselected by default
(pytest.ini adds -m "not live"); run with:

    .venv-ci/bin/python -m pytest tests/ingest/test_live_ren.py -m live -s

Runs the real pipeline end to end over ALL 14 active REN core series and the last 13 COMPLETED
months (the running month is never requested; range printed in the output): the registered
RenVerifier re-reads a fresh random sample through the independent portal CSV export channel.
REN terms are restrictive (registry redistribution_ok=false), so the licence gate (migration
0005) must keep served=0 even though the run verifies technically. RequestsHttp throttles to
<=1 req/s, 50 s timeout, polite UA.
"""
from datetime import date

import pytest

from ingest.db import open_db
from ingest.http import RequestsHttp
from ingest.rawstore import RawStore
from ingest.registry import load_registry, sync_registry
from ingest.sources.ren import RenSource
from ingest.verifiers import register_verifier
from ingest.verifiers.ren import RenVerifier
from ingest.verify import run_with_refetch
from tests.ingest.ren_fixtures import ROOT

LIVE_SERIES = [
    "ren.electricity_biomass.PT",
    "ren.electricity_consumption.PT",
    "ren.electricity_exports.PT",
    "ren.electricity_hydro.PT",
    "ren.electricity_imports.PT",
    "ren.electricity_natural_gas.PT",
    "ren.electricity_natural_gas_ccgt.PT",
    "ren.electricity_net_imports.PT",
    "ren.electricity_price_mibel.PT",
    "ren.electricity_production_non_renewable.PT",
    "ren.electricity_production_renewable.PT",
    "ren.electricity_production_total.PT",
    "ren.electricity_solar.PT",
    "ren.electricity_wind.PT",
]


@pytest.mark.live
def test_live_run_with_refetch_is_verified_but_legally_withheld(tmp_path, monkeypatch):
    from ingest import verifiers
    monkeypatch.setattr(verifiers, "_REGISTRY", {})
    verifier = RenVerifier()
    register_verifier(verifier)

    reg = {s.id: s for s in load_registry(ROOT / "registry" / "core.yaml")}
    specs = [reg[i] for i in LIVE_SERIES]
    source = RenSource()  # default: the last 13 completed months, computed from today
    db = open_db(tmp_path / "live.db")
    try:
        sync_registry(db, specs)
        assert db.conn.execute("SELECT redistribution_ok FROM source WHERE name='ren'") \
            .fetchone()[0] == 0
        http = RequestsHttp(throttle_rps=1.0, timeout=50.0)
        result = run_with_refetch(db, RawStore(tmp_path / "raw"), source, verifier, specs, http,
                                  size=50)
        per_series = db.conn.execute(
            "SELECT series_id, COUNT(*), MIN(period), MAX(period) FROM observation "
            "WHERE dataset_run_id = ? GROUP BY series_id", (result.run_id,)).fetchall()
        served = db.conn.execute("SELECT COUNT(*) FROM served_observation").fetchone()[0]
        verifs = db.conn.execute(
            "SELECT seed, sample_size, passed FROM verification WHERE dataset_run_id=?",
            (result.run_id,)).fetchall()
        quar = db.conn.execute(
            "SELECT series_id, reason, COUNT(*) FROM quarantine WHERE dataset_run_id=? "
            "GROUP BY series_id, reason", (result.run_id,)).fetchall()
        print(f"\nrequested periods: {source.periods[0]}..{source.periods[-1]} "
              f"({len(source.periods)} completed months, today {date.today()})")
        print(f"final state: {result.state}  run_id={result.run_id}  written={result.n_written}"
              f"  quarantined={result.n_quarantined}  served={served}  verifications={verifs}")
        for sid, n, lo, hi in sorted(per_series):
            print(f"  {sid}: {n} observations {lo}..{hi}")
        for sid, reason, n in quar:
            print(f"  quarantine {sid}: {reason} x{n}")
        assert result.state == "verified"
        assert {r[0] for r in per_series} == set(LIVE_SERIES)
        assert all(n == len(source.periods) for _, n, _, _ in per_series)
        assert result.n_written == 14 * len(source.periods)
        assert verifs and all(p == 1 for _, _, p in verifs)
        # technical verification passed AND the licence gate keeps everything withheld
        assert served == 0
        # archived evidence recovers offline (no HTTP): integrity-checked raw payloads
        rows = db.conn.execute("SELECT id, evidence_sha256 FROM verification_item WHERE "
                               "evidence_sha256 IS NOT NULL").fetchall()
        store = RawStore(tmp_path / "raw")
        n_loaded = sum(1 for _, sha in rows
                       if store.load(store.root / "verify-ren" / sha[:2] / sha) is not None)
        assert rows and n_loaded == len(rows)
        n_raw = db.conn.execute("SELECT COUNT(*) FROM raw_fetch WHERE dataset_run_id=? AND ok=1",
                                (result.run_id,)).fetchone()[0]
        assert n_raw == 2 * len(source.periods)  # balance + prices per month
    finally:
        db.close()
