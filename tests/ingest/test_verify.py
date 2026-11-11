"""Truth verification (spec 6b) against a real SQLite file, real RawStore, fake source/verifier."""
import hashlib
import importlib
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from ingest import verifiers
from ingest.db import open_db
from ingest.pipeline import run_dataset
from ingest.rawstore import RawIntegrityError, RawStore
from ingest.registry import sync_registry
from ingest.verifiers import BlindItem, ItemResult, get_verifier, register_verifier
from ingest.verify import (VerificationConflict, draw_sample, replay_item, run_with_refetch,
                           verify_run)
from tests.ingest.fake_verifier import FakeVerifier
from tests.ingest.fakes import FakeHttp, FakeSource, ok, payload, spec, truth_of

BASE = {"s1": [["2023", "1.5"], ["2024", "2.0"]], "s2": [["2024", "10"]]}


class Clock:
    def __init__(self):
        self.t = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        self.t += timedelta(seconds=1)
        return self.t


@pytest.fixture(autouse=True)
def empty_registry(monkeypatch):
    monkeypatch.setattr(verifiers, "_REGISTRY", {})


@pytest.fixture
def env(db, tmp_path):
    specs = [spec("s1"), spec("s2")]
    sync_registry(db, specs)
    store = RawStore(tmp_path / "raw")
    clock = Clock()

    def run(series=BASE):
        return run_dataset(db, store, FakeSource(), specs, FakeHttp(ok(payload(series))), clock)

    return db, specs, store, clock, run


def q(db, sql, *args):
    return db.conn.execute(sql, args).fetchall()


def keys(items):
    return [(i.series_id, i.period) for i in items]


# --- sampling ----------------------------------------------------------------------------------

def big(n_series=3, years=range(2000, 2025)):
    return {f"s{k}": [[str(y), f"{y}.{k}"] for y in years] for k in range(1, n_series + 1)}


@pytest.fixture
def big_env(db, tmp_path):
    specs = [spec("s1"), spec("s2"), spec("s3")]
    sync_registry(db, specs)
    r = run_dataset(db, RawStore(tmp_path / "raw"), FakeSource(), specs,
                    FakeHttp(ok(payload(big()))), Clock())
    assert r.state == "pending-verification" and r.n_written == 75
    return db, specs, r.run_id


def test_sample_always_includes_latest_period_of_each_series(big_env):
    db, specs, run_id = big_env
    for seed in range(20):
        items = draw_sample(db, run_id, seed, 5, specs=specs)
        assert len(items) == 5
        assert {("s1", "2024"), ("s2", "2024"), ("s3", "2024")} <= set(keys(items))
        assert len(set(keys(items))) == 5  # without replacement


def test_sample_is_reproducible_from_seed(big_env):
    db, specs, run_id = big_env
    a = draw_sample(db, run_id, 42, 10, specs=specs)
    assert a == draw_sample(db, run_id, 42, 10, specs=specs)
    assert keys(a) == sorted(keys(a))  # deterministic order
    assert {tuple(keys(draw_sample(db, run_id, s, 10, specs=specs))) for s in range(10)} != {
        tuple(keys(a))}  # the seed actually drives the random part
    item = next(i for i in a if i.series_id == "s2" and i.period == "2024")
    assert (item.expected_text, item.expected_unit, item.expected_flag) == ("2024.2", "EUR", None)
    assert item.spec == specs[1]


def test_sample_covers_every_series_even_when_size_smaller(big_env):
    db, specs, run_id = big_env
    items = draw_sample(db, run_id, 7, 1, specs=specs)
    assert keys(items) == [("s1", "2024"), ("s2", "2024"), ("s3", "2024")]


def test_sample_takes_every_observation_when_size_exceeds_run(env):
    db, specs, _, _, run = env
    r = run()
    assert keys(draw_sample(db, r.run_id, 1, 50, specs=specs)) == [
        ("s1", "2023"), ("s1", "2024"), ("s2", "2024")]


