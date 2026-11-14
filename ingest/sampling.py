"""Verification sample design, procedure `prumo-sample-v2` (Task 21). Pure: no DB, no network.

Given the observations a run wrote (`rows`, (series_id, period) ordered by series then
period), the run's changed cells, a stored random `seed` and the verifier's `request_key`,
`design_sample` returns which rows are compared and WHY. Steps, in order (a row is chosen
once, with the reason of the first step that takes it):

1. latest          the latest period of every series (census of the newest data).
1b. previously-failed  every row whose (series, period) MISMATCHED in a failed verification
                   of the same dataset since its last verified run (Task 24, re-review 2
                   I1). A parser defect is deterministic: refetched bytes re-parse to the
                   same wrong cells, so without this step every retry (run_with_refetch
                   attempts, scheduler retries) would be a fresh independent draw and a
                   defect would eventually pass on a lucky one. Uncapped: the set is bounded
                   by the earlier samples' sizes.
2. changed         every row the run revised or newly added (revision / new_periods events),
                   at most `changed_cap`; above the cap the `changed_cap` lowest-ranked are
                   taken and the rest fall back into the pool of step 3.
3. series-stratum  per series, its remaining rows ("pool") are split by period into
                   `history_per_series` contiguous bands of near-equal size (k=2: older half
                   and recent half) and the lowest-ranked row of each non-empty band is taken.
4. random          a simple random sample without replacement, of size
                   n = discovery_size(|pool|, tolerable_rate, confidence), from the pool rows
                   step 3 left (the lowest-ranked n).
5. same-response   every other row whose `request_key` equals that of a chosen row: the
                   verifier reads it from a response it fetches anyway, so it is compared at
                   no extra HTTP cost (a census of every fetched response).

Ranking (replaces random.Random.sample, whose sequence CPython does not guarantee across
versions): rank = sha256("prumo-sample-v2" US seed US stratum US series_id US period) as
lowercase hex (US = the 0x1F unit separator); "lowest-ranked k" means the k smallest ranks.
With an unpredictable seed this is a uniform random permutation of each stratum, and anyone
can recompute it from the stored seed with any SHA-256 implementation.

Statistical statement (step 4): with D = max(1, ceil(tolerable_rate * |pool|)) defective
pool rows, a simple random sample of n misses all of them with the hypergeometric
probability prod_{i<n} (|pool|-D-i)/(|pool|-i); n is the smallest size that makes this at
most 1 - confidence (exact rational arithmetic). Steps 3 and 5 only add rows, and drawing
step 4 from the pool minus step 3's rows can only lower the miss probability (each factor
1 - D/(M-i) shrinks as M shrinks), so the bound holds for the whole design: if at least
`tolerable_rate` of the non-must rows were wrong, the verification would detect at least one
with probability >= `confidence`. Steps 1, 1b and 2 are a census of their rows.

Across attempts: once one attempt has detected a defective cell, step 1b re-checks that cell
in every later attempt of the dataset until a verification passes, so a deterministic defect
is detected with probability 1 from the second attempt on (a transient fetch glitch clears,
because the refetched cell then matches). The per-verification 95% bound above is therefore
also the bound on serving a dataset with a deterministic >= 1% history defect: retries can
no longer re-draw until a lucky sample misses it.
"""
import hashlib
import math
from collections.abc import Callable, Hashable
from dataclasses import asdict, dataclass, field
from fractions import Fraction

PROCEDURE = "prumo-sample-v2"
REASONS = ("latest", "previously-failed", "changed", "series-stratum", "random",
           "same-response")
_SEP = "\x1f"


@dataclass(frozen=True)
class SamplingPolicy:
    """The reviewed defaults: 95% confidence of catching a >= 1% error rate in the history
    pool, two history cells per series (older/recent half), at most 500 changed cells forced
    into the must-check set per run."""
    confidence: Fraction = Fraction(95, 100)
    tolerable_rate: Fraction = Fraction(1, 100)
    history_per_series: int = 2
    changed_cap: int = 500

    def __post_init__(self):
        if not 0 <= self.confidence < 1:
            raise ValueError(f"confidence must be in [0, 1), got {self.confidence}")
        if not 0 < self.tolerable_rate <= 1:
            raise ValueError(f"tolerable_rate must be in (0, 1], got {self.tolerable_rate}")
        if self.history_per_series < 0 or self.changed_cap < 0:
            raise ValueError("history_per_series and changed_cap must be >= 0")

    def as_dict(self) -> dict:
        d = asdict(self)
        return {**d, "confidence": str(self.confidence),
                "tolerable_rate": str(self.tolerable_rate)}


