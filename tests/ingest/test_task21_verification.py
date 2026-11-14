"""Task 21: final-review part B fixes (B-I1..B-I4, B-M1, B-M3) through the real DB."""
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from fractions import Fraction

import pytest
import requests

import ingest.db as dbmod
from ingest import verifiers
from ingest.cli import main
from ingest.db import MIGRATIONS_DIR, open_db
from ingest.pipeline import run_dataset
from ingest.rawstore import RawIntegrityError, RawStore
from ingest.registry import sync_registry
from ingest.sampling import SamplingPolicy
from ingest.verifiers import VerifierUnavailable, register_verifier
from ingest.verify import replay_check, replay_item, run_with_refetch, verify_run
from tests.ingest.fake_verifier import FakeVerifier
from tests.ingest.fakes import FakeHttp, FakeSource, ok, payload, spec, truth_of


class Clock:
    def __init__(self):
        self.t = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        self.t += timedelta(seconds=1)
        return self.t


@pytest.fixture(autouse=True)
def empty_registry(monkeypatch):
    monkeypatch.setattr(verifiers, "_REGISTRY", {})


def q(db, sql, *args):
    return db.conn.execute(sql, args).fetchall()


SERIES = {"s1": [[str(y), f"{y}.1"] for y in range(2000, 2025)],
          "s2": [[str(y), f"{y}.2"] for y in range(2000, 2025)]}


@pytest.fixture
def env(db, tmp_path):
    specs = [spec("s1"), spec("s2")]
    sync_registry(db, specs)
    store = RawStore(tmp_path / "raw")
    clock = Clock()

    def run(series=SERIES):
        return run_dataset(db, store, FakeSource(), specs, FakeHttp(ok(payload(series))), clock)
    return db, specs, store, clock, run


def items(db, run_id):
    return q(db, "SELECT i.id, i.series_id, i.period, i.match, i.note, i.reason, i.compared, "
                 "i.unit_not_compared, i.flag_not_compared FROM verification_item i "
                 "JOIN verification v ON v.id = i.verification_id WHERE v.dataset_run_id = ? "
                 "ORDER BY i.id", run_id)


def events(db, kind):
    return [(r, json.loads(d)) for r, d in
            q(db, "SELECT dataset_run_id, detail_json FROM event WHERE kind = ? ORDER BY id",
              kind)]


# --- B-I2: the run's changed set is must-check, with the reason recorded -----------------------

def test_revised_and_new_cells_are_forced_into_the_sample(env):
    db, specs, store, clock, run = env
    r1 = run()
    assert verify_run(db, r1.run_id, FakeVerifier(truth_of(SERIES)), None, specs=specs,
                      store=store, now=clock)
    assert events(db, "new_periods") == []  # a first ingestion has nothing to be new against
    revised = {"s1": [*[[p, v] for p, v in SERIES["s1"] if p != "2003"], ["2003", "9.9"],
                      ["2025", "2025.1"]],
               "s2": SERIES["s2"]}
    r2 = run(revised)
    assert [d for _, d in events(db, "revision")] == [
        {"series_id": "s1", "period": "2003", "old": "2003.1", "new": "9.9"}]
    assert [d for _, d in events(db, "new_periods")] == [{"series_id": "s1",
                                                          "periods": ["2025"]}]
    v = FakeVerifier(truth_of(revised))
    # a policy with no history fill: only must-check rows (+ nothing else) are drawn
    assert verify_run(db, r2.run_id, v, None, specs=specs, store=store, now=clock,
                      policy=SamplingPolicy(confidence=Fraction(0), history_per_series=0))
    got = {(sid, period): why for _, sid, period, _, _, why, *_ in items(db, r2.run_id)}
    assert got == {("s1", "2003"): "changed", ("s1", "2025"): "latest",
                   ("s2", "2024"): "latest"}
    (design,), = q(db, "SELECT sample_design FROM verification WHERE dataset_run_id = ?",
                   r2.run_id)
    d = json.loads(design)
    assert (d["n_changed_total"], d["n_changed_checked"], d["policy"]["changed_cap"]) == (
        1, 1, 500)