def test_sample_rejects_unknown_series_and_bad_size(env):
    db, specs, _, _, run = env
    r = run()
    with pytest.raises(ValueError):
        draw_sample(db, r.run_id, 1, 5, specs=specs[:1])
    with pytest.raises(ValueError):
        draw_sample(db, r.run_id, 1, 0, specs=specs)


# --- verify_run --------------------------------------------------------------------------------

TRUTH = truth_of(BASE)
SERVED_BASE = {("s1", "2023"): "1.5", ("s1", "2024"): "2.0", ("s2", "2024"): "10"}


def served(db):
    return dict(((s, p), v) for s, p, v in
                q(db, "SELECT series_id, period, value_text FROM served_observation"))


def items_of(db, run_id):
    return q(db, "SELECT i.series_id, i.period, i.expected_text, i.observed_text, i.evidence_url, "
                 "i.match, i.note, i.id FROM verification_item i JOIN verification v "
                 "ON v.id = i.verification_id WHERE v.dataset_run_id = ? ORDER BY i.id", run_id)


def failure_events(db):
    return [json.loads(d) for (d,) in
            q(db, "SELECT detail_json FROM event WHERE kind = 'verification_failure' ORDER BY id")]


def vrun(env, verifier, series=BASE, seed=1, size=50):
    db, specs, store, clock, run = env
    r = run(series)
    assert r.state == "pending-verification"
    return r.run_id, verify_run(db, r.run_id, verifier, None, seed=seed, size=size, specs=specs,
                                store=store, now=clock)


class ScriptedVerifier:
    source_name = "fake"

    def __init__(self, results):
        self.results = results

    def check(self, items, http):
        return self.results(items)


def echo(items, truth=TRUTH, **kw):
    return [ItemResult(i.series_id, i.period, truth.get((i.series_id, i.period)), "u", **kw)
            for i in items]


def test_all_match_marks_verified(env):
    db = env[0]
    run_id, passed = vrun(env, FakeVerifier(TRUTH), seed=123)
    assert passed is True
    assert db.run_state(run_id) == "verified"
    assert q(db, "SELECT dataset_run_id, seed, sample_size, passed FROM verification") == [
        (run_id, 123, 3, 1)]
    assert [r[5] for r in items_of(db, run_id)] == [1, 1, 1]
    assert served(db) == SERVED_BASE
    assert failure_events(db) == []


def test_single_mismatch_marks_failed_and_not_served(env):
    db = env[0]
    run_id, passed = vrun(env, FakeVerifier({**TRUTH, ("s1", "2023"): "1.6"}), seed=9)
    assert passed is False
    assert db.run_state(run_id) == "failed-verification"
    assert served(db) == {}
    assert q(db, "SELECT seed, sample_size, passed FROM verification") == [(9, 3, 0)]
    assert [(r[0], r[1], r[2], r[3], r[5]) for r in items_of(db, run_id)] == [
        ("s1", "2023", "1.5", "1.6", 0), ("s1", "2024", "2.0", "2.0", 1),
        ("s2", "2024", "10", "10", 1)]
    assert failure_events(db) == [{"run_id": run_id, "seed": 9, "n_items": 3, "n_mismatch": 1,
                                   "first_mismatches": [{"series_id": "s1", "period": "2023",
                                                         "expected": "1.5", "observed": "1.6"}]}]


def test_none_observed_counts_as_mismatch(env):
    db = env[0]
    truth = {k: v for k, v in TRUTH.items() if k != ("s2", "2024")}
    run_id, passed = vrun(env, FakeVerifier(truth))
    assert passed is False and db.run_state(run_id) == "failed-verification"
    row = [r for r in items_of(db, run_id) if r[0] == "s2"][0]
    assert (row[3], row[5]) == (None, 0)


def test_verification_items_store_evidence_url(env):
    db = env[0]
    run_id, _ = vrun(env, FakeVerifier(TRUTH))
    assert [r[4] for r in items_of(db, run_id)] == [
        "http://verify.fake/s1/2023", "http://verify.fake/s1/2024", "http://verify.fake/s2/2024"]
    assert q(db, "SELECT observed_decimal, observed_unit, observed_flag FROM verification_item "
                 "LIMIT 1") == [(".", None, None)]


