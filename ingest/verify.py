"""Truth verification (spec 6b): a random, seeded sample of a run's observations is re-read
through an independent, blinded `Verifier`; only a 100% match moves the run to `verified`.

    pending-verification ──verify_run──> verified             (every sampled item matches)
                                    └──> failed-verification  (any mismatch, not-found, verifier
                                         error / wrong count / wrong key or order) + event
    run_with_refetch: failed-verification -> event(refetch) -> a new run_dataset + fresh seed,
    up to max_attempts; a failed-verification run is never served (view served_observation).

The verifier sees only `BlindItem`s (key + spec); the expected side stays here. Each
verify_run writes one `verification` row (seed, actual sample size, passed) and one
`verification_item` per sampled observation holding every field the comparison used (expected
and observed text/decimal/unit/flag, the key the verifier answered for, evidence URL and the
sha256 of the evidence bytes kept in the raw store), so `replay_item` can re-decide each item
from stored data alone and `draw_sample` can redraw the sample from the seed.
"""
import random
import secrets
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime

from ingest.db import Db
from ingest.http import Http
from ingest.models import SeriesSpec, parse_decimal
from ingest.pipeline import DatasetRunResult, _iso, _utc_now, run_dataset
from ingest.rawstore import RawStore
from ingest.sources import Source
from ingest.verifiers import BlindItem, ItemResult, Verifier, get_verifier


class VerificationConflict(ValueError):
    """The run left `pending-verification` while this verification was in progress (another
    worker verified it); this verification's rows were rolled back."""


@dataclass(frozen=True)
class SampleItem:
    """A sampled observation with its expected side. Internal: verifiers get `blind()` only."""
    series_id: str
    period: str
    expected_text: str  # stored value_text (publisher token, in spec.decimal format)
    spec: SeriesSpec
    expected_unit: str
    expected_flag: str | None

    def blind(self) -> BlindItem:
        return BlindItem(series_id=self.series_id, period=self.period, spec=self.spec)


def draw_sample(db: Db, run_id: int, seed: int, size: int, *,
                specs: list[SeriesSpec]) -> list[SampleItem]:
    """Seeded, stratified sample of the observations written by run `run_id`.

    Every series of the run contributes its latest period (if the run has more series than
    `size`, the sample grows to one per series: no series is ever skipped); the rest of `size`
    is drawn uniformly without replacement with random.Random(seed) from the remaining
    observations. Same db + seed + size -> same list, ordered by (series_id, period).

    `specs` (the registry specs of the run's series) supplies SampleItem.spec and the declared
    unit; the DB does not store every spec field (e.g. decimal). ValueError if a sampled series
    has no spec or size < 1.
    """
    if size < 1:
        raise ValueError(f"sample size must be >= 1, got {size}")
    by_id = {s.id: s for s in specs}
    rows = db.observations_of_run(run_id)
    missing = sorted({r[0] for r in rows} - by_id.keys())
    if missing:
        raise ValueError(f"run {run_id} has series without a spec: {missing}")
    latest = {r[0]: i for i, r in enumerate(rows)}  # rows are ordered: last index = latest period
    must = sorted(latest.values())
    rest = sorted(set(range(len(rows))) - set(must))
    n_fill = min(max(size - len(must), 0), len(rest))
    chosen = sorted(must + random.Random(seed).sample(rest, n_fill))
    return [SampleItem(series_id=sid, period=period, expected_text=text, spec=by_id[sid],
                       expected_unit=by_id[sid].unit, expected_flag=flag)
            for sid, period, text, flag in (rows[i] for i in chosen)]