DEFAULT_POLICY = SamplingPolicy()


@dataclass(frozen=True)
class Design:
    """chosen: (row index, reason) ordered by row index; summary: the stored sample design."""
    procedure: str
    chosen: list[tuple[int, str]]
    summary: dict = field(compare=True)


def discovery_size(n_pop: int, *, tolerable_rate: Fraction, confidence: Fraction) -> int:
    """Smallest n such that a simple random sample of n from n_pop rows with
    D = max(1, ceil(tolerable_rate * n_pop)) defective rows contains none of them with
    probability <= 1 - confidence (hypergeometric, exact Fractions). 0 for an empty pool."""
    if n_pop <= 0 or confidence == 0:
        return 0
    defects = min(max(1, math.ceil(Fraction(tolerable_rate) * n_pop)), n_pop)
    alpha = 1 - Fraction(confidence)
    miss, n = Fraction(1), 0
    while miss > alpha and n < n_pop:
        miss *= Fraction(n_pop - defects - n, n_pop - n)
        n += 1
    return n


def rank(seed: int, stratum: str, series_id: str, period: str) -> str:
    """The documented ranking key (module docstring)."""
    text = _SEP.join((PROCEDURE, str(seed), stratum, series_id, period))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def design_sample(rows: list[tuple[str, str]], *, seed: int, changed: set[tuple[str, str]],
                  request_key: Callable[[tuple[str, str]], Hashable],
                  policy: SamplingPolicy = DEFAULT_POLICY,
                  previously_failed: set[tuple[str, str]] = frozenset()) -> Design:
    """The sample of `rows` per the module docstring. `changed` and `previously_failed` keys
    absent from `rows` are ignored; `request_key((series_id, period))` names the verifier
    response a row is read from."""
    reason: dict[int, str] = {}
    by_series: dict[str, list[int]] = {}
    for i, (sid, _period) in enumerate(rows):
        by_series.setdefault(sid, []).append(i)

    def lowest(indices: list[int], stratum: str, k: int) -> list[int]:
        return sorted(indices, key=lambda i: rank(seed, stratum, *rows[i]))[:k]

    for idx in by_series.values():  # 1. latest of every series
        reason[idx[-1]] = "latest"

    failed_idx = [i for i, key in enumerate(rows) if key in previously_failed]
    for i in failed_idx:  # 1b. cells that mismatched before (deterministic defects)
        reason.setdefault(i, "previously-failed")

    changed_idx = [i for i, key in enumerate(rows) if key in changed and i not in reason]
    for i in lowest(changed_idx, "changed", policy.changed_cap):  # 2. changed (capped)
        reason[i] = "changed"

    pool = [i for i in range(len(rows)) if i not in reason]
    k = policy.history_per_series
    for sid, idx in by_series.items():  # 3. per-series period bands
        hist = [i for i in idx if i not in reason]
        for b in range(k):
            band = hist[b * len(hist) // k:(b + 1) * len(hist) // k]
            for i in lowest(band, f"series-stratum{_SEP}{b}", 1):
                reason[i] = "series-stratum"

    n_random = discovery_size(len(pool), tolerable_rate=policy.tolerable_rate,
                              confidence=policy.confidence)
    left = [i for i in pool if i not in reason]
    for i in lowest(left, "random", n_random):  # 4. discovery SRS
        reason[i] = "random"

    keys = {request_key(rows[i]) for i in reason}  # 5. free closure
    for i, key in enumerate(rows):
        if i not in reason and request_key(key) in keys:
            reason[i] = "same-response"

    chosen = sorted(reason.items())
    counts = {r: sum(1 for _, why in chosen if why == r) for r in REASONS}
    summary = {
        "procedure": PROCEDURE, "policy": policy.as_dict(),
        "n_observations": len(rows), "n_series": len(by_series),
        "n_previously_failed": len(failed_idx),
        "n_changed_total": len(changed_idx), "n_changed_checked": counts["changed"],
        "n_pool": len(pool), "n_random_target": n_random,
        "counts": counts, "n_items": len(chosen)}
    return Design(PROCEDURE, chosen, summary)