@pytest.mark.parametrize("expected,observed,decimal,match", [
    ("1.10", "1,1", ",", True),
    ("1.10", "1.1", ".", True),
    ("1 234.5", "1.234,50", ",", True),
    ("1.10", "1.1000001", ".", False),
    ("0.30000000000000004", "0.3", ".", False),
    ("1.10", "1,1", ".", False),  # "1,1" is not a number when the decimal is "."
    ("1.10", "n/d", ".", False),
])
def test_decimal_comparison_is_exact_not_float(env, expected, observed, decimal, match):
    db = env[0]
    series = {"s1": [["2024", expected]], "s2": [["2024", "10"]]}
    truth = {("s1", "2024"): observed, ("s2", "2024"): "10"}
    run_id, passed = vrun(env, FakeVerifier(truth, decimal=decimal), series=series)
    assert passed is match
    assert db.run_state(run_id) == ("verified" if match else "failed-verification")


@pytest.mark.parametrize("kw,match", [
    ({"unit": "EUR"}, True), ({"unit": " EUR "}, True), ({"unit": "USD"}, False),
    ({"flag": "p"}, False), ({"flag": ""}, True),
])
def test_unit_or_flag_mismatch_fails(env, kw, match):
    db = env[0]
    run_id, passed = vrun(env, FakeVerifier(TRUTH, **kw))
    assert passed is match
    if not match:
        assert all(r[6] for r in items_of(db, run_id))  # each item says why


def test_verifier_exception_is_failure_not_pass(env):
    db = env[0]
    run_id, passed = vrun(env, FakeVerifier(raises=RuntimeError("site down")))
    assert passed is False and db.run_state(run_id) == "failed-verification"
    rows = items_of(db, run_id)
    assert len(rows) == 3 and all(r[5] == 0 and "site down" in r[6] for r in rows)
    assert failure_events(db)[0]["n_mismatch"] == 3
    assert served(db) == {}


def test_wrong_result_count_is_failure(env):
    db = env[0]
    for results, n in ((lambda items: echo(items)[:-1], 2), (lambda items: echo(items) * 2, 6)):
        run_id, passed = vrun(env, ScriptedVerifier(results))
        assert passed is False and db.run_state(run_id) == "failed-verification"
        assert all(r[5] == 0 and f"{n} results for 3 items" in r[6] for r in items_of(db, run_id))


def test_out_of_order_result_is_failure(env):
    db = env[0]
    run_id, passed = vrun(env, ScriptedVerifier(lambda items: echo(list(reversed(items)))))
    assert passed is False and db.run_state(run_id) == "failed-verification"
    notes = [r[6] for r in items_of(db, run_id)]
    assert "result is for s2/2024" in notes[0]


def test_duplicate_key_result_is_failure(env):
    db = env[0]
    run_id, passed = vrun(env, ScriptedVerifier(lambda items: echo([items[0]] * len(items))))
    assert passed is False
    assert [r[5] for r in items_of(db, run_id)] == [1, 0, 0]


def test_parser_swapped_periods_with_reordered_verifier_fails(env):
    """Probe 2: the parser swapped two periods of s1 (stored 2023=2.0, 2024=1.5); a verifier
    that iterates its table by period DESC returns the right values in the wrong order."""
    db = env[0]
    swapped = {"s1": [["2023", "2.0"], ["2024", "1.5"]], "s2": [["2024", "10"]]}

    def desc(items):
        s1 = [i for i in items if i.series_id == "s1"]
        reordered = [s1[len(s1) - 1 - s1.index(i)] if i.series_id == "s1" else i for i in items]
        return echo(reordered)

    run_id, passed = vrun(env, ScriptedVerifier(desc), series=swapped)
    assert passed is False and db.run_state(run_id) == "failed-verification"
    assert served(db) == {}
    # the same swap with an honest, ordered verifier fails on value
    run_id, passed = vrun(env, ScriptedVerifier(echo), series=swapped)
    assert passed is False
    assert [r[6] for r in items_of(db, run_id)][:2] == ["value differs", "value differs"]


