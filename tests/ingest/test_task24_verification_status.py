"""Task 24: re-review 2 fixes (docs/superpowers/handoff/reports/final-review/
rereview-2-verification-status.md) and re-review 1 M-4.

- I1: a cell that mismatched in a failed verification is re-checked by every later attempt of
  the dataset (reason 'previously-failed') until a verification passes, so a deterministic
  defect is detected with probability 1 from the second attempt on, across run_with_refetch
  attempts and separate (scheduler) retries.
- M1: verify_run re-reads every item from the evidence it returned (a stored match replays by
  construction); empty evidence fails.
- M3: World Bank exponent rewrite is bounded.
- M5: a pinned-bundle verification never confirms currency; status shows the channel.
- M6: the read-only report retries once with plain mode=ro after an immutable read error.
- RR1 M-4: a pending-verification run older than 24 h is counted and shows its remedy.
"""
import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from ingest import verifiers
from ingest import verify as verify_mod
from ingest.db import open_db, read_db_readonly
from ingest.models import Observation
from ingest.operations import group_specs
from ingest.pipeline import run_dataset
from ingest.rawstore import RawStore
from ingest.registry import sync_registry
from ingest.status import build_status, render_text
from ingest.verifiers import ItemResult, register_verifier
from ingest.verify import draw_sample, run_with_refetch, verify_run
from tests.ingest.fake_verifier import FakeVerifier
from tests.ingest.fakes import FakeHttp, FakeSource, ok, payload, spec, truth_of

T0 = datetime(2026, 11, 13, tzinfo=timezone.utc)
# one monthly series, 36 years of history: the step-4 sample is far from a census
SERIES = {"m1": [[f"{y}-{m:02d}", f"{y}.{m}"] for y in range(1990, 2026)
                 for m in range(1, 13)]}
DEFECT = ("m1", "2003-07")  # the parser's deterministic wrong cell (history, not latest)
TRUTH = {**truth_of(SERIES), DEFECT: "999.9"}


class Clock:
    def __init__(self):
        self.t = T0

    def __call__(self):
        self.t += timedelta(seconds=1)
        return self.t


@pytest.fixture(autouse=True)
def empty_registry(monkeypatch):
    monkeypatch.setattr(verifiers, "_REGISTRY", {})


@pytest.fixture
def env(db, tmp_path):
    specs = [spec("m1", frequency="M")]
    sync_registry(db, specs)
    return db, specs, RawStore(tmp_path / "raw"), Clock()


def _fetch(env):
    db, specs, store, clock = env
    return run_dataset(db, store, FakeSource(), specs, FakeHttp(ok(payload(SERIES))), clock)


def _defect_drawn(env, run_id, seed) -> str | None:
    db, specs, _, _ = env
    for item in draw_sample(db, run_id, seed, specs=specs, verifier=FakeVerifier()):
        if (item.series_id, item.period) == DEFECT:
            return item.reason
    return None


def _seeds(env, run_id):
    """A seed whose fresh draw catches the defect and one whose fresh draw misses it."""
    catch = next(s for s in range(500) if _defect_drawn(env, run_id, s))
    miss = next(s for s in range(500) if not _defect_drawn(env, run_id, s))
    return catch, miss


# --- I1 ------------------------------------------------------------------------------------

def test_detection_probability_becomes_one_on_the_next_attempt(env):
    db, specs, store, clock = env
    first = _fetch(env)
    catch, miss = _seeds(env, first.run_id)
    # without history the draw is random: some seeds miss the defect (probability < 1)
    assert _defect_drawn(env, first.run_id, miss) is None
    assert not verify_run(db, first.run_id, FakeVerifier(TRUTH), None, seed=catch,
                          specs=specs, store=store, now=clock)
    second = _fetch(env)  # identical bytes: previous run failed, so re-processed
    assert second.state == "pending-verification"
    reasons = [_defect_drawn(env, second.run_id, s) for s in range(200)]
    assert reasons == ["previously-failed"] * 200  # every draw now checks it
    assert not verify_run(db, second.run_id, FakeVerifier(TRUTH), None, seed=miss,
                          specs=specs, store=store, now=clock)
    design = json.loads(db.conn.execute(
        "SELECT sample_design FROM verification ORDER BY id DESC LIMIT 1").fetchone()[0])
    assert design["n_previously_failed"] == 1
    assert design["counts"]["previously-failed"] == 1


