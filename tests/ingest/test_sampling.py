"""Sample design v2 (Task 21, B-I1/B-I2/B-M5): pure, no DB, no network."""
from fractions import Fraction
from math import comb

import pytest

from ingest.sampling import (
    PROCEDURE,
    REASONS,
    SamplingPolicy,
    design_sample,
    discovery_size,
    rank,
)


def rows_of(n_series: int, n_periods: int) -> list[tuple[str, str]]:
    return [(f"s{k:03d}", str(2000 + p)) for k in range(n_series) for p in range(n_periods)]


def per_item(key):
    return key  # every observation is its own request (no free closure)


def reasons(design):
    out: dict[str, int] = {}
    for _, why in design.chosen:
        out[why] = out.get(why, 0) + 1
    return out


# --- discovery (zero-acceptance) sample size ------------------------------------------------

def _miss(n_pop, defects, n):
    """Exact hypergeometric P(no defective in a simple random sample of n)."""
    return Fraction(comb(n_pop - defects, n), comb(n_pop, n))


@pytest.mark.parametrize("n_pop", [1, 2, 10, 99, 100, 101, 1_000, 4_400, 50_000])
def test_discovery_size_is_the_smallest_n_with_miss_probability_at_most_alpha(n_pop):
    n = discovery_size(n_pop, tolerable_rate=Fraction(1, 100), confidence=Fraction(95, 100))
    defects = max(1, -(-n_pop // 100))
    assert _miss(n_pop, defects, n) <= Fraction(5, 100)
    if n > 0:
        assert _miss(n_pop, defects, n - 1) > Fraction(5, 100)
    assert n <= n_pop


def test_discovery_size_known_values():
    one_pct = dict(tolerable_rate=Fraction(1, 100), confidence=Fraction(95, 100))
    assert discovery_size(0, **one_pct) == 0
    assert discovery_size(50, **one_pct) == 48  # one defect in 50: nearly a census
    assert 250 < discovery_size(1_400, **one_pct) < 300
    assert 280 < discovery_size(100_000, **one_pct) <= 300  # tends to ln(.05)/ln(.99) = 298.1
    assert discovery_size(10_000, tolerable_rate=Fraction(1, 100),
                          confidence=Fraction(0)) == 0


# --- deterministic ranking (B-M5) -------------------------------------------------------------

def test_rank_is_a_documented_sha256_construction_not_python_random():
    import hashlib
    assert rank(42, "random", "s1", "2024") == hashlib.sha256(
        b"prumo-sample-v2\x1f42\x1frandom\x1fs1\x1f2024").hexdigest()


def test_design_is_reproducible_and_seed_driven():
    rows = rows_of(20, 30)
    a = design_sample(rows, seed=1, changed=set(), request_key=per_item)
    assert a == design_sample(rows, seed=1, changed=set(), request_key=per_item)
    others = {tuple(design_sample(rows, seed=s, changed=set(), request_key=per_item).chosen)
              for s in range(2, 8)}
    assert tuple(a.chosen) not in others
    assert a.procedure == PROCEDURE == "prumo-sample-v2"


# --- must-check sets (B-I1 / B-I2) ------------------------------------------------------------

def test_every_series_latest_is_checked_even_above_fifty_series():
    rows = rows_of(329, 30)  # the Eurostat group shape that used to get latest-only
    d = design_sample(rows, seed=3, changed=set(), request_key=per_item)
    chosen = {rows[i]: why for i, why in d.chosen}
    for k in range(329):
        assert chosen[(f"s{k:03d}", "2029")] == "latest"


def test_history_is_sampled_above_fifty_series_with_a_minimum_per_series():
    """The old design (size 50) drew ZERO history once a group had >= 50 series."""
    rows = rows_of(329, 30)
    d = design_sample(rows, seed=3, changed=set(), request_key=per_item)
    r = reasons(d)
    assert r["series-stratum"] == 329 * 2  # one older-half + one recent-half cell per series
    by_series: dict[str, set] = {}
    for i, why in d.chosen:
        if why == "series-stratum":
            by_series.setdefault(rows[i][0], set()).add(rows[i][1])
    for periods in by_series.values():
        olds = [p for p in periods if p < "2014"]  # history 2000..2028: halves split at 2014
        assert len(olds) == 1 and len(periods) == 2
    n_pool = 329 * 29
    assert r["random"] == discovery_size(n_pool, tolerable_rate=Fraction(1, 100),
                                         confidence=Fraction(95, 100))
    assert d.summary["n_pool"] == n_pool and d.summary["n_items"] == len(d.chosen)


def test_sample_size_grows_with_the_population():
    small = design_sample(rows_of(10, 10), seed=1, changed=set(), request_key=per_item)
    large = design_sample(rows_of(10, 1_000), seed=1, changed=set(), request_key=per_item)
    assert len(large.chosen) > len(small.chosen)


def test_series_with_little_history_takes_what_exists():
    rows = [("a", "2024"), ("b", "2023"), ("b", "2024")]
    d = design_sample(rows, seed=1, changed=set(), request_key=per_item)
    assert sorted(d.chosen) == [(0, "latest"), (1, "series-stratum"), (2, "latest")]


def test_changed_observations_are_must_check_up_to_the_cap():
    rows = rows_of(5, 200)
    changed = {rows[i] for i in range(0, 1000, 3)}  # 334 revised/new cells
    pol = SamplingPolicy(changed_cap=100)
    d = design_sample(rows, seed=9, changed=changed, request_key=per_item, policy=pol)
    picked = [rows[i] for i, why in d.chosen if why == "changed"]
    assert len(picked) == 100 and set(picked) <= changed
    assert d.summary["n_changed_total"] == len(changed - {rows[i] for i in range(199, 1000, 200)})
    assert d.summary["n_changed_checked"] == 100 and d.summary["policy"]["changed_cap"] == 100
    # under the cap every changed cell is checked
    d2 = design_sample(rows, seed=9, changed=set(list(changed)[:50]), request_key=per_item)
    assert sum(1 for _, why in d2.chosen if why == "changed") == len(
        set(list(changed)[:50]) - {rows[i] for i in range(199, 1000, 200)})


def test_changed_latest_is_reported_as_latest_and_unknown_keys_are_ignored():
    rows = [("a", "2023"), ("a", "2024")]
    d = design_sample(rows, seed=1, changed={("a", "2024"), ("zz", "1999")},
                      request_key=per_item)
    assert (1, "latest") in d.chosen and d.summary["n_changed_total"] == 0


# --- free closure: cells read from a response the sample already needs --------------------------

def test_cells_sharing_a_sampled_response_are_compared_for_free():
    rows = rows_of(60, 40)
    d = design_sample(rows, seed=2, changed=set(), request_key=lambda key: key[0])
    assert len(d.chosen) == len(rows)  # every series is fetched (latest) -> full history
    assert reasons(d)["same-response"] == len(rows) - sum(
        v for k, v in reasons(d).items() if k != "same-response")
    assert {why for _, why in d.chosen} <= set(REASONS)


def test_closure_never_adds_cells_of_unsampled_responses():
    rows = rows_of(2, 100)
    d = design_sample(rows, seed=5, changed=set(), request_key=lambda key: key,
                      policy=SamplingPolicy(confidence=Fraction(0), history_per_series=0))
    assert sorted(d.chosen) == [(99, "latest"), (199, "latest")]


def test_policy_validation():
    for bad in (dict(confidence=Fraction(1)), dict(tolerable_rate=Fraction(0)),
                dict(history_per_series=-1), dict(changed_cap=-1)):
        with pytest.raises(ValueError):
            SamplingPolicy(**bad)