def test_verifier_gets_blinded_items(env):
    db = env[0]
    v = FakeVerifier(TRUTH)
    vrun(env, v)
    item = v.calls[0][0]
    assert type(item) is BlindItem
    for attr in ("expected_text", "expected_unit", "expected_flag"):
        with pytest.raises(AttributeError):
            getattr(item, attr)
    with pytest.raises(AttributeError):
        item.expected_text = "1"  # frozen: cannot be smuggled in either

    peek = ScriptedVerifier(lambda items: [ItemResult(i.series_id, i.period, i.expected_text, "u")
                                           for i in items])
    run_id, passed = vrun(env, peek, series={"s1": [["2024", "3"]], "s2": [["2024", "4"]]})
    assert passed is False and "AttributeError" in items_of(db, run_id)[0][6]


def test_echoing_what_it_is_given_cannot_pass(env):
    db = env[0]
    parrot = ScriptedVerifier(lambda items: [
        ItemResult(i.series_id, i.period, getattr(i, "expected_text", None), "u") for i in items])
    run_id, passed = vrun(env, parrot, series={"s1": [["2024", "999"]], "s2": [["2024", "1"]]})
    assert passed is False and served(db) == {}


def test_refuses_to_verify_non_pending_run(env):
    db, specs, store, clock, run = env
    r = run()
    verify_run(db, r.run_id, FakeVerifier(TRUTH), None, specs=specs, store=store, now=clock)
    for state in ("verified", "failed-verification", "failed-validation", "running"):
        db.set_run_state(r.run_id, state)
        with pytest.raises(ValueError):
            verify_run(db, r.run_id, FakeVerifier(TRUTH), None, specs=specs, now=clock)
    assert q(db, "SELECT count(*) FROM verification") == [(1,)]


def test_random_seed_is_stored_when_not_given(env):
    db, specs, store, clock, run = env
    r = run()
    assert verify_run(db, r.run_id, FakeVerifier(TRUTH), None, specs=specs, now=clock)
    (seed,), = q(db, "SELECT seed FROM verification")
    assert keys(draw_sample(db, r.run_id, seed, 50, specs=specs)) == [
        tuple(x[:2]) for x in items_of(db, r.run_id)]


def test_malformed_result_fields_are_failure_not_crash(env):
    db = env[0]
    sloppy = ScriptedVerifier(lambda items: [
        ItemResult(i.series_id, i.period, float(TRUTH[(i.series_id, i.period)]), 42,
                   observed_unit=7) for i in items])
    run_id, passed = vrun(env, sloppy)
    assert passed is False and db.run_state(run_id) == "failed-verification"
    rows = items_of(db, run_id)
    assert all(r[3] is None and r[4] is None and r[5] == 0 and r[6] for r in rows)
    for bad in (lambda items: [None] * len(items),
                lambda items: [{"observed_text": "1"}] * len(items),
                lambda items: echo(items, evidence="not bytes")):
        run_id, passed = vrun(env, ScriptedVerifier(bad))
        assert passed is False and all(r[5] == 0 and r[6] for r in items_of(db, run_id))


class LyingStr(str):
    def __eq__(self, other):
        return True

    __hash__ = str.__hash__


@pytest.mark.parametrize("field", ["observed_text", "observed_unit", "series_id"])
def test_str_subclass_fields_are_failure(env, field):
    db = env[0]

    def lie(items):
        out = []
        for r in echo(items):
            kw = {field: LyingStr(getattr(r, field) or "x")}
            out.append(ItemResult(**{**r.__dict__, **kw}))
        return out

    run_id, passed = vrun(env, ScriptedVerifier(lie))
    assert passed is False
    rows = items_of(db, run_id)
    assert all(r[5] == 0 and f"exact str: {field}: LyingStr" in r[6] for r in rows)


def test_replay_refuses_legacy_item(env):
    db, _, store, _, _ = env
    run_id, _ = vrun(env, FakeVerifier(TRUTH))
    (vid,), = q(db, "SELECT id FROM verification")
    cur = db.conn.execute(
        "INSERT INTO verification_item(verification_id, series_id, period, expected_text, "
        "observed_text, evidence_url, match) VALUES (?, 's1', '2024', '2.0', '2.0', 'u', 1)", (vid,))
    with pytest.raises(ValueError, match="legacy item"):
        replay_item(db, store, cur.lastrowid)