def test_changed_cells_above_the_cap_are_capped_and_the_cap_recorded(env):
    db, specs, store, clock, run = env
    r1 = run()
    assert verify_run(db, r1.run_id, FakeVerifier(truth_of(SERIES)), None, specs=specs,
                      store=store, now=clock)
    revised = {sid: [[p, v + "0"] for p, v in rows] for sid, rows in SERIES.items()}
    r2 = run(revised)
    pol = SamplingPolicy(confidence=Fraction(0), history_per_series=0, changed_cap=5)
    assert verify_run(db, r2.run_id, FakeVerifier(truth_of(revised)), None, specs=specs,
                      store=store, now=clock, policy=pol)
    reasons = [row[5] for row in items(db, r2.run_id)]
    assert reasons.count("changed") == 5 and reasons.count("latest") == 2
    d = json.loads(q(db, "SELECT sample_design FROM verification WHERE dataset_run_id = ?",
                     r2.run_id)[0][0])
    assert (d["n_changed_total"], d["n_changed_checked"], d["policy"]["changed_cap"]) == (
        48, 5, 5)


# --- verification record: procedure, design, origin, channel, specs ------------------------------

def test_verification_row_records_procedure_design_origin_channel_and_specs(env):
    db, specs, store, clock, run = env
    r = run()
    assert verify_run(db, r.run_id, FakeVerifier(truth_of(SERIES)), None, seed=11,
                      specs=specs, store=store, now=clock)
    (proc, design, origin, channel, size), = q(
        db, "SELECT sample_procedure, sample_design, input_origin, verifier_channel, "
            "sample_size FROM verification")
    d = json.loads(design)
    assert (proc, origin, channel) == ("prumo-sample-v2", "live", "live")
    assert d["n_observations"] == 50 and d["n_items"] == size == len(items(db, r.run_id))
    assert sum(d["counts"].values()) == size
    stored = dict(q(db, "SELECT series_id, spec_json FROM verification_spec"))
    assert set(stored) == {"s1", "s2"}
    assert json.loads(stored["s1"]) == json.loads(specs[0].model_dump_json())


# --- B-M1: compared fields and recorded reasons -------------------------------------------------

def test_each_item_records_compared_fields_and_why_unit_or_flag_was_not(env):
    db, specs, store, clock, run = env
    r = run()
    assert verify_run(db, r.run_id, FakeVerifier(truth_of(SERIES), unit="EUR"), None,
                      specs=specs, store=store, now=clock)
    for *_, compared, unit_reason, flag_reason in items(db, r.run_id):
        assert compared == "series_id,period,value,unit"
        assert unit_reason is None
        assert flag_reason == FakeVerifier.not_compared["flag"]


def test_unexposed_field_without_a_declared_reason_fails(env):
    db, specs, store, clock, run = env

    class Mute(FakeVerifier):
        not_compared = {"flag": "no status surface"}  # declares nothing for unit

    r = run()
    assert not verify_run(db, r.run_id, Mute(truth_of(SERIES)), None, specs=specs,
                          store=store, now=clock)
    notes = {row[4] for row in items(db, r.run_id)}
    assert notes == {"unit not exposed and the verifier declares no reason it cannot be"}


# --- B-I4: evidence mandatory, replay re-reads it --------------------------------------------------

def test_an_item_without_evidence_fails(env):
    db, specs, store, clock, run = env
    r = run()
    assert not verify_run(db, r.run_id, FakeVerifier(truth_of(SERIES), evidence=False), None,
                          specs=specs, store=store, now=clock)
    assert {row[4] for row in items(db, r.run_id)} == {
        "no evidence bytes returned (evidence is mandatory)"}


def test_replay_rereads_evidence_and_catches_a_claim_the_evidence_does_not_support(env):
    db, specs, store, clock, run = env
    r = run()
    v = FakeVerifier(truth_of(SERIES))
    assert verify_run(db, r.run_id, v, None, specs=specs, store=store, now=clock)
    ids = [row[0] for row in items(db, r.run_id)]
    assert all(replay_item(db, store, i, v) for i in ids)
    # an altered stored claim (the verifier "misread" its evidence) no longer replays
    db.conn.execute("UPDATE verification_item SET observed_text = expected_text || '9', "
                    "expected_text = expected_text || '9' WHERE id = ?", (ids[0],))
    why = replay_check(db, store, ids[0], v)
    assert why is not None and "disagrees with the stored claim" in why
    # missing evidence
    db.conn.execute("UPDATE verification_item SET evidence_sha256 = NULL WHERE id = ?",
                    (ids[1],))
    assert replay_check(db, store, ids[1], v) == "no evidence archived for this item"
    # evidence that does not re-read
    (sha,), = q(db, "SELECT evidence_sha256 FROM verification_item WHERE id = ?", ids[2])
    path = store.root / "verify-fake" / sha[:2] / sha
    path.write_bytes(b"not json")
    with pytest.raises(RawIntegrityError):  # corrupt file: integrity failure first
        replay_item(db, store, ids[2], v)


