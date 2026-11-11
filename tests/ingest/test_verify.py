"""Truth verification (spec 6b) against a real SQLite file, real RawStore, fake source/verifier."""
from datetime import datetime, timedelta, timezone

import pytest

from ingest.pipeline import run_dataset
from ingest.rawstore import RawStore
from ingest.registry import sync_registry
from ingest.verify import draw_sample
from tests.ingest.fakes import FakeHttp, FakeSource, ok, payload, spec

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