# --- I1: concurrent verification (compare-and-set) ---------------------------------------------

@pytest.mark.parametrize("inner_truth,final", [({}, "failed-verification"),
                                                (TRUTH, "verified")])
def test_concurrent_verify_loser_is_rolled_back(env, tmp_path, inner_truth, final):
    """Probe 8: while worker 1's verifier is checking, worker 2 (another connection to the same
    file) verifies the same run to completion. Worker 1 must not overwrite that outcome."""
    db, specs, store, clock, run = env
    r = run()
    db2 = open_db(tmp_path / "prumo.db")
    try:
        def inner(items):
            verify_run(db2, r.run_id, FakeVerifier(inner_truth), None, specs=specs,
                       store=store, now=clock)
            outer_truth = TRUTH if inner_truth == {} else {}
            return echo(items, outer_truth)

        with pytest.raises(VerificationConflict):
            verify_run(db, r.run_id, ScriptedVerifier(inner), None, specs=specs, store=store,
                       now=clock)
    finally:
        db2.close()
    assert db.run_state(r.run_id) == final
    assert q(db, "SELECT passed FROM verification") == [(int(final == "verified"),)]
    assert q(db, "SELECT count(*) FROM verification_item") == [(3,)]
    n_fail = 0 if final == "verified" else 1
    assert len(failure_events(db)) == n_fail
    assert served(db) == (SERVED_BASE if final == "verified" else {})


# --- I6: evidence and replay -------------------------------------------------------------------

def test_evidence_bytes_saved_and_items_replayable(env):
    db, specs, store, clock, _ = env
    truth = {**TRUTH, ("s1", "2023"): "1,6"}
    run_id, passed = vrun(env, FakeVerifier(truth, evidence=True))
    assert passed is False
    rows = q(db, "SELECT id, series_id, period, observed_text, expected_decimal, expected_unit, "
                 "expected_flag, evidence_sha256, match FROM verification_item ORDER BY id")
    for item_id, sid, period, observed, dec, unit, flag, sha, match in rows:
        body = f"{sid},{period},{observed}".encode()
        assert sha == hashlib.sha256(body).hexdigest()
        assert (store.root / "verify-fake" / sha[:2] / sha).read_bytes() == body
        assert (dec, unit, flag) == (".", "EUR", None)
        assert replay_item(db, store, item_id) is bool(match)
    assert [r[-1] for r in rows] == [0, 1, 1]


def test_replay_needs_no_registry_and_reproduces_every_outcome(env):
    db = env[0]
    store = env[2]
    outcomes = []
    # every verifier but the last fails, so no run is short-circuited by an identical payload
    for v in (FakeVerifier({}), FakeVerifier(TRUTH, unit="USD"),
              FakeVerifier(raises=RuntimeError("x")),
              ScriptedVerifier(lambda items: echo(list(reversed(items)))),
              FakeVerifier({("s1", "2023"): "1,5", ("s1", "2024"): "2,1", ("s2", "2024"): "10"},
                           decimal=","),
              FakeVerifier(TRUTH)):
        run_id, _ = vrun(env, v)
        outcomes += [(r[7], bool(r[5])) for r in items_of(db, run_id)]
    assert {m for _, m in outcomes} == {True, False}
    assert all(replay_item(db, store, item_id) is match for item_id, match in outcomes)


def test_replay_detects_tampered_evidence(env):
    db, _, store, _, _ = env
    run_id, _ = vrun(env, FakeVerifier(TRUTH, evidence=True))
    item_id = items_of(db, run_id)[0][7]
    (sha,), = q(db, "SELECT evidence_sha256 FROM verification_item WHERE id = ?", item_id)
    (store.root / "verify-fake" / sha[:2] / sha).write_bytes(b"forged")
    with pytest.raises(RawIntegrityError):
        replay_item(db, store, item_id)


