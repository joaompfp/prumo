"""Run one dataset (one source, a fixed set of series) from fetch to `pending-verification`.

    running ──fetch──> raw store + raw_fetch rows (always kept: audit evidence)
       ├─ http.get raised / non-2xx / empty / HTML body ──> failed-fetch       + event(fetch_failure)
       ├─ same payload as the previous run, which is verified ──> verified (no rows, see below)
       ├─ parse/validate raised, or a series has no rows ──> failed-validation + event(format_change)
       └─ ONE transaction: observations + quarantine + revision events + state
          ──> pending-verification      (any exception inside: rolled back, failed-validation)

Only `verified` runs are served (view `served_observation`), so no failure here can hide or
overwrite previously verified data. Verification (Task 7) moves pending-verification onward.
"""
import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from ingest.db import Db
from ingest.http import Http
from ingest.models import Observation, SeriesSpec
from ingest.rawstore import RawStore
from ingest.sources import RawResponse, Source
from ingest.validate import Rejection, validate


@dataclass(frozen=True)
class DatasetRunResult:
    state: str  # final dataset_run.state
    run_id: int
    n_written: int  # observation rows committed by this run
    n_quarantined: int  # quarantine rows committed by this run


def dataset_key(source_name: str, series_ids: list[str]) -> str:
    """Dataset identity: "<source>:<sha256 of the sorted series ids joined by newline>"."""
    digest = hashlib.sha256("\n".join(sorted(series_ids)).encode()).hexdigest()
    return f"{source_name}:{digest}"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def run_dataset(db: Db, store: RawStore, source: Source, specs: list[SeriesSpec], http: Http,
                now: Callable[[], datetime] = _utc_now) -> DatasetRunResult:
    """Fetch, store, parse, validate and write one dataset; never raises for source misbehaviour.

    Preconditions (ValueError otherwise): `specs` non-empty, all from `source.name`, already
    synced to the DB (registry); `now()` returns a timezone-aware datetime (stored as UTC ISO-8601).

    Identical payload (Ruling D): if the sha256 fingerprint of this run's responses equals that of
    the previous run of the same dataset_key AND that run is `verified`, this run is recorded as
    `verified` with no observations, no quarantine, no events and no verification of its own
    (callers such as Task 7 must not verify it). The previously verified rows stay served. After a
    previous run in any other state, identical bytes are fully re-processed so a failed dataset
    can be retried.

    Observation provenance: every observation of the run references the run's FIRST raw_fetch
    row (Source.parse does not attribute rows to responses); all of the run's payloads are
    linked by raw_fetch.dataset_run_id.

    Revisions: compared on `value_text` (the publisher's verbatim token, so "2.0" -> "2.10" is a
    revision) against the currently served *verified fetched* value only, never legacy or
    unverified rows. A revision emits event(revision, {series_id, period, old, new}); the new
    value is stored as a new vintage (higher observation.id) either way.
    """
    _check_preconditions(source, specs)
    ts = lambda: _iso(now())  # noqa: E731
    key = dataset_key(source.name, [s.id for s in specs])
    run_id = db.begin_run(source.name, key, ts())

    def finish(state: str, event: str | None = None, detail: dict | None = None,
               n_written: int = 0, n_quarantined: int = 0) -> DatasetRunResult:
        t = ts()
        if event:
            db.add_event(t, event, run_id, detail)
        db.set_run_state(run_id, state, finished_at=t)
        return DatasetRunResult(state, run_id, n_written, n_quarantined)

    try:
        responses = source.fetch(specs, http)
    except Exception as e:  # network failure, possibly mid-pagination: nothing is written
        return finish("failed-fetch", "fetch_failure", {"error": repr(e)})
    if not responses:
        return finish("failed-fetch", "fetch_failure", {"error": "source returned no responses"})

    expected = getattr(source, "expected_format", None)
    fetched_at = ts()
    raw_ids, problems = [], []
    for resp in responses:
        problem = _fetch_problem(resp, expected)
        sha, path = store.save(source.name, resp.body)
        raw_ids.append(db.record_raw_fetch(
            source_name=source.name, run_id=run_id, url=resp.url,
            params_json=json.dumps(resp.params, sort_keys=True) if resp.params is not None else None,
            fetched_at=fetched_at, http_status=resp.status, sha256=sha, path=str(path),
            n_bytes=len(resp.body), ok=problem is None))
        if problem:
            problems.append({"url": resp.url, "status": resp.status, "reason": problem})
    if problems:
        return finish("failed-fetch", "fetch_failure", {"problems": problems})

    if _same_as_previous_verified(db, key, run_id):
        return finish("verified")

    try:
        parsed = source.parse(specs, responses)
        missing = [s.id for s in specs if not parsed.get(s.id)]
        if missing:
            return finish("failed-validation", "format_change", {"series_without_rows": missing})
        checked = [(s, *validate(s, parsed[s.id])) for s in specs]
    except Exception as e:
        return finish("failed-validation", "format_change", {"error": repr(e)})

    try:
        with db.transaction():
            n_written, n_quarantined = _write(db, run_id, raw_ids[0], fetched_at, checked, ts())
            db.set_run_state(run_id, "pending-verification", finished_at=ts())
    except Exception as e:  # rolled back: none of this run's observations/quarantine remain
        return finish("failed-validation", "format_change", {"error": repr(e), "stage": "write"})
    return DatasetRunResult("pending-verification", run_id, n_written, n_quarantined)


def _write(db: Db, run_id: int, raw_fetch_id: int, fetched_at: str,
           checked: list[tuple[SeriesSpec, list[Observation], list[Rejection]]],
           t: str) -> tuple[int, int]:
    n_written = n_quarantined = 0
    for spec, observations, rejections in checked:
        served = db.served_fetched_values(spec.id)
        for o in observations:
            old = served.get(o.period)
            if old is not None and old != o.value_text:
                db.add_event(t, "revision", run_id, {"series_id": spec.id, "period": o.period,
                                                     "old": old, "new": o.value_text})
        db.write_observations(run_id, raw_fetch_id, fetched_at, observations)
        if rejections:
            db.write_quarantine(run_id, spec.id, rejections, t)
        n_written += len(observations)
        n_quarantined += len(rejections)
    return n_written, n_quarantined


def _fetch_problem(resp: RawResponse, expected_format: str | None) -> str | None:
    if not 200 <= resp.status < 300:
        return "http_status"
    if not resp.body.strip():
        return "empty_body"
    if expected_format and _looks_like_html(resp.body):
        return "html_body"
    return None


def _looks_like_html(body: bytes) -> bool:
    head = body[:512].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    return head.startswith((b"<!doctype html", b"<html"))


def _fingerprint(shas: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(shas)).encode()).hexdigest()


def _same_as_previous_verified(db: Db, key: str, run_id: int) -> bool:
    prev = db.previous_run(key, run_id)
    if prev is None or prev[1] != "verified":
        return False
    return _fingerprint(db.raw_fetch_shas(prev[0])) == _fingerprint(db.raw_fetch_shas(run_id))


def _check_preconditions(source: Source, specs: list[SeriesSpec]) -> None:
    if not specs:
        raise ValueError("run_dataset needs at least one series (specs is empty)")
    foreign = sorted({s.source.name for s in specs} - {source.name})
    if foreign:
        raise ValueError(f"specs belong to source(s) {foreign}, not {source.name!r}")


def _iso(t: datetime) -> str:
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("now() must return a timezone-aware datetime")
    return t.astimezone(timezone.utc).isoformat()