def test_sticky_across_refetch_attempts_and_scheduler_retries_then_reset(env, monkeypatch):
    db, specs, store, clock = env
    probe = _fetch(env)
    catch, miss = _seeds(env, probe.run_id)
    db.set_run_state(probe.run_id, "failed-validation")  # discard the probe run
    seeds = iter([catch, miss, miss, miss, miss])
    monkeypatch.setattr(verify_mod.secrets, "randbits", lambda _n: next(seeds))
    v = FakeVerifier(TRUTH)
    register_verifier(v)

    def attempt(n):
        return run_with_refetch(db, store, FakeSource(), v, specs,
                                FakeHttp(*[ok(payload(SERIES)) for _ in range(n)]),
                                max_attempts=n, now=clock)

    res = attempt(3)  # catch, then two attempts whose fresh draw would have missed
    assert res.state == "failed-verification"
    retry = attempt(2)  # a later scheduler retry of the same dataset: still caught
    assert retry.state == "failed-verification"
    rows = db.conn.execute(
        "SELECT v.dataset_run_id, i.reason, i.match FROM verification_item i "
        "JOIN verification v ON v.id = i.verification_id "
        "WHERE i.series_id = ? AND i.period = ? ORDER BY v.id", DEFECT).fetchall()
    assert [(reason, match) for _, reason, match in rows] == [
        (rows[0][1], 0)] + [("previously-failed", 0)] * 4
    assert rows[0][1] != "previously-failed"

    # the publisher fixes the cell: the next attempt passes and the chain resets
    good = FakeVerifier(truth_of(SERIES))
    monkeypatch.setattr(verifiers, "_REGISTRY", {})
    register_verifier(good)
    seeds = iter([miss])
    monkeypatch.setattr(verify_mod.secrets, "randbits", lambda _n: next(seeds))
    fixed = run_with_refetch(db, store, FakeSource(), good, specs,
                             FakeHttp(ok(payload(SERIES))), max_attempts=1, now=clock)
    assert fixed.state == "verified"
    later = db.begin_run("fake", db.run_info(fixed.run_id)[2], "2026-11-14T00:00:00+00:00")
    assert db.previously_failed_keys(later) == set()


def test_outage_items_are_not_carried_as_defects(env):
    db, specs, store, clock = env
    first = _fetch(env)
    assert not verify_run(db, first.run_id, FakeVerifier(raises=OSError("down")), None,
                          seed=1, specs=specs, store=store, now=clock)
    second = _fetch(env)
    assert db.previously_failed_keys(second.run_id) == set()


# --- M1 ------------------------------------------------------------------------------------

class LyingReread(FakeVerifier):
    """check() claims the truth, but its evidence re-reads to something else."""

    def reread(self, evidence, item):
        res = super().reread(evidence, item)
        return ItemResult(res.series_id, res.period, "0", res.evidence_url,
                          observed_decimal=".", evidence=evidence)


def test_an_item_whose_evidence_does_not_replay_fails_at_verify_time(env):
    db, specs, store, clock = env
    r = _fetch(env)
    assert not verify_run(db, r.run_id, LyingReread(truth_of(SERIES)), None, seed=1,
                          specs=specs, store=store, now=clock)
    notes = {n for (n,) in db.conn.execute("SELECT note FROM verification_item")}
    assert all(n and "replay would fail" in n for n in notes)


def test_empty_evidence_fails(env):
    db, specs, store, clock = env

    class Empty(FakeVerifier):
        def check(self, items, http):
            return [ItemResult(r.series_id, r.period, r.observed_text, r.evidence_url,
                               evidence=b"") for r in super().check(items, http)]

    r = _fetch(env)
    assert not verify_run(db, r.run_id, Empty(truth_of(SERIES)), None, seed=1, specs=specs,
                          store=store, now=clock)
    notes = {n for (n,) in db.conn.execute("SELECT note FROM verification_item")}
    assert notes == {"empty evidence bytes (evidence is mandatory)"}


def test_reread_many_parses_each_shared_evidence_once(env):
    db, specs, store, clock = env
    shared = b'{"shared": true}'
    calls = []

    class Shared(FakeVerifier):
        def check(self, items, http):
            return [ItemResult(i.series_id, i.period, TRUTH_OK[(i.series_id, i.period)],
                               "http://v", evidence=shared) for i in items]

        def reread_many(self, evidence, items):
            calls.append(len(items))
            return [ItemResult(i.series_id, i.period, TRUTH_OK[(i.series_id, i.period)],
                               "http://v", evidence=evidence) for i in items]

    r = _fetch(env)
    assert verify_run(db, r.run_id, Shared(), None, seed=1, specs=specs, store=store,
                      now=clock)
    n = db.conn.execute("SELECT COUNT(*) FROM verification_item").fetchone()[0]
    assert calls == [n]