def test_evidence_without_store_is_refused(env):
    db, specs, _, clock, run = env
    r = run()
    with pytest.raises(ValueError, match="store"):
        verify_run(db, r.run_id, FakeVerifier(TRUTH, evidence=True), None, specs=specs,
                   now=clock)


# --- run_with_refetch --------------------------------------------------------------------------

def refetch(env, verifier, *pages, max_attempts=3, size=50):
    db, specs, store, clock, _ = env
    if verifiers._REGISTRY.get(verifier.source_name) is not verifier:
        register_verifier(verifier)
    http = FakeHttp(*[ok(payload(p)) for p in pages])
    return run_with_refetch(db, store, FakeSource(), verifier, specs, http,
                            max_attempts=max_attempts, size=size, now=clock)


def test_refetch_uses_new_seed_each_attempt(env):
    db = env[0]
    bad = {**TRUTH, ("s2", "2024"): "11"}
    v = FakeVerifier(bad, bad, TRUTH)
    r = refetch(env, v, BASE, BASE, BASE)
    assert r.state == "verified" and db.run_state(r.run_id) == "verified"
    rows = q(db, "SELECT dataset_run_id, seed, passed FROM verification ORDER BY id")
    assert [p for _, _, p in rows] == [0, 0, 1]
    assert len({s for _, s, _ in rows}) == 3  # fresh seed every attempt
    assert len({run for run, _, _ in rows}) == 3  # each attempt is a new run (re-fetched)
    assert [x[0] for x in q(db, "SELECT kind FROM event WHERE kind IN "
                                "('verification_failure','refetch') ORDER BY id")] == [
        "verification_failure", "refetch", "verification_failure", "refetch"]
    assert served(db) == SERVED_BASE


def test_gives_up_after_max_attempts_and_stays_unserved(env):
    db = env[0]
    v = FakeVerifier({})
    r = refetch(env, v, BASE, BASE, max_attempts=2)
    assert r.state == "failed-verification" and db.run_state(r.run_id) == "failed-verification"
    assert len(v.calls) == 2
    assert q(db, "SELECT count(*), sum(passed) FROM verification") == [(2, 0)]
    assert q(db, "SELECT count(*) FROM event WHERE kind = 'refetch'") == [(1,)]
    assert q(db, "SELECT state FROM dataset_run ORDER BY id") == [
        ("failed-verification",), ("failed-verification",)]
    assert served(db) == {}


def test_previously_verified_data_still_served_after_failed_verification(env):
    db = env[0]
    v = FakeVerifier(TRUTH)
    assert refetch(env, v, BASE).state == "verified"
    revised = {"s1": [["2023", "1.5"], ["2024", "2.5"]], "s2": [["2024", "10"]]}
    r = refetch(env, v, revised, max_attempts=1)  # verifier still sees 2.0
    assert r.state == "failed-verification"
    assert served(db) == SERVED_BASE


def test_short_circuit_run_gets_no_verification_row(env):
    db = env[0]
    v = FakeVerifier(TRUTH)
    first = refetch(env, v, BASE)
    second = refetch(env, v, BASE)
    assert (first.state, second.state) == ("verified", "verified")
    assert second.n_written == 0 and len(v.calls) == 1
    assert q(db, "SELECT dataset_run_id FROM verification") == [(first.run_id,)]
    assert served(db) == SERVED_BASE


def test_failed_fetch_is_returned_without_verification(env):
    db, specs, store, clock, _ = env
    v = FakeVerifier(TRUTH)
    register_verifier(v)
    r = run_with_refetch(db, store, FakeSource(), v, specs, FakeHttp(ok(b"", status=500)),
                         now=clock)
    assert r.state == "failed-fetch" and v.calls == []
    assert q(db, "SELECT count(*) FROM verification") == [(0,)]


def test_refetch_requires_the_registered_verifier(env):
    db, specs, store, clock, _ = env
    v = FakeVerifier(TRUTH)
    with pytest.raises(ValueError, match="registered"):  # not registered at all
        run_with_refetch(db, store, FakeSource(), v, specs, FakeHttp(), now=clock)
    register_verifier(FakeVerifier(TRUTH))
    with pytest.raises(ValueError, match="registered"):  # another instance is registered
        run_with_refetch(db, store, FakeSource(), v, specs, FakeHttp(), now=clock)
    assert q(db, "SELECT count(*) FROM dataset_run") == [(0,)]


