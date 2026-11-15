"""Decision 1 (vintage dedupe): the identical-CONTENT short-circuit generalises Ruling D.

A run whose would-be observation rows (series_id, period, value_text, status_flag,
released_at) and quarantine rows (series_id, raw_period, raw_value, reason) equal, as sorted
multisets, those of its base run (Db.content_base_run) is recorded `verified` with nothing of
its own: no observations, no quarantine, no events, no verification. Different bytes are
enough to miss the byte short-circuit, so every test here varies the bytes (trailing
whitespace the JSON parser ignores) while keeping the parsed values."""
import json
from datetime import datetime, timedelta, timezone

import pytest

import ingest.pipeline as pipeline_mod
from ingest import verifiers as _verifiers
from ingest.db import RunContent, observation_content, quarantine_content
from ingest.pipeline import DatasetRunResult, run_dataset
from ingest.rawstore import RawStore
from ingest.registry import sync_registry
from ingest.sources import RawResponse
from ingest.status import build_status
from ingest.verifiers import register_verifier
from ingest.verify import run_with_refetch, verify_run
from tests.ingest.fake_verifier import FakeVerifier
from tests.ingest.fakes import FakeHttp, FakeSource, ok, payload, spec, truth_of

BASE = {"s1": [["2023", "1.5"], ["2024", "2.0"]], "s2": [["2024", "10"]]}
T0 = datetime(2026, 11, 15, 6, 0, tzinfo=timezone.utc)


