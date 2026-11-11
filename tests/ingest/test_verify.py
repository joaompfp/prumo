"""Truth verification (spec 6b) against a real SQLite file, real RawStore, fake source/verifier."""
import json
from datetime import datetime, timedelta, timezone

import pytest

from ingest.pipeline import run_dataset
from ingest.rawstore import RawStore
from ingest.registry import sync_registry
from ingest.verifiers import ItemResult
from ingest.verify import draw_sample, run_with_refetch, verify_run
from tests.ingest.fakes import FakeHttp, FakeSource, FakeVerifier, ok, payload, spec, truth_of

BASE = {"s1": [["2023", "1.5"], ["2024", "2.0"]], "s2": [["2024", "10"]]}


class Clock:
    def __init__(self):
        self.t = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        self.t += timedelta(seconds=1)
        return self.t


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
                 "i.match, i.note FROM verification_item i JOIN verification v "
                 "ON v.id = i.verification_id WHERE v.dataset_run_id = ? ORDER BY i.id", run_id)


def failure_events(db):
    return [json.loads(d) for (d,) in
            q(db, "SELECT detail_json FROM event WHERE kind = 'verification_failure' ORDER BY id")]


def vrun(env, verifier, series=BASE, seed=1, size=50):
    db, specs, _, clock, run = env
    r = run(series)
    assert r.state == "pending-verification"
    return r.run_id, verify_run(db, r.run_id, verifier, None, seed=seed, size=size, specs=specs,
                                now=clock)


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


class ScriptedVerifier:
    source_name = "fake"

    def __init__(self, results):
        self.results = results

    def check(self, items, http):
        return self.results(items)


def test_wrong_result_count_is_failure(env):
    db = env[0]
    short = ScriptedVerifier(lambda items: [ItemResult(TRUTH[(i.series_id, i.period)], "u")
                                            for i in items[:-1]])
    run_id, passed = vrun(env, short)
    assert passed is False and db.run_state(run_id) == "failed-verification"
    assert all(r[5] == 0 and "2 results for 3 items" in r[6] for r in items_of(db, run_id))


def test_out_of_order_result_is_failure(env):
    db = env[0]
    swapped = ScriptedVerifier(lambda items: [
        ItemResult(TRUTH[(i.series_id, i.period)], "u", series_id=i.series_id, period=i.period)
        for i in reversed(items)])
    run_id, passed = vrun(env, swapped)
    assert passed is False and db.run_state(run_id) == "failed-verification"
    notes = [r[6] for r in items_of(db, run_id)]
    assert "result is for s2/2024" in notes[0]


def test_refuses_to_verify_non_pending_run(env):
    db, specs, _, clock, run = env
    r = run()
    verify_run(db, r.run_id, FakeVerifier(TRUTH), None, specs=specs, now=clock)
    for state in ("verified", "failed-verification", "failed-validation", "running"):
        db.set_run_state(r.run_id, state)
        with pytest.raises(ValueError):
            verify_run(db, r.run_id, FakeVerifier(TRUTH), None, specs=specs, now=clock)
    assert q(db, "SELECT count(*) FROM verification") == [(1,)]


def test_random_seed_is_stored_when_not_given(env):
    db, specs, _, clock, run = env
    r = run()
    assert verify_run(db, r.run_id, FakeVerifier(TRUTH), None, specs=specs, now=clock)
    (seed,), = q(db, "SELECT seed FROM verification")
    assert keys(draw_sample(db, r.run_id, seed, 50, specs=specs)) == [
        tuple(x[:2]) for x in items_of(db, r.run_id)]


# --- run_with_refetch --------------------------------------------------------------------------

def refetch(env, verifier, *pages, max_attempts=3, size=50):
    db, specs, store, clock, _ = env
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
    assert refetch(env, FakeVerifier(TRUTH), BASE).state == "verified"
    revised = {"s1": [["2023", "1.5"], ["2024", "2.5"]], "s2": [["2024", "10"]]}
    r = refetch(env, FakeVerifier(TRUTH), revised, max_attempts=1)  # verifier still sees 2.0
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
    r = run_with_refetch(db, store, FakeSource(), v, specs, FakeHttp(ok(b"", status=500)),
                         now=clock)
    assert r.state == "failed-fetch" and v.calls == []
    assert q(db, "SELECT count(*) FROM verification") == [(0,)]


def test_malformed_result_fields_are_failure_not_crash(env):
    db = env[0]
    sloppy = ScriptedVerifier(lambda items: [
        ItemResult(float(TRUTH[(i.series_id, i.period)]), 42, observed_unit=7,
                   series_id=i.series_id, period=i.period) for i in items])
    run_id, passed = vrun(env, sloppy)
    assert passed is False and db.run_state(run_id) == "failed-verification"
    rows = items_of(db, run_id)
    assert all(r[3] is None and r[4] is None and r[5] == 0 and r[6] for r in rows)


# --- registration ------------------------------------------------------------------------------

@pytest.fixture
def make_verifier(tmp_path, monkeypatch):
    """Write a verifier module with `imports` to tmp_path, import it, return an instance."""
    import importlib
    import uuid

    from ingest import verifiers
    monkeypatch.setattr(verifiers, "_REGISTRY", {})
    monkeypatch.syspath_prepend(str(tmp_path))

    def make(imports: str, source_name: str = "acme"):
        name = f"tmp_verifier_{uuid.uuid4().hex}"  # unique: sys.modules outlives tmp_path
        (tmp_path / f"{name}.py").write_text(
            # imports sit in a function body: never executed, but visible to the AST check
            f"def _unused():\n" + "".join(f"    {line}\n" for line in imports.splitlines() or ["pass"])
            + f"\n\nclass V:\n    source_name = {source_name!r}\n\n"
              f"    def check(self, items, http):\n        return []\n")
        return importlib.import_module(name).V()
    return make


@pytest.mark.parametrize("imports", [
    "import ingest.sources.acme",
    "from ingest.sources.acme import parse",
    "from ingest.sources import acme",
    "from ingest.sources import eurostat",
    "import ingest.sources.eurostat as e",
    "import acme",
    "from vendor.acme import parse",
    "from vendor import acme",
])
def test_verifier_importing_parser_is_rejected(make_verifier, imports):
    from ingest.verifiers import get_verifier, register_verifier
    v = make_verifier(imports)
    with pytest.raises(ValueError, match="import"):
        register_verifier(v)
    with pytest.raises(KeyError):
        get_verifier("acme")


@pytest.mark.parametrize("imports", [
    "",
    "from ingest.sources import RawResponse",
    "import ingest.sources",
    "from ingest.http import Http\nfrom ingest.models import parse_decimal\nimport json",
    "from ingest.verifiers import ItemResult, SampleItem",
])
def test_independent_verifier_is_registered(make_verifier, imports):
    from ingest.verifiers import get_verifier, register_verifier
    v = make_verifier(imports)
    register_verifier(v)
    assert get_verifier("acme") is v


def test_duplicate_registration_is_rejected(make_verifier):
    from ingest.verifiers import register_verifier
    register_verifier(make_verifier(""))
    with pytest.raises(ValueError, match="already registered"):
        register_verifier(make_verifier(""))


def test_fake_verifier_module_passes_the_rule(monkeypatch):
    from ingest import verifiers
    monkeypatch.setattr(verifiers, "_REGISTRY", {})
    verifiers.register_verifier(FakeVerifier())
    assert verifiers.get_verifier("fake").source_name == "fake"