def test_replay_of_evidence_that_cannot_be_reread_is_not_a_match(env):
    db, specs, store, clock, run = env

    class Broken(FakeVerifier):
        def reread(self, evidence, item):
            raise ValueError("cannot parse")

    r = run()
    assert verify_run(db, r.run_id, FakeVerifier(truth_of(SERIES)), None, specs=specs,
                      store=store, now=clock)
    item_id = items(db, r.run_id)[0][0]
    assert "does not re-read" in replay_check(db, store, item_id, Broken())


def test_replay_of_pre_0012_item_needs_the_registry_specs(env):
    db, specs, store, clock, run = env
    r = run()
    v = FakeVerifier(truth_of(SERIES))
    assert verify_run(db, r.run_id, v, None, specs=specs, store=store, now=clock)
    db.conn.execute("DELETE FROM verification_spec")
    item_id = items(db, r.run_id)[0][0]
    with pytest.raises(ValueError, match="predates migration 0012"):
        replay_item(db, store, item_id, v)
    assert replay_item(db, store, item_id, v, specs=specs)
    with pytest.raises(ValueError, match="belongs to"):
        other = FakeVerifier()
        other.source_name = "other"
        replay_item(db, store, item_id, other)


# --- B-M3: outage vs mismatch, escalation -----------------------------------------------------------

def _refetch(env, verifier, n_pages, **kw):
    db, specs, store, clock, _ = env
    register_verifier(verifier)
    http = FakeHttp(*[ok(payload(SERIES)) for _ in range(n_pages)])
    return run_with_refetch(db, store, FakeSource(), verifier, specs, http, now=clock, **kw), http


@pytest.mark.parametrize("error", [VerifierUnavailable("HTTP 503"),
                                   requests.ConnectionError("offline"),
                                   TimeoutError("slow")])
def test_verifier_outage_stops_without_redownload_and_escalates(env, error):
    db = env[0]
    res, http = _refetch(env, FakeVerifier(raises=error), 3)
    assert res.state == "failed-verification"
    assert len(http.calls) == 1  # ONE collector download, no refetch
    assert "verifier channel unavailable" in res.detail
    assert q(db, "SELECT count(*) FROM dataset_run") == [(1,)]
    assert events(db, "refetch") == []
    [(rid, outage)] = events(db, "verifier_outage")
    assert rid == res.run_id and type(error).__name__ in outage["error"]
    [(_, esc)] = events(db, "verification_escalated")
    assert esc["reason"] == "verifier_outage" and esc["run_ids"] == [res.run_id]


def test_genuine_mismatch_refetches_then_escalates_at_max_attempts(env):
    db = env[0]
    res, http = _refetch(env, FakeVerifier({}), 3, max_attempts=3)
    assert res.state == "failed-verification" and len(http.calls) == 3
    assert len(events(db, "refetch")) == 2 and events(db, "verifier_outage") == []
    [(rid, esc)] = events(db, "verification_escalated")
    runs = [r for (r,) in q(db, "SELECT id FROM dataset_run ORDER BY id")]
    assert esc["reason"] == "max_attempts" and esc["run_ids"] == runs and rid == runs[-1]
    assert "3 attempt(s)" in res.detail


def test_drift_raised_by_the_verifier_is_not_an_outage(env):
    db = env[0]
    res, http = _refetch(env, FakeVerifier(raises=ValueError("page layout drift")), 2,
                         max_attempts=2)
    assert len(http.calls) == 2 and events(db, "verifier_outage") == []


# --- B-I3: the verifier reads its own (live) client; recorded input -------------------------------

