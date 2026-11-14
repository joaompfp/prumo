"""CLI tests (Task 17A): `python -m ingest` argument handling, dry-run isolation, run-all
failure isolation, replay/verify/import-legacy correctness. Two flavours: offline end-to-end
over the RECORDED genuine World Bank publisher fixtures (JSON data + CSV ZIP export bytes),
and labelled seam injections (mini registries/failing statuses; not publisher results)."""
import json
from pathlib import Path

import pytest
import yaml

import ingest.verifiers as verifiers
from ingest.cli import main
from ingest.db import open_db
from ingest.models import SeriesSpec, SourceSpec
from ingest.operations import VERIFIER_OPS, ensure_verifier
from ingest.pipeline import run_dataset
from ingest.rawstore import RawStore
from ingest.registry import sync_registry
from ingest.sources.worldbank import WorldBankSource
from ingest.verifiers.worldbank import WorldBankVerifier
from tests.ingest.legacy_csv import write_csv
from tests.ingest.worldbank_fixtures import (
    GDP_PTDES,
    POP_EUGRAT,
    FixtureHttp,
    specs_of,
)
from tests.ingest.worldbank_verifier_fixtures import VerifyFixtureHttp

T0 = "2026-03-01T10:00:00+00:00"


@pytest.fixture(autouse=True)
def _clean_registry(monkeypatch):
    monkeypatch.setattr(verifiers, "_REGISTRY", {})


def _write_registry(path: Path, specs: list[SeriesSpec]) -> Path:
    sources, series = {}, []
    for s in specs:
        sources[s.source.name] = s.source.model_dump(exclude={"name"})
        series.append({**s.model_dump(exclude={"source"}), "source": s.source.name})
    path.write_text(yaml.safe_dump({"sources": sources, "series": series},
                                   sort_keys=False, allow_unicode=True))
    return path


class _E2EHttp:
    """Routes the collector's /v2/country/... JSON requests to the recorded FixtureHttp and
    the verifier's /v2/<lang>/indicator/...?downloadformat=csv requests to the recorded
    VerifyFixtureHttp. Genuine recorded bytes, no network."""

    def __init__(self, source_status=None):
        self.source = FixtureHttp(status=source_status)
        self.verifier = VerifyFixtureHttp()

    def get(self, url, params=None, headers=None, timeout=None):
        if "/v2/country/" in url:
            return self.source.get(url, params=params, headers=headers, timeout=timeout)
        return self.verifier.get(url, params=params, headers=headers, timeout=timeout)


def _paths(tmp_path):
    return tmp_path / "prumo.sqlite3", tmp_path / "raw", tmp_path / "registry.yaml"


def _wb_specs():
    return specs_of(GDP_PTDES + POP_EUGRAT)


def test_cli_run_worldbank_offline_end_to_end_then_status(tmp_path, capsys):
    db_path, raw, reg = _paths(tmp_path)
    _write_registry(reg, _wb_specs())
    rc = main(["--db", str(db_path), "--raw-dir", str(raw), "--registry", str(reg),
               "run", "worldbank"],
              http_for=lambda name: _E2EHttp())
    assert rc == 0
    out = capsys.readouterr().out
    assert "worldbank: verified" in out
    assert "NY.GDP.MKTP.CD: verified" in out and "SP.POP.TOTL: verified" in out
    db = open_db(db_path)
    try:  # six series x two indicators verified through the real verifier + recorded CSV ZIPs
        assert db.conn.execute("SELECT COUNT(*) FROM dataset_run WHERE state='verified'"
                               ).fetchone()[0] == 2
        assert db.conn.execute("SELECT COUNT(*) FROM served_observation").fetchone()[0] > 0
    finally:
        db.close()
    rc = main(["--db", str(db_path), "--registry", str(reg), "status", "--json"])
    assert rc == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["schema"] == "prumo-status" and doc["version"] == 2
    wb = next(s for s in doc["sources"] if s["name"] == "worldbank")
    assert wb["latest_attempt_state"] == "verified"
    assert all(s["availability"] == "verified" for s in wb["series"])
    assert wb["last_verified"] and wb["real_data_fetched_at"] < wb["last_verified"]


def test_cli_run_worldbank_one_failed_group_does_not_block_the_healthy_one(tmp_path, capsys):
    db_path, raw, reg = _paths(tmp_path)
    _write_registry(reg, _wb_specs())
    pop_key = ("SP.POP.TOTL", frozenset({"EU", "GR", "AT"}), 1)
    rc = main(["--db", str(db_path), "--raw-dir", str(raw), "--registry", str(reg),
               "run", "worldbank"], http_for=lambda name: _E2EHttp({pop_key: 500}))
    out = capsys.readouterr().out
    assert rc == 1  # an ACTIVE source did not fully verify
    assert "SP.POP.TOTL: failed-fetch" in out
    assert "NY.GDP.MKTP.CD: verified" in out