# --- registration (Ruling Q) -------------------------------------------------------------------

@pytest.fixture
def fake_ingest(tmp_path, monkeypatch):
    """A throwaway `ingest` source tree (files only, never imported) for the transitive check."""
    root = tmp_path / "ingest_tree"
    monkeypatch.setattr(verifiers, "_INGEST_ROOT", root)

    def write(files: dict[str, str]):
        for rel, text in {"__init__.py": "", "sources/__init__.py": "", **files}.items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(text)
    return write


@pytest.fixture
def make_verifier(tmp_path, monkeypatch):
    """Write a verifier module with `code` to tmp_path, import it, return an instance."""
    mods = tmp_path / "mods"
    mods.mkdir()
    monkeypatch.syspath_prepend(str(mods))

    def make(code: str, source_name: str = "acme"):
        name = f"tmp_verifier_{uuid.uuid4().hex}"  # unique: sys.modules outlives tmp_path
        (mods / f"{name}.py").write_text(
            # the code sits in a function body: never executed, but visible to the AST check
            "def _unused():\n" + "".join(f"    {line}\n" for line in code.splitlines() or ["pass"])
            + f"\n\nclass V:\n    source_name = {source_name!r}\n\n"
              f"    def check(self, items, http):\n        return []\n")
        importlib.invalidate_caches()
        return importlib.import_module(name).V()
    return make


@pytest.mark.parametrize("code", [
    "import ingest.sources.acme",
    "from ingest.sources.acme import parse",
    "from ingest.sources import acme",
    "from ingest.sources import eurostat",
    "import ingest.sources.eurostat as e",
    "from ingest.sources import validate_helper",
    "import importlib\nP = importlib.import_module('ingest.sources.acme')",
    "from importlib import import_module",
    "P = __import__('ingest.sources.acme')",
    "from ingest import sources\nP = sources.acme",
    "from ingest import sources as s",
    "import ingest.sources\nP = ingest.sources.acme",
    "import ingest\nP = ingest.sources.acme",
    "exec('from ingest.sources.acme import parse')",
    "eval('1')",
    "import sys\nP = sys.modules['ingest.sources.acme']",
    "from sys import modules",
    "import ACME",
    "import acme",
    "from vendor.Acme import parse",
    "from vendor import acme",
])
def test_verifier_importing_parser_is_rejected(make_verifier, code):
    v = make_verifier(code)
    with pytest.raises(ValueError, match="independent"):
        register_verifier(v)
    with pytest.raises(KeyError):
        get_verifier("acme")


@pytest.mark.parametrize("code", [
    "",
    "from ingest.sources import RawResponse, Source",
    "from ingest.http import Http\nfrom ingest.models import parse_decimal\nimport json",
    "from ingest.verifiers import ItemResult, BlindItem",
    "from ingest.rawstore import RawStore",
    "from ingest.http import HttpResult\nfrom ingest.models import parse_number\n"
    "from ingest.rawstore import RawStore\nfrom ingest.sources import Source, RawResponse\n"
    "from ingest.verifiers import ItemResult, BlindItem",
    "import re\nP = re.compile('x')\nwith open('f') as f:\n    pass",
])
def test_independent_verifier_is_registered(make_verifier, code):
    v = make_verifier(code)
    register_verifier(v)
    assert get_verifier("acme") is v


def test_shared_helper_with_parser_is_rejected(make_verifier, fake_ingest):
    fake_ingest({"sources/acme.py": "from ingest import sdmx\nfrom ingest.models import x\n",
                 "sdmx.py": "import json\n",
                 "wrapper.py": "from . import sdmx\n"})
    for code in ("from ingest.sdmx import f", "from ingest import sdmx",
                 "from ingest.wrapper import f"):
        with pytest.raises(ValueError, match="shares code.*ingest.sdmx"):
            register_verifier(make_verifier(code))