class _Spy:
    def __init__(self):
        self.calls = 0

    def get(self, *a, **k):
        self.calls += 1
        raise AssertionError("never used by the fake verifier")


def test_verifier_gets_its_own_client_and_recorded_runs_are_labelled(env):
    db, specs, store, clock, _ = env
    seen = []

    v = FakeVerifier(truth_of(SERIES))
    register_verifier(v)
    v.check = lambda items, http: (seen.append(http), FakeVerifier.check(v, items, http))[1]
    live = _Spy()
    res = run_with_refetch(db, store, FakeSource(), v, specs,
                           FakeHttp(ok(payload(SERIES))), now=clock,
                           input_origin="recorded", verify_http=live)
    assert res.state == "verified" and seen == [live]
    assert q(db, "SELECT input_origin, verifier_channel FROM verification") == [
        ("recorded", "live")]


def test_recorded_input_gets_one_attempt_and_pinned_channel_only_for_recorded(env):
    db, specs, store, clock, _ = env
    v = FakeVerifier({})
    register_verifier(v)
    http = FakeHttp(*[ok(payload(SERIES)) for _ in range(3)])
    res = run_with_refetch(db, store, FakeSource(), v, specs, http, now=clock,
                           input_origin="recorded", verifier_channel="pinned-bundle")
    assert res.state == "failed-verification" and len(http.calls) == 1
    assert events(db, "verification_escalated")[0][1]["reason"] == \
        "recorded_input_single_attempt"
    assert q(db, "SELECT verifier_channel FROM verification") == [("pinned-bundle",)]
    with pytest.raises(ValueError, match="only for recorded input"):
        run_with_refetch(db, store, FakeSource(), v, specs, FakeHttp(), now=clock,
                         verifier_channel="pinned-bundle")


# --- B-I3 through the CLI: --bundle verifies over live HTTP by default ------------------------------

from tests.ingest.test_bundle import _wb_specs, _WBNet, _write_registry  # noqa: E402


def _capture_wb(tmp_path):
    reg = _write_registry(tmp_path / "registry.yaml", _wb_specs())
    out = tmp_path / "bundle"
    assert main(["--registry", str(reg), "capture", "worldbank", "--output", str(out),
                 "--indicator", "SP.POP.TOTL"], http_for=lambda _n: _WBNet()) == 0
    return reg, out


class _LiveVerifierOnly:
    """The 'internet' during a recorded replay: the verifier's CSV channel answers, the
    collector's JSON API must never be called (its input is the pinned bundle)."""

    def __init__(self):
        self.net = _WBNet()
        self.urls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.urls.append(url)
        assert "/v2/country/" not in url, "the collector must read the bundle, not the network"
        return self.net.get(url, params=params, headers=headers, timeout=timeout)


def _run(reg, db_path, raw, bundle, http_for, *extra):
    return main(["--db", str(db_path), "--raw-dir", str(raw), "--registry", str(reg), "run",
                 "worldbank", "--bundle", str(bundle), "--indicator", "SP.POP.TOTL", *extra],
                http_for=http_for)


def test_cli_bundle_run_verifies_against_live_http(tmp_path, capsys):
    reg, bundle = _capture_wb(tmp_path)
    live = _LiveVerifierOnly()
    db_path = tmp_path / "p.sqlite3"
    assert _run(reg, db_path, tmp_path / "raw", bundle, lambda _n: live) == 0, \
        capsys.readouterr()
    assert live.urls and all("downloadformat=csv" in u for u in live.urls)
    db = open_db(db_path)
    try:
        assert q(db, "SELECT v.input_origin, v.verifier_channel, r.input_origin FROM "
                     "verification v JOIN dataset_run r ON r.id = v.dataset_run_id") == [
            ("recorded", "live", "recorded")]
    finally:
        db.close()


def test_cli_bundle_run_offline_fails_clearly_and_serves_nothing(tmp_path, capsys):
    reg, bundle = _capture_wb(tmp_path)
    capsys.readouterr()

    class Offline:
        def get(self, *a, **k):
            raise requests.ConnectionError("network is unreachable")

    db_path = tmp_path / "p.sqlite3"
    assert _run(reg, db_path, tmp_path / "raw", bundle, lambda _n: Offline()) == 1
    out = capsys.readouterr().out
    assert "failed-verification" in out and "verifier channel unavailable" in out
    db = open_db(db_path)
    try:
        assert q(db, "SELECT count(*) FROM served_observation WHERE kind = 'fetched'") == [(0,)]
        assert [d["reason"] for _, d in events(db, "verification_escalated")] == [
            "verifier_outage"]
    finally:
        db.close()