def verify_run(db: Db, run_id: int, verifier: Verifier, http: Http, seed: int | None = None,
               size: int = 50, *, specs: list[SeriesSpec], store: RawStore | None = None,
               now: Callable[[], datetime] = _utc_now) -> bool:
    """Verify a `pending-verification` run; True iff it ends `verified`.

    The sample is draw_sample(db, run_id, seed, size, specs=specs); seed defaults to
    secrets.randbits(63) and is stored either way. The verifier gets the blinded items; each
    result is turned into a stored item row and decided by `_row_mismatch` (key at the same
    position, exact Decimal value, unit/flag when exposed). A verifier that raises or returns the
    wrong number of results fails every item (noted). Evidence bytes are saved to `store` under
    "verify-<source>" (ValueError if evidence is returned and store is None).

    Rows, failure event and the state change are one transaction; the state change is a
    compare-and-set from pending-verification, so if another worker finished this run meanwhile
    everything is rolled back and VerificationConflict is raised.
    ValueError (nothing written) if the run is not `pending-verification` (e.g. a short-circuit
    `verified` run, which has no verification of its own) or the verifier/specs belong to
    another source.
    """
    state = db.run_state(run_id)
    if state != "pending-verification":
        raise ValueError(f"run {run_id} is {state!r}; only pending-verification runs are verified")
    foreign = sorted({s.source.name for s in specs} - {verifier.source_name})
    if foreign:
        raise ValueError(f"verifier for {verifier.source_name!r} cannot verify source(s) {foreign}")
    if seed is None:
        seed = secrets.randbits(63)
    items = draw_sample(db, run_id, seed, size, specs=specs)

    results: list = [None] * len(items)
    whole_note = None
    try:
        got = list(verifier.check([i.blind() for i in items], http))
    except Exception as e:  # a broken verifier is a failure, never a pass
        whole_note = f"verifier raised: {e!r}"
    else:
        if len(got) != len(items):
            whole_note = f"verifier returned {len(got)} results for {len(items)} items"
        else:
            results = got

    rows = []
    for item, res in zip(items, results):
        row, note = _item_row(item, res, store, verifier.source_name)
        note = whole_note or note or _row_mismatch(row)
        rows.append({**row, "match": note is None, "note": note})
    bad = [r for r in rows if not r["match"]]
    passed = bool(rows) and not bad

    t = _iso(now())
    with db.transaction():
        vid = db.add_verification(run_id, seed, len(rows), passed, t)
        for row in rows:
            db.add_verification_item(vid, row)
        if not passed:
            db.add_event(t, "verification_failure", run_id, {
                "run_id": run_id, "seed": seed, "n_items": len(rows), "n_mismatch": len(bad),
                "first_mismatches": [
                    {"series_id": r["series_id"], "period": r["period"],
                     "expected": r["expected_text"], "observed": r["observed_text"]}
                    for r in bad[:5]]})
        new_state = "verified" if passed else "failed-verification"
        if not db.transition_run_state(run_id, "pending-verification", new_state):
            raise VerificationConflict(
                f"run {run_id} is no longer pending-verification (now "
                f"{db.run_state(run_id)!r}); this verification was rolled back")
    return passed


def _str(x: object) -> str | None:
    """Only exact `str` is stored (no subclasses, whose dunders could lie in comparisons);
    anything else a verifier returns is recorded as None."""
    return x if type(x) is str else None


def _item_row(item: SampleItem, res: object, store: RawStore | None,
              source_name: str) -> tuple[dict, str | None]:
    """The stored row for one item (without match/note) and a shape note for a malformed result.
    A malformed result keeps no observed fields, so its stored row can never replay as a match."""
    row = {"series_id": item.series_id, "period": item.period,
           "expected_text": item.expected_text, "expected_decimal": item.spec.decimal,
           "expected_unit": item.expected_unit, "expected_flag": item.expected_flag,
           "observed_series_id": None, "observed_period": None, "observed_text": None,
           "observed_decimal": None, "observed_unit": None, "observed_flag": None,
           "evidence_url": None, "evidence_sha256": None}
    if res is None:
        return row, None
    if type(res) is not ItemResult or (res.evidence is not None
                                       and type(res.evidence) is not bytes):
        return row, f"malformed result: {type(res).__name__}"
    if res.evidence is not None:
        if store is None:
            raise ValueError("verifier returned evidence bytes but verify_run has no store")
        row["evidence_sha256"], _ = store.save(f"verify-{source_name}", res.evidence)
    row.update(observed_series_id=_str(res.series_id), observed_period=_str(res.period),
               observed_text=_str(res.observed_text),
               observed_decimal=(res.observed_decimal
                                 if _str(res.observed_decimal) in (".", ",") else None),
               observed_unit=_str(res.observed_unit), observed_flag=_str(res.observed_flag),
               evidence_url=_str(res.evidence_url))
    wrong = [f"{f}: {type(getattr(res, f)).__name__}" for f in _TEXT_FIELDS
             if getattr(res, f) is not None and _str(getattr(res, f)) is None]
    # e.g. a float observed_text (would bypass exact comparison) or a str subclass
    return row, (f"result fields must be exact str: {', '.join(wrong)}" if wrong else None)


