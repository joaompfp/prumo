"""Truth verification (spec 6b): a random, seeded sample of a run's observations is re-read
through an independent `Verifier`; only a 100% match moves the run to `verified` (served).
"""
import random

from ingest.db import Db
from ingest.models import SeriesSpec
from ingest.verifiers import SampleItem


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