def test_cli_pinned_verifier_is_explicit_and_recorded(tmp_path, capsys):
    reg, bundle = _capture_wb(tmp_path)

    def no_network(_n):
        raise AssertionError("pinned mode is offline")
    db_path = tmp_path / "p.sqlite3"
    assert _run(reg, db_path, tmp_path / "raw", bundle, no_network, "--pinned-verifier") == 0
    db = open_db(db_path)
    try:
        assert q(db, "SELECT verifier_channel FROM verification") == [("pinned-bundle",)]
    finally:
        db.close()
    rc = main(["--db", str(db_path), "--registry", str(reg), "run", "worldbank",
               "--pinned-verifier"])
    assert rc == 2 and "--pinned-verifier only applies" in capsys.readouterr().err


# --- registration contract ---------------------------------------------------------------------------

def test_registration_requires_reread_request_key_and_reasons():
    class NoReread:
        source_name = "fake"
        not_compared: dict = {}

        def check(self, items, http):
            return []

        def request_key(self, item):
            return item.series_id

    with pytest.raises(ValueError, match="contract"):
        register_verifier(NoReread())

    class BadReason(FakeVerifier):
        not_compared = {"value": "no"}

    with pytest.raises(ValueError, match="contract"):
        register_verifier(BadReason())


# --- migration 0012 on a populated 0011 database ------------------------------------------------------

def test_0012_backfills_procedure_and_marks_old_recorded_verifications_pinned(tmp_path,
                                                                               monkeypatch):
    mig = tmp_path / "mig11"
    mig.mkdir()
    for f in MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql"):
        if f.stem < "0012":
            (mig / f.name).write_bytes(f.read_bytes())
    monkeypatch.setattr(dbmod, "MIGRATIONS_DIR", mig)
    p = tmp_path / "old.db"
    d = open_db(p)
    sync_registry(d, [spec("s1")])
    live = d.begin_run("fake", "k", "t")
    rec = d.begin_run("fake", "k", "t", input_origin="recorded")
    for run_id in (live, rec):
        d.set_run_state(run_id, "verified")
        d.conn.execute("INSERT INTO verification(dataset_run_id, seed, sample_size, passed, "
                       "created_at) VALUES (?, 1, 1, 1, 't')", (run_id,))
    d.add_event("t", "revision", live, {"series_id": "s1", "period": "2024", "old": "1",
                                        "new": "2"})
    d.close()
    monkeypatch.setattr(dbmod, "MIGRATIONS_DIR", MIGRATIONS_DIR)
    d = open_db(p)
    try:
        assert q(d, "SELECT dataset_run_id, sample_procedure, input_origin, verifier_channel "
                    "FROM verification ORDER BY id") == [
            (live, "v1-python-random-sample", "live", "live"),
            (rec, "v1-python-random-sample", "recorded", "pinned-bundle")]
        assert q(d, "SELECT kind FROM event") == [("revision",)]
        d.add_event("t", "verification_escalated", live, {"reason": "x"})
        with pytest.raises(sqlite3.IntegrityError):
            d.add_event("t", "no_such_kind", live, {})
        names = {n for (n,) in q(d, "SELECT name FROM sqlite_master WHERE type='trigger'")}
        assert "dataset_run_withdraw_reviewed" in names
        with pytest.raises(sqlite3.IntegrityError, match="withdraw only"):
            d.set_run_state(live, "withdrawn")
        d.withdraw_run(live, "reviewed", "t")  # the trigger still reads the rebuilt event
        assert d.run_state(live) == "withdrawn"
    finally:
        d.close()


def test_verifier_contract_is_implemented_by_every_registered_source():
    from ingest.operations import VERIFIER_OPS
    for name, ops in VERIFIER_OPS.items():
        v = ops.make()
        verifiers._check_contract(v)
        assert set(v.not_compared) <= {"unit", "flag"}, name