DGEG = SourceSpec(name="dgeg", licence="UNVERIFIED", licence_url="http://l",
                  attribution="DGEG", redistribution_ok=False, verifiable=False)
FRED = SourceSpec(name="fred", licence="UNVERIFIED", licence_url="http://l",
                  attribution="FRED", redistribution_ok=False, verifiable=True)


def _fred_spec() -> SeriesSpec:
    return SeriesSpec(id="fred.zinc.WORLD", source=FRED, indicator_key="zinc.WORLD.M",
                      role="primary", theme="economy", geography="WORLD", frequency="M",
                      unit="USD", native_code="PZINCUSDM", active=True)


def _dgeg_spec() -> SeriesSpec:
    return SeriesSpec(id="dgeg.diesel.PT", source=DGEG, indicator_key="diesel.PT.W",
                      role="primary", theme="energy", geography="PT", frequency="M",
                      unit="EUR/l", active=False)


def test_cli_run_all_reports_dgeg_blocked_with_no_http_and_a_missing_fred_key_blocks_only_fred(
        tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    db_path, raw, reg = _paths(tmp_path)
    _write_registry(reg, [*_wb_specs(), _fred_spec(), _dgeg_spec()])
    probes = []

    def counting_http(name):
        probes.append(name)
        return _E2EHttp()
    rc = main(["--db", str(db_path), "--raw-dir", str(raw), "--registry", str(reg),
               "run", "all"], http_for=counting_http)
    out = capsys.readouterr().out
    assert rc == 1  # fred is active but its credential is missing
    assert "dgeg: blocked" in out and "verifiable: false" in out
    assert "fred: blocked" in out and "FRED needs an API key" in out
    assert "worldbank: verified" in out  # a missing FRED key never blocks the healthy sources
    assert probes == ["worldbank"]  # blocked sources (dgeg/fred) never even build a client


def test_cli_dry_run_never_touches_the_real_paths(tmp_path, capsys):
    db_path, raw, reg = _paths(tmp_path)
    _write_registry(reg, _wb_specs())
    rc = main(["--db", str(db_path), "--raw-dir", str(raw), "--registry", str(reg),
               "run", "worldbank", "--dry-run"], http_for=lambda name: _E2EHttp())
    assert rc == 0 and "verified" in capsys.readouterr().out
    assert not db_path.exists() and not raw.exists()  # the real targets were never opened


def test_cli_import_legacy_then_replay_keeps_dated_legacy_and_never_verifies_it(
        tmp_path, capsys):
    db_path, raw, reg = _paths(tmp_path)
    specs = _wb_specs()
    _write_registry(reg, specs)
    csv_path = tmp_path / "indicators.csv"
    # 1959 is outside the recorded fetch window (1960+), so the dated legacy row stays the
    # served value for its period after replay (fetched verified always wins when both exist)
    write_csv(csv_path, [("WORLDBANK", "gdp_usd", "PT", "1959", "1.25", "USD", T0)])
    assert main(["--db", str(db_path), "--registry", str(reg),
                 "import-legacy", str(csv_path)]) == 0
    before = open_db(db_path)
    legacy_before = before.conn.execute(
        "SELECT series_id, period, value_text, kind, fetched_at FROM observation "
        "WHERE kind='legacy-unverified'").fetchall()
    legacy_run = before.conn.execute("SELECT id, state FROM dataset_run WHERE dataset_key="
                                     "'legacy:worldbank'").fetchone()
    verifications_before = before.conn.execute("SELECT COUNT(*) FROM verification").fetchone()[0]
    before.close()
    assert legacy_before and legacy_run[1] == "verified"

    rc = main(["--db", str(db_path), "--raw-dir", str(raw), "--registry", str(reg),
               "replay", "--from", "2026-04"], http_for=lambda name: _E2EHttp())
    capsys.readouterr()
    assert rc == 0
    db = open_db(db_path)
    try:
        # legacy rows and the synthetic run are byte-identical; legacy runs got NO verification
        assert db.conn.execute("SELECT series_id, period, value_text, kind, fetched_at FROM "
                               "observation WHERE kind='legacy-unverified'").fetchall() == \
            legacy_before
        assert db.conn.execute("SELECT state FROM dataset_run WHERE id=?",
                               (legacy_run[0],)).fetchone()[0] == "verified"
        assert db.conn.execute("SELECT COUNT(*) FROM verification").fetchone()[0] > \
            verifications_before
        assert db.conn.execute("SELECT COUNT(*) FROM verification WHERE dataset_run_id=?",
                               (legacy_run[0],)).fetchone()[0] == 0
        # scoped eligibility (migration 0007): the dated 1959 legacy row is served honestly
        assert db.conn.execute("SELECT value_text, fetched_at FROM served_observation WHERE "
                               "series_id='worldbank.gdp_usd.PT' AND period='1959'"
                               ).fetchall() == [("1.25", T0.replace("+00:00", "Z"))]
    finally:
        db.close()


def test_cli_verify_resolves_the_registered_verifier_of_an_existing_pending_run(
        tmp_path, capsys):
    db_path, raw, reg = _paths(tmp_path)
    specs = _wb_specs()
    _write_registry(reg, specs)
    db = open_db(db_path)
    sync_registry(db, specs)
    result = run_dataset(db, RawStore(raw), WorldBankSource(), specs, FixtureHttp())
    db.close()
    assert result.state == "pending-verification"
    rc = main(["--db", str(db_path), "--raw-dir", str(raw), "--registry", str(reg),
               "verify", str(result.run_id)],
              http_for=lambda name: VerifyFixtureHttp())
    out = capsys.readouterr().out
    assert rc == 0 and f"run {result.run_id}: verified" in out

    # the now-verified run and unknown ids are refused instead of verifying unrelated data
    assert main(["--db", str(db_path), "--registry", str(reg), "verify",
                 str(result.run_id)]) == 2
    assert "pending-verification" in capsys.readouterr().err
    assert main(["--db", str(db_path), "--registry", str(reg), "verify", "999"]) == 2
    assert "no such run" in capsys.readouterr().err
    assert main(["--db", str(db_path), "--registry", str(reg), "verify", "0"]) == 2


def test_cli_verify_refuses_legacy_runs(tmp_path, capsys):
    db_path, raw, reg = _paths(tmp_path)
    _write_registry(reg, _wb_specs())
    csv_path = tmp_path / "indicators.csv"
    write_csv(csv_path, [("WORLDBANK", "gdp_usd", "PT", "1970", "1.25", "USD")])
    assert main(["--db", str(db_path), "--registry", str(reg),
                 "import-legacy", str(csv_path)]) == 0
    db = open_db(db_path)
    legacy_run_id = db.conn.execute("SELECT id FROM dataset_run WHERE dataset_key="
                                    "'legacy:worldbank'").fetchone()[0]
    db.close()
    assert main(["--db", str(db_path), "--registry", str(reg), "verify",
                 str(legacy_run_id)]) == 2
    assert "legacy" in capsys.readouterr().err


def test_ensure_verifier_registers_once_and_reuses_only_a_compatible_instance():
    """The supported reuse contract: one registration per source per process; a pre-registered
    instance with a DIFFERENT configuration is a clear mismatch error, never a silent reuse or
    a private-registry replacement."""
    ops = VERIFIER_OPS["worldbank"]
    v = ensure_verifier(ops)
    assert v.indicator_locales == {"NY.GDP.MKTP.KD.ZG": "es", "SL.UEM.TOTL.ZS": "es"}
    assert ensure_verifier(ops) is v  # compatible pre-registered instance is reused
    verifiers._REGISTRY["worldbank"] = WorldBankVerifier()  # foreign default-en instance
    with pytest.raises(ValueError, match="incompatible"):
        ensure_verifier(ops)


def test_cli_argument_errors(tmp_path, capsys):
    db_path, raw, reg = _paths(tmp_path)
    _write_registry(reg, _wb_specs())
    assert main(["--db", str(db_path), "--registry", str(reg), "run", "nonsense"],
                http_for=lambda name: None) == 2
    assert "unknown source" in capsys.readouterr().err
    for bad in ("2026-4", "2026-13", "２０２６-０４", "2099-01"):
        assert main(["--db", str(db_path), "--registry", str(reg), "replay",
                     "--from", bad]) == 2
        capsys.readouterr()
    duckdb = tmp_path / "old.duckdb"
    duckdb.write_bytes(b"not a csv")
    assert main(["--db", str(db_path), "--registry", str(reg),
                 "import-legacy", str(duckdb)]) == 2
    err = capsys.readouterr().err
    assert "CSV" in err and "DuckDB" in err
    # status takes no time-travel knobs: timestamps come from the DB and the clock only
    with pytest.raises(SystemExit):
        main(["--db", str(db_path), "--registry", str(reg), "status", "--as-of", "2026-01-01"])