def _ts(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def body(series=BASE, variant: int = 0) -> bytes:
    """payload(series) with `variant` trailing newlines: other bytes, same parsed values."""
    return payload(series) + b"\n" * variant


class Clock:
    def __init__(self, start: datetime = T0):
        self.t = start

    def __call__(self):
        self.t += timedelta(seconds=1)
        return self.t


@pytest.fixture
def env(db, tmp_path):
    specs = [spec("s1"), spec("s2")]
    sync_registry(db, specs)
    store = RawStore(tmp_path / "raw")
    clock = Clock()

    def run(*bodies: bytes, verify: bool = False):
        r = run_dataset(db, store, FakeSource(pages=len(bodies)), specs,
                        FakeHttp(*[ok(b) for b in bodies]), clock)
        if verify and r.state == "pending-verification":
            assert db.transition_run_state(r.run_id, "pending-verification", "verified")
        return r

    return db, specs, store, clock, run


def q(db, sql, *args):
    return db.conn.execute(sql, args).fetchall()


def own(db, table, run_id):
    return q(db, f"SELECT count(*) FROM {table} WHERE dataset_run_id = ?", run_id)[0][0]


def events_of(db, run_id):
    return q(db, "SELECT kind, detail_json FROM event WHERE dataset_run_id = ? ORDER BY id",
             run_id)


def served(db):
    return dict(((s, p), v) for s, p, v in
                q(db, "SELECT series_id, period, value_text FROM served_observation"))


def assert_content_shortcut(db, r, base_run_id):
    assert (r.state, r.n_written, r.n_quarantined) == ("verified", 0, 0)
    assert str(base_run_id) in r.detail and "identical" in r.detail
    assert db.run_state(r.run_id) == "verified"
    assert own(db, "observation", r.run_id) == 0
    assert own(db, "quarantine", r.run_id) == 0
    assert own(db, "verification", r.run_id) == 0
    assert events_of(db, r.run_id) == []
    assert own(db, "raw_fetch", r.run_id) >= 1  # the fetched bytes stay as audit evidence


# --- (a) different bytes, identical values -------------------------------------------------------

def test_different_bytes_identical_values_short_circuit(env):
    db, _, _, _, run = env
    base = run(body(), verify=True)
    n = q(db, "SELECT count(*) FROM observation")[0][0]
    r = run(body(variant=1))
    assert_content_shortcut(db, r, base.run_id)
    assert r == DatasetRunResult("verified", r.run_id, 0, 0, detail=r.detail)
    assert q(db, "SELECT count(*) FROM observation")[0][0] == n
    assert served(db) == {("s1", "2023"): "1.5", ("s1", "2024"): "2.0", ("s2", "2024"): "10"}
    # a further identical-values run walks back over the short-circuit to the same base
    again = run(body(variant=2))
    assert_content_shortcut(db, again, base.run_id)


# --- (b) released_at is part of the identity -------------------------------------------------------

def _stamp_observations(monkeypatch, fields: dict):
    """Every observation the pipeline validates gets `fields` (read at each call, so a test
    can change them between runs): the fake source carries no release date or flag."""
    real = pipeline_mod.validate

    def stamped(s, rows):
        obs, rej = real(s, rows)
        return [o.model_copy(update=dict(fields)) for o in obs], rej
    monkeypatch.setattr(pipeline_mod, "validate", stamped)


def test_identical_values_different_released_at_are_stored(env, monkeypatch):
    db, _, _, _, run = env
    fields = {"released_at": datetime(2026, 11, 1, tzinfo=timezone.utc)}
    _stamp_observations(monkeypatch, fields)
    run(body(), verify=True)
    fields["released_at"] = datetime(2026, 11, 14, tzinfo=timezone.utc)
    r = run(body(variant=1))
    assert (r.state, r.n_written) == ("pending-verification", 3)
    assert {x for (x,) in q(db, "SELECT released_at FROM observation WHERE dataset_run_id = ?",
                            r.run_id)} == {"2026-11-14T00:00:00+00:00"}


def test_identical_values_and_released_at_short_circuit(env, monkeypatch):
    db, _, _, _, run = env
    _stamp_observations(monkeypatch, {"released_at": datetime(2026, 11, 1, tzinfo=timezone.utc)})
    base = run(body(), verify=True)
    assert_content_shortcut(db, run(body(variant=1)), base.run_id)


# --- (c) quarantine rows are part of the identity -------------------------------------------------

WITH_BAD = {"s1": [["2023", "1.5"], ["2024", "2.0"], ["2025", "n/a"]], "s2": [["2024", "10"]]}
OTHER_BAD = {"s1": [["2023", "1.5"], ["2024", "2.0"], ["2025", "--"]], "s2": [["2024", "10"]]}


def test_identical_values_different_quarantine_are_stored(env):
    db, _, _, _, run = env
    run(body(WITH_BAD), verify=True)
    r = run(body(OTHER_BAD))
    assert (r.state, r.n_written, r.n_quarantined) == ("pending-verification", 3, 1)


def test_identical_values_without_the_base_quarantine_are_stored(env):
    db, _, _, _, run = env
    run(body(WITH_BAD), verify=True)
    r = run(body(BASE))
    assert (r.state, r.n_written, r.n_quarantined) == ("pending-verification", 3, 0)


def test_identical_values_and_quarantine_short_circuit(env):
    db, _, _, _, run = env
    base = run(body(WITH_BAD), verify=True)
    assert_content_shortcut(db, run(body(WITH_BAD, variant=1)), base.run_id)


# --- (d) one changed value ---------------------------------------------------------------------

def test_one_changed_value_is_stored_in_full_and_verifiable(env, monkeypatch):
    monkeypatch.setattr(_verifiers, "_REGISTRY", {})
    db, specs, store, clock, run = env
    run(body(), verify=True)
    changed = {"s1": [["2023", "1.5"], ["2024", "2.1"]], "s2": [["2024", "10"]]}
    r = run(body(changed))
    assert (r.state, r.n_written) == ("pending-verification", 3)  # a complete vintage
    assert [k for k, _ in events_of(db, r.run_id)] == ["revision"]
    assert verify_run(db, r.run_id, FakeVerifier(truth_of(changed)), None, specs=specs,
                      store=store, now=clock)
    assert db.run_state(r.run_id) == "verified"
    assert served(db)[("s1", "2024")] == "2.1"


# --- (e) A, B, A ---------------------------------------------------------------------------------

def test_a_b_a_third_run_is_stored(env):
    db, _, _, _, run = env
    b_vals = {"s1": [["2023", "1.5"], ["2024", "2.1"]], "s2": [["2024", "10"]]}
    run(body(), verify=True)
    run(body(b_vals), verify=True)
    r = run(body(variant=1))
    assert (r.state, r.n_written) == ("pending-verification", 3)


# --- (f) a non-verified previous run is never a base --------------------------------------------

@pytest.mark.parametrize("prev_state", ["failed-verification", "pending-verification",
                                        "failed-validation", "blocked-stale"])
def test_previous_run_not_verified_is_stored(env, prev_state):
    db, _, _, _, run = env
    run(body(), verify=True)
    middle = run(body(variant=1)).run_id  # short-circuited onto the base ...
    db.set_run_state(middle, prev_state)  # ... then (test) put into a non-verified state
    r = run(body(variant=2))
    assert (r.state, r.n_written) == ("pending-verification", 3)


def test_previous_failed_verification_with_rows_is_stored(env):
    db, _, _, _, run = env
    first = run(body())
    db.set_run_state(first.run_id, "failed-verification")
    r = run(body(variant=1))
    assert (r.state, r.n_written) == ("pending-verification", 3)


def test_no_previous_run_is_stored(env):
    _, _, _, _, run = env
    assert run(body()).state == "pending-verification"


# --- (g) withdrawal of the base ---------------------------------------------------------------

def test_after_withdrawing_the_base_the_next_identical_fetch_is_stored(env):
    db, _, _, _, run = env
    base = run(body(), verify=True)
    short = run(body(variant=1))
    assert short.state == "verified"
    withdrawn = db.withdraw_run(base.run_id, "test: wrong vintage", _ts(T0 + timedelta(hours=1)))
    assert withdrawn == [base.run_id, short.run_id]  # cascade covers the content short-circuit
    r = run(body(variant=2))
    assert (r.state, r.n_written) == ("pending-verification", 3)


# --- (h) recorded input -------------------------------------------------------------------------

NOV01 = "2026-11-01T00:00:00+00:00"
NOV13 = datetime(2026, 11, 13, tzinfo=timezone.utc)


class Recorded(FakeSource):
    """One recorded response carrying its ORIGINAL receipt time (a replayed bundle)."""

    def __init__(self, raw: bytes, receipt: str):
        super().__init__()
        self.raw, self.receipt = raw, receipt

    def fetch(self, specs, http):
        yield RawResponse(url="http://fake/data/1", params={"page": 1}, status=200,
                          body=self.raw, fetched_at=self.receipt)


def test_recorded_stale_bundle_with_identical_values_is_blocked_stale(db, tmp_path):
    sp = spec("s1")
    sync_registry(db, [sp])
    store = RawStore(tmp_path / "raw")
    vals = {"s1": [["2024", "2.0"]]}
    live = run_dataset(db, store, FakeSource(), [sp], FakeHttp(ok(body(vals))),
                       now=lambda: NOV13)
    assert db.transition_run_state(live.run_id, "pending-verification", "verified")
    old = run_dataset(db, store, Recorded(body(vals, variant=1), NOV01), [sp], None,
                      now=lambda: NOV13, input_origin="recorded")
    assert (old.state, old.n_written) == ("blocked-stale", 0)
    assert [k for k, _ in events_of(db, old.run_id)] == ["stale_refusal"]


def test_recorded_identical_values_not_stale_is_verified_no_op(db, tmp_path):
    sp = spec("s1")
    sync_registry(db, [sp])
    store = RawStore(tmp_path / "raw")
    vals = {"s1": [["2024", "2.0"]]}
    first = run_dataset(db, store, Recorded(body(vals), NOV01), [sp], None,
                        now=lambda: NOV13, input_origin="recorded")
    assert first.state == "pending-verification"
    assert db.transition_run_state(first.run_id, "pending-verification", "verified")
    again = run_dataset(db, store, Recorded(body(vals, variant=1), NOV01), [sp], None,
                        now=lambda: NOV13, input_origin="recorded")
    assert_content_shortcut(db, again, first.run_id)


# --- (i) multisets, not sets ---------------------------------------------------------------------

DUP_PAGE = {"s1": [["2024", "9"]], "s2": []}
FIRST_PAGE = {"s1": [["2023", "1.5"], ["2024", "9"]], "s2": [["2024", "10"]]}


def test_quarantine_rows_compare_as_a_multiset(env):
    """s1 2024 in two pages -> two duplicate_period rows; in three pages -> three. As sets
    those are equal; as multisets they are not, so the three-page run is stored."""
    db, _, _, _, run = env
    two = run(body(FIRST_PAGE), body(DUP_PAGE), verify=True)
    assert two.n_quarantined == 2
    three = run(body(FIRST_PAGE), body(DUP_PAGE), body(DUP_PAGE, variant=1))
    assert (three.state, three.n_quarantined) == ("pending-verification", 3)
    assert db.transition_run_state(three.run_id, "pending-verification", "verified")
    same = run(body(FIRST_PAGE, variant=1), body(DUP_PAGE), body(DUP_PAGE, variant=1))
    assert_content_shortcut(db, same, three.run_id)


def test_observation_rows_compare_as_a_multiset(env, monkeypatch):
    """A (series, period) written from two responses appears twice; one copy is not the same
    content (forced through validate: the fake source cannot produce it on its own)."""
    db, _, _, _, run = env
    real = pipeline_mod.validate
    copies = [2]

    def doubled(s, rows):
        obs, rej = real(s, rows)
        if s.id == "s2":
            obs = [o.model_copy(update={"response_index": i}) for o in obs
                   for i in range(copies[0])]
        return obs, rej
    monkeypatch.setattr(pipeline_mod, "validate", doubled)
    page2 = {"s1": [], "s2": []}
    base = run(body(), body(page2), verify=True)
    assert base.n_written == 4
    copies[0] = 1
    once = run(body(variant=1), body(page2))
    assert (once.state, once.n_written) == ("pending-verification", 3)
    assert db.transition_run_state(once.run_id, "pending-verification", "verified")
    copies[0] = 2
    twice = run(body(variant=2), body(page2))
    assert (twice.state, twice.n_written) == ("pending-verification", 4)
    assert db.transition_run_state(twice.run_id, "pending-verification", "verified")
    assert_content_shortcut(db, run(body(variant=3), body(page2)), twice.run_id)


# --- (j) status: a content short-circuit confirms the series current ---------------------------

MONTHLY = {"m1": [["2026-08", "1.0"], ["2026-09", "1.1"]]}


def test_status_counts_a_content_short_circuit_as_confirmed_current(db, tmp_path, monkeypatch):
    monkeypatch.setattr(_verifiers, "_REGISTRY", {})
    specs = [spec("m1", frequency="M")]
    sync_registry(db, specs)
    store = RawStore(tmp_path / "raw")

    def fetch(at, variant):
        r = run_dataset(db, store, FakeSource(), specs, FakeHttp(ok(body(MONTHLY, variant))),
                        lambda: at)
        if r.state == "pending-verification":
            assert verify_run(db, r.run_id, FakeVerifier(truth_of(MONTHLY)), None,
                              specs=specs, store=store, now=lambda: at)
        return r

    fetch(T0, 0)
    t1 = T0 + timedelta(hours=30)
    again = fetch(t1, 1)
    assert again.state == "verified" and again.n_written == 0 and "identical" in again.detail

    def series(at):
        report = build_status(db, specs, now=lambda: at)
        return next(s for src in report.sources for s in src.series if s.id == "m1")
    s = series(t1 + timedelta(hours=1))
    assert s.real_data_fetched_at == _ts(T0)
    assert s.last_confirmed_current == _ts(t1)
    assert s.stale is False and s.stale_reason is None
    assert series(t1 + timedelta(hours=25)).stale is True  # 1-day policy, judged on t1


# --- (l) Ruling M: empty series keep their format_change event ---------------------------------

def test_run_with_an_empty_series_is_not_content_short_circuited(env):
    db, _, _, _, run = env
    vals = {"s1": BASE["s1"], "s2": [["bad", "10"]]}  # s2: every row quarantined
    first = run(body(vals), verify=True)
    assert [k for k, _ in events_of(db, first.run_id)] == ["format_change"]
    r = run(body(vals, variant=1))
    assert (r.state, r.n_written, r.n_quarantined) == ("pending-verification", 2, 1)
    (kind, detail), = events_of(db, r.run_id)
    assert kind == "format_change"
    assert json.loads(detail)["series_id"] == "s2"


# --- (m) run_with_refetch returns the content short-circuit as is ------------------------------

def test_run_with_refetch_returns_the_content_short_circuit_without_verifying(env, monkeypatch):
    monkeypatch.setattr(_verifiers, "_REGISTRY", {})
    db, specs, store, clock, run = env
    base = run(body(), verify=True)
    v = FakeVerifier(truth_of(BASE))
    register_verifier(v)
    r = run_with_refetch(db, store, FakeSource(), v, specs, FakeHttp(ok(body(variant=1))),
                         now=clock)
    assert_content_shortcut(db, r, base.run_id)
    assert v.calls == []


# --- fix round 1 ----------------------------------------------------------------------------------

def test_identical_values_different_status_flag_are_stored(env, monkeypatch):
    db, _, _, _, run = env
    fields = {"status_flag": None}
    _stamp_observations(monkeypatch, fields)
    run(body(), verify=True)
    fields["status_flag"] = "p"  # provisional now
    r = run(body(variant=1))
    assert (r.state, r.n_written) == ("pending-verification", 3)


NULLS = {"s1": [["2023", "1.5"], ["2024", "2.0"], [None, "7"], ["2025", "null"]],
         "s2": [["2024", "10"]]}


def test_quarantine_rows_with_null_period_or_value_short_circuit(env):
    db, _, _, _, run = env
    base = run(body(NULLS), verify=True)
    assert sorted(db.run_content(base.run_id).quarantine, key=str) == sorted(
        [("s1", None, "7", "bad_period"), ("s1", "2025", None, "non_numeric")], key=str)
    assert_content_shortcut(db, run(body(NULLS, variant=1)), base.run_id)


def test_a_a_shortcut_b_a_last_run_is_stored(env):
    db, _, _, _, run = env
    b_vals = {"s1": [["2023", "1.5"], ["2024", "2.1"]], "s2": [["2024", "10"]]}
    a = run(body(), verify=True)
    assert_content_shortcut(db, run(body(variant=1)), a.run_id)
    run(body(b_vals), verify=True)
    r = run(body(variant=2))
    assert (r.state, r.n_written) == ("pending-verification", 3)


def test_stored_run_content_equals_the_would_be_content_of_the_shared_helpers(env, monkeypatch):
    """What the writers store reads back exactly as the tuples the comparison builds."""
    db, specs, _, _, run = env
    _stamp_observations(monkeypatch, {"status_flag": "e",
                                      "released_at": datetime(2026, 11, 2, 9, 30,
                                                              tzinfo=timezone.utc)})
    r = run(body(NULLS))
    resp = RawResponse(url="u", params=None, status=200, body=body(NULLS))
    parsed = FakeSource().parse(specs, [resp])
    obs, quar = [], []
    for sp in specs:
        accepted, rejected = pipeline_mod.validate(sp, parsed.get(sp.id) or [])
        obs += [observation_content(o) for o in accepted]
        quar += [quarantine_content(sp.id, x) for x in rejected]
    assert db.run_content(r.run_id) == RunContent.of(obs, quar)
    assert db.run_content(r.run_id) == RunContent.of(reversed(obs), reversed(quar))


def _pinned_or_live_base(db, tmp_path, channel):
    sp = spec("s1")
    sync_registry(db, [sp])
    store = RawStore(tmp_path / "raw")
    vals = {"s1": [["2024", "2.0"]]}
    rec = run_dataset(db, store, Recorded(body(vals), NOV01), [sp], None,
                      now=lambda: NOV13, input_origin="recorded")
    assert rec.state == "pending-verification"
    db.add_verification(rec.run_id, 1, 1, True, _ts(NOV13), sample_procedure="prumo-sample-v2",
                        sample_design={}, input_origin="recorded", verifier_channel=channel)
    assert db.transition_run_state(rec.run_id, "pending-verification", "verified")
    live = run_dataset(db, store, FakeSource(), [sp], FakeHttp(ok(body(vals, variant=1))),
                       now=lambda: NOV13 + timedelta(days=1))
    return rec, live


def test_pinned_bundle_verified_run_is_never_a_base(db, tmp_path):
    """Not audit-grade: a live fetch with the same values must be stored and verified live."""
    rec, live = _pinned_or_live_base(db, tmp_path, "pinned-bundle")
    assert (live.state, live.n_written) == ("pending-verification", 1)


def test_live_verified_recorded_run_is_a_base(db, tmp_path):
    rec, live = _pinned_or_live_base(db, tmp_path, "live")
    assert_content_shortcut(db, live, rec.run_id)


def test_base_superseded_by_another_dataset_is_not_a_base(env):
    """K1={s1} writes s1=A; K2={s1,s2} later writes s1=B (served: newer); K1 fetches A
    again. A short-circuit would leave K2's B served, so the run is stored in full."""
    db, specs, store, clock, _ = env

    def run(sps, series, variant=0):
        r = run_dataset(db, store, FakeSource(), sps, FakeHttp(ok(body(series, variant))),
                        clock)
        assert db.transition_run_state(r.run_id, "pending-verification", "verified")
        return r
    run(specs[:1], {"s1": [["2024", "1.0"]]})
    run(specs, {"s1": [["2024", "2.0"]], "s2": [["2024", "10"]]})
    assert served(db)[("s1", "2024")] == "2.0"
    r3 = run_dataset(db, store, FakeSource(), specs[:1],
                     FakeHttp(ok(body({"s1": [["2024", "1.0"]]}, variant=1))), clock)
    assert (r3.state, r3.n_written) == ("pending-verification", 1)
    assert db.transition_run_state(r3.run_id, "pending-verification", "verified")
    assert served(db)[("s1", "2024")] == "1.0"
    # once K1 holds the newest rows again, its next identical fetch short-circuits
    r4 = run_dataset(db, store, FakeSource(), specs[:1],
                     FakeHttp(ok(body({"s1": [["2024", "1.0"]]}, variant=2))), clock)
    assert_content_shortcut(db, r4, r3.run_id)