TRUTH_OK = truth_of(SERIES)


# --- M3 ------------------------------------------------------------------------------------

def test_world_bank_exponent_is_bounded():
    from ingest.verifiers.worldbank import MAX_EXPONENT, _plain
    assert MAX_EXPONENT == 400
    assert _plain("1E-400") == "0." + "0" * 399 + "1"
    assert len(_plain("1E+400")) == 401
    for bad in ("1E+401", "1E-401", "1E+999999999", "-2.5E-000000000000000000000000500"):
        with pytest.raises(ValueError, match="exponent"):
            _plain(bad)


# --- M5 / RR1 M-4: status ------------------------------------------------------------------

def _verified(db, key, value, at, channel, rows=True):
    run = db.begin_run("fake", key, at)
    fid = db.record_raw_fetch(source_name="fake", run_id=run, url="http://x", params_json=None,
                              fetched_at=at, http_status=200, sha256=f"{key}{at}{value}",
                              path="p", n_bytes=1, ok=True)
    if rows:
        db.write_observations(run, [(Observation.from_raw("s1", "2024", value), fid, at)])
    db.set_run_state(run, "verified")
    if rows:
        db.add_verification(run, 1, 1, True, at, sample_procedure="prumo-sample-v2",
                            sample_design={}, input_origin="recorded",
                            verifier_channel=channel)
    return run


def test_pinned_bundle_verification_never_confirms_currency(db):
    sp = spec("s1")
    sync_registry(db, [sp])
    key = group_specs([sp])[0].key()
    at = T0.isoformat()
    _verified(db, key, "1", at, "pinned-bundle")
    _verified(db, key, "1", (T0 + timedelta(hours=1)).isoformat(), None, rows=False)  # shortcut
    report = build_status(db, [sp], now=lambda: T0 + timedelta(hours=2))
    s = next(x for src in report.sources for x in src.series if x.id == "s1")
    assert s.availability == "verified" and s.last_confirmed_current is None
    assert (s.stale, s.stale_reason) == (True, "pinned_bundle_only")
    (d,) = next(src for src in report.sources if src.name == "fake").datasets
    assert d.verifier_channel == "pinned-bundle"
    assert "last verified via pinned-bundle" in render_text(report)

    live_at = (T0 + timedelta(hours=3)).isoformat()
    _verified(db, key, "1", live_at, "live")
    report = build_status(db, [sp], now=lambda: T0 + timedelta(hours=4))
    s = next(x for src in report.sources for x in src.series if x.id == "s1")
    assert s.last_confirmed_current == live_at and s.stale is False


def test_stuck_pending_verification_is_counted_with_its_remedy(db):
    sp = spec("s1")
    sync_registry(db, [sp])
    run = db.begin_run("fake", group_specs([sp])[0].key(), T0.isoformat())
    db.set_run_state(run, "pending-verification")
    report = build_status(db, [sp], now=lambda: T0 + timedelta(hours=25))
    assert report.totals["pending_stuck"] == 1
    text = render_text(report)
    assert f"python -m ingest verify {run}" in text
    assert "pending verification over 24h 1" in text


# --- M6 ------------------------------------------------------------------------------------

def test_read_only_report_retries_once_with_plain_mode_ro(tmp_path):
    path = tmp_path / "p.db"
    open_db(path).close()
    seen = []

    def read(db):
        seen.append(db.immutable)
        if len(seen) == 1:
            raise sqlite3.DatabaseError("database disk image is malformed")
        return "ok"

    assert read_db_readonly(path, read) == "ok"
    assert seen == [True, False]


def test_read_only_report_does_not_retry_a_plain_open(tmp_path):
    path = tmp_path / "p.db"
    writer = open_db(path)  # a running writer: -wal exists, plain mode=ro is used
    writer.conn.execute("SELECT 1")
    seen = []

    def read(db):
        seen.append(db.immutable)
        raise sqlite3.DatabaseError("boom")

    try:
        with pytest.raises(sqlite3.DatabaseError):
            read_db_readonly(path, read)
    finally:
        writer.close()
    assert seen == [False]