def test_only_allow_listed_shared_modules_is_accepted(make_verifier, fake_ingest):
    fake_ingest({"sources/acme.py": "from ingest.models import x\nfrom ingest import http\n"
                                    "from ingest.sources import RawResponse\nimport ingest.sdmx\n",
                 "sdmx.py": "", "own_helper.py": "from ingest.models import y\n"})
    v = make_verifier("from ingest.models import x\nfrom ingest.http import Http\n"
                      "from ingest.rawstore import RawStore\nfrom ingest.own_helper import y")
    register_verifier(v)
    assert get_verifier("acme") is v


@pytest.mark.parametrize("code,rule", [
    # plain `import ingest...` binds the name `ingest` -> ingest.sources.<x> by attribute
    ("import ingest.http\nP = ingest.sources.acme.parse_rows", "plain import binds 'ingest'"),
    ("import ingest.models\nP = ingest.sources.acme", "plain import binds 'ingest'"),
    ("import ingest.rawstore", "plain import binds 'ingest'"),
    ("import ingest.http as h", "plain import binds 'ingest'"),
    ("import ingest", "plain import binds 'ingest'"),
    ("from ingest.verifiers import ingest as i", "name binds 'ingest'"),
    # defence in depth: attribute chains, even without the import line
    ("P = ingest.sources.acme.parse_rows", "attribute access to collector: ingest.sources.acme"),
    ("from ingest.verifiers import ingest as i\nP = i.sources", "attribute access to collector"),
    # dynamic import / introspection, any alias form
    ("import sys as s\nP = s.modules['ingest.sources.acme']", "dynamic import/DB access"),
    ("from sys import modules", "dynamic import/DB access"),
    ("from ingest.verifiers import sys", "dynamic import/DB access"),
    ("import builtins\nP = builtins.__import__('ingest.sources.acme')", "dynamic import/DB access"),
    ("from builtins import __import__ as imp\nP = imp('x')", "dynamic import/DB access"),
    ("import runpy\nruns = runpy.run_module", "dynamic import/DB access"),
    ("import pkgutil\nP = pkgutil.resolve_name('ingest.sources.acme:parse_rows')",
     "dynamic import/DB access"),
    ("import importlib", "dynamic import/DB access"),
    ("from importlib import import_module", "dynamic import/DB access"),
    ("P = __import__('ingest.sources.acme')", "dynamic code: __import__"),
    ("x = object().__import__", "dynamic code: .__import__"),
    ("P = vars(ingest)['sources']", "dynamic code: vars"),
    ("P = globals()['__builtins__']['__imp' + 'ort__']", "dynamic code: globals"),
    ("P = locals()", "dynamic code: locals"),
    ("P = __builtins__", "dynamic code: __builtins__"),
    ("exec('import ingest.sources.acme')", "dynamic code: exec"),
    ("eval('1')", "dynamic code: eval"),
    ("P = compile('1', 'f', 'eval')", "dynamic code: compile"),
    # reading expected values from the database
    ("from ingest.db import open_db", "dynamic import/DB access: from ingest.db"),
    ("from ingest import db", "dynamic import/DB access: from ingest import db"),
    ("import sqlite3", "dynamic import/DB access: import sqlite3"),
    # collector imports and source-named modules
    ("from ingest.sources import acme", "collector import"),
    ("from ingest.sources.acme import parse_rows", "collector import"),
    ("from ingest import sources", "collector import"),
    ("import ACME", "source-named import"),
])
def test_registration_bypasses_are_rejected(make_verifier, code, rule):
    with pytest.raises(ValueError, match="independent") as e:
        register_verifier(make_verifier(code))
    assert rule in str(e.value)
    with pytest.raises(KeyError):
        get_verifier("acme")


def test_duplicate_registration_is_rejected(make_verifier):
    register_verifier(make_verifier(""))
    with pytest.raises(ValueError, match="already registered"):
        register_verifier(make_verifier(""))


def test_fake_verifier_module_passes_the_rule():
    register_verifier(FakeVerifier())
    assert get_verifier("fake").source_name == "fake"
