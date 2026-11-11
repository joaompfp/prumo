"""Truth verification (spec 6b): a random, seeded sample of a run's observations is re-read
through an independent `Verifier`; only a 100% match moves the run to `verified` (served).

    pending-verification ──verify_run──> verified             (every sampled item matches)
                                    └──> failed-verification  (any mismatch, not-found, verifier
                                         error / wrong count / out-of-order result) + event
    run_with_refetch: failed-verification -> event(refetch) -> a new run_dataset + fresh seed,
    up to max_attempts; a failed-verification run is never served (view served_observation).

Every verify_run writes one `verification` row (seed, actual sample size, passed) and one
`verification_item` per sampled observation (expected/observed text, evidence URL, observed
decimal/unit/flag, match, note), so an auditor can redraw the sample from the seed
(draw_sample) and replay each comparison.
"""
import random
import secrets
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

from ingest.db import Db
from ingest.http import Http
from ingest.models import SeriesSpec, parse_decimal
from ingest.pipeline import DatasetRunResult, _iso, _utc_now, run_dataset
from ingest.rawstore import RawStore
from ingest.sources import Source
from ingest.verifiers import ItemResult, SampleItem, Verifier


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
               size: int = 50, *, specs: list[SeriesSpec],
               now: Callable[[], datetime] = _utc_now) -> bool:
    """Verify a `pending-verification` run; True iff it ends `verified`.

    The sample is draw_sample(db, run_id, seed, size, specs=specs); seed defaults to
    secrets.randbits(63) and is stored either way. An item matches only if (see _mismatch):
    the result is for that item's key, observed_text is not None, the numbers are equal as exact
    Decimals (expected parsed with spec.decimal, observed with observed_decimal; no tolerance),
    and the observed unit / flag, when the channel exposes them, equal the expected ones.
    A verifier that raises or returns the wrong number of results fails every item (noted).
    Rows, state and the failure event are written in one transaction.

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
        got = list(verifier.check(list(items), http))
    except Exception as e:  # a broken verifier is a failure, never a pass
        whole_note = f"verifier raised: {e!r}"
    else:
        if len(got) != len(items):
            whole_note = f"verifier returned {len(got)} results for {len(items)} items"
        else:
            results = got
    checked = [(item, res, whole_note or _safe_mismatch(item, res))
               for item, res in zip(items, results)]
    bad = [(item, res) for item, res, note in checked if note is not None]
    passed = bool(items) and not bad

    t = _iso(now())
    with db.transaction():
        vid = db.add_verification(run_id, seed, len(items), passed, t)
        for item, res, note in checked:
            r = res if isinstance(res, ItemResult) else ItemResult(None, "")
            db.add_verification_item(
                vid, series_id=item.series_id, period=item.period,
                expected_text=item.expected_text, observed_text=_str(r.observed_text),
                evidence_url=_str(r.evidence_url) or None, match=note is None,
                observed_decimal=r.observed_decimal if r.observed_decimal in (".", ",") else None,
                observed_unit=_str(r.observed_unit), observed_flag=_str(r.observed_flag),
                note=note)
        if not passed:
            db.add_event(t, "verification_failure", run_id, {
                "run_id": run_id, "seed": seed, "n_items": len(items), "n_mismatch": len(bad),
                "first_mismatches": [
                    {"series_id": i.series_id, "period": i.period, "expected": i.expected_text,
                     "observed": _str(getattr(r, "observed_text", None))}
                    for i, r in bad[:5]]})
        db.set_run_state(run_id, "verified" if passed else "failed-verification")
    return passed


def _str(x: object) -> str | None:
    """Only real strings are stored; anything else a verifier returns is recorded as None."""
    return x if isinstance(x, str) else None


def _safe_mismatch(item: SampleItem, res: object) -> str | None:
    try:
        return _mismatch(item, res)
    except Exception as e:  # malformed result: a failure, never a crash that leaves it pending
        return f"cannot compare result: {e!r}"


def _blank(s: str | None) -> str | None:
    return s.strip() or None if s is not None else None


def _mismatch(item: SampleItem, res: object) -> str | None:
    """Why `res` does not confirm `item`, or None if it does. Never uses float."""
    if not isinstance(res, ItemResult):
        return f"verifier returned {type(res).__name__}, not ItemResult"
    if ((res.series_id is not None and res.series_id != item.series_id)
            or (res.period is not None and res.period != item.period)):
        return (f"result is for {res.series_id}/{res.period}, "
                f"expected {item.series_id}/{item.period} (out of order)")
    if res.observed_text is None:
        return "not found by verifier"
    if not isinstance(res.observed_text, str):  # e.g. a float: would bypass exact comparison
        return f"observed_text must be the publisher's text, got {type(res.observed_text).__name__}"
    if res.observed_decimal not in (".", ","):
        return f"invalid observed_decimal {res.observed_decimal!r}"
    try:
        expected = parse_decimal(item.expected_text, item.spec.decimal)
    except ValueError:
        return f"expected_text not a number with decimal {item.spec.decimal!r}"
    try:
        observed = parse_decimal(res.observed_text, res.observed_decimal)
    except ValueError:
        return f"observed_text not a number with decimal {res.observed_decimal!r}"
    if observed != expected:
        return "value differs"
    if res.observed_unit is not None and res.observed_unit.strip() != item.expected_unit.strip():
        return f"unit differs: expected {item.expected_unit!r}, observed {res.observed_unit!r}"
    if res.observed_flag is not None and _blank(res.observed_flag) != _blank(item.expected_flag):
        return f"flag differs: expected {item.expected_flag!r}, observed {res.observed_flag!r}"
    return None


def run_with_refetch(db: Db, store: RawStore, source: Source, verifier: Verifier,
                     specs: list[SeriesSpec], http: Http, max_attempts: int = 3, size: int = 50,
                     now: Callable[[], datetime] | None = None) -> DatasetRunResult:
    """run_dataset, then verify_run with a fresh random seed; on failure emit event(refetch) and
    re-fetch the whole dataset (a new run: identical bytes are re-processed because the previous
    run is not verified), at most `max_attempts` runs in total.

    Returns the last run's result: `verified` on a pass; `failed-verification` after
    max_attempts failures (left unserved; escalation is the CLI report's business); any other
    run_dataset outcome (failed-fetch, failed-validation, or the `verified` short-circuit for a
    payload identical to the previous verified run, which gets no verification) as-is.
    """
    if max_attempts < 1:
        raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")
    if verifier.source_name != source.name:
        raise ValueError(f"verifier is for {verifier.source_name!r}, source is {source.name!r}")
    now = now or _utc_now
    for attempt in range(1, max_attempts + 1):
        result = run_dataset(db, store, source, specs, http, now)
        if result.state != "pending-verification":
            return result
        if verify_run(db, result.run_id, verifier, http, size=size, specs=specs, now=now):
            return replace(result, state="verified")
        if attempt < max_attempts:
            db.add_event(_iso(now()), "refetch", result.run_id,
                         {"failed_run_id": result.run_id, "next_attempt": attempt + 1,
                          "max_attempts": max_attempts})
    return replace(result, state="failed-verification")