_TEXT_FIELDS = ("series_id", "period", "observed_text", "evidence_url", "observed_decimal",
                "observed_unit", "observed_flag")


def _blank(s: str | None) -> str | None:
    return s.strip() or None if s is not None else None


def _row_mismatch(row: dict) -> str | None:
    """Why the stored item row is not a match, or None if it is. Uses only stored fields and
    exact Decimals (never float); shared by verify_run and replay_item."""
    if (row["observed_series_id"], row["observed_period"]) != (row["series_id"], row["period"]):
        return (f"result is for {row['observed_series_id']}/{row['observed_period']}, "
                f"expected {row['series_id']}/{row['period']} (wrong order or key)")
    if row["observed_text"] is None:
        return "not found by verifier"
    if row["observed_decimal"] not in (".", ","):
        return "invalid observed_decimal"
    try:
        expected = parse_decimal(row["expected_text"], row["expected_decimal"])
    except ValueError:
        return f"expected_text not a number with decimal {row['expected_decimal']!r}"
    try:
        observed = parse_decimal(row["observed_text"], row["observed_decimal"])
    except ValueError:
        return f"observed_text not a number with decimal {row['observed_decimal']!r}"
    if observed != expected:
        return "value differs"
    if (row["observed_unit"] is not None
            and row["observed_unit"].strip() != (row["expected_unit"] or "").strip()):
        return f"unit differs: expected {row['expected_unit']!r}, observed {row['observed_unit']!r}"
    if row["observed_flag"] is not None and _blank(row["observed_flag"]) != _blank(
            row["expected_flag"]):
        return f"flag differs: expected {row['expected_flag']!r}, observed {row['observed_flag']!r}"
    return None


def replay_item(db: Db, store: RawStore, verification_item_id: int) -> bool:
    """Re-decide a stored verification_item from its stored fields only (no registry, no
    network) and return the match. ValueError for a legacy (pre-0004) item. If evidence bytes
    were kept, their file is loaded from `store` and integrity-checked (RawIntegrityError if
    altered)."""
    row = db.verification_item(verification_item_id)
    if row["expected_decimal"] is None:  # always set since 0004 (spec.decimal is never None)
        raise ValueError(f"verification_item {verification_item_id} is a legacy item "
                         "(pre-0004): its comparison fields were not stored, cannot replay")
    if row["evidence_sha256"] is not None:
        sha = row["evidence_sha256"]
        source = db.verification_item_source(verification_item_id)
        store.load(store.root / f"verify-{source}" / sha[:2] / sha)
    return _row_mismatch(row) is None


def run_with_refetch(db: Db, store: RawStore, source: Source, verifier: Verifier,
                     specs: list[SeriesSpec], http: Http, max_attempts: int = 3, size: int = 50,
                     now: Callable[[], datetime] | None = None) -> DatasetRunResult:
    """run_dataset, then verify_run with a fresh random seed; on failure emit event(refetch) and
    re-fetch the whole dataset (a new run: identical bytes are re-processed because the previous
    run is not verified), at most `max_attempts` runs in total.

    `verifier` must be the one registered for `source.name` (register_verifier enforces the
    independence rule), else ValueError.

    Returns the last run's result: `verified` on a pass; `failed-verification` after
    max_attempts failures (left unserved; escalation is the CLI report's business); any other
    run_dataset outcome (failed-fetch, failed-validation, or the `verified` short-circuit for a
    payload identical to the previous verified run, which gets no verification) as-is.
    """
    if max_attempts < 1:
        raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")
    try:
        registered = get_verifier(source.name)
    except KeyError:
        registered = None
    if registered is not verifier:
        raise ValueError(f"verifier is not the one registered for source {source.name!r}")
    now = now or _utc_now
    for attempt in range(1, max_attempts + 1):
        result = run_dataset(db, store, source, specs, http, now)
        if result.state != "pending-verification":
            return result
        if verify_run(db, result.run_id, verifier, http, size=size, specs=specs, store=store,
                      now=now):
            return replace(result, state="verified")
        if attempt < max_attempts:
            db.add_event(_iso(now()), "refetch", result.run_id,
                         {"failed_run_id": result.run_id, "next_attempt": attempt + 1,
                          "max_attempts": max_attempts})
    return replace(result, state="failed-verification")
