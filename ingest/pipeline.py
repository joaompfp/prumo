"""Run one dataset (one source, a fixed set of series) from fetch to `pending-verification`.

    running ──fetch──> raw store + raw_fetch rows (always kept: audit evidence)
       ├─ http.get raised / non-2xx / empty / HTML body ──> failed-fetch       + event(fetch_failure)
       ├─ same payload as the previous run, which is verified ──> verified (no rows, see below)
       ├─ parse/validate raised, or a series has no rows ──> failed-validation + event(format_change)
       └─ ONE transaction: observations + quarantine + revision events + state
          ──> pending-verification      (any exception inside: rolled back, failed-validation)
       a recorded replay whose ORIGINAL receipts are older than held verified fetched rows
          ──> rolled back atomically as 'blocked-stale' + event(stale_refusal) instead

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


class StaleRecordedError(ValueError):
    """A recorded replay tried to insert observations OLDER than the verified fetched data
    already held for those series. Raised INSIDE the write transaction: the whole dataset
    write rolls back atomically, so a concurrent newer writer is never displaced by old
    recorded rows even when it lands between the CLI preflight and the insert."""


def dataset_key(source_name: str, series_ids: list[str]) -> str:
    """Dataset identity: "<source>:<sha256 of the sorted series ids joined by newline>"."""
    digest = hashlib.sha256("\n".join(sorted(series_ids)).encode()).hexdigest()
    return f"{source_name}:{digest}"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _receipt_ts(raw: str) -> str:
    """A recorded-replay receipt timestamp (`RawResponse.fetched_at`): a timezone-aware
    ISO-8601 datetime, normalized to UTC. Raises ValueError on anything else - a bad receipt
    is NEVER silently replaced by 'now'."""
    if not isinstance(raw, str):
        raise ValueError(f"recorded receipt fetched_at must be a string, got {type(raw).__name__}")
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as e:
        raise ValueError(f"recorded receipt fetched_at is not ISO-8601: {raw!r}") from e
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"recorded receipt fetched_at must be timezone-aware: {raw!r}")
    return dt.astimezone(timezone.utc).isoformat()


def run_dataset(db: Db, store: RawStore, source: Source, specs: list[SeriesSpec], http: Http,
                now: Callable[[], datetime] = _utc_now, *,
                input_origin: str = "live") -> DatasetRunResult:
    """Fetch, store, parse, validate and write one dataset; never raises for source misbehaviour.

    Preconditions (ValueError otherwise): `specs` non-empty, all from `source.name`, already
    synced to the DB (registry); `now()` returns a timezone-aware datetime (stored as UTC ISO-8601).

    Identical payload (Ruling D): if the sha256 fingerprint of this run's responses equals that of
    the previous run of the same dataset_key AND that run is `verified`, this run is recorded as
    `verified` with no observations, no quarantine, no events and no verification of its own
    (callers such as Task 7 must not verify it). The previously verified rows stay served. After a
    previous run in any other state, identical bytes are fully re-processed so a failed dataset
    can be retried.

    Fetch is consumed incrementally: each response is saved to the raw store and gets its own
    raw_fetch row (linked by raw_fetch.dataset_run_id) as it arrives, so pages received before
    a mid-pagination exception are kept as evidence. A plain list from fetch works too.

    Observation provenance: each observation references the raw_fetch row of the response its
    RawRow came from (`RawRow.response_index`, default 0); its fetched_at is that row's.
    An out-of-range response_index is a failed-validation (format_change).

    Empty series (Ruling M): a series with zero valid observations (no rows from parse, or all
    rows quarantined) emits event(format_change, {series_id, reason: 'no_valid_observations',
    n_raw_rows, n_quarantined}) and the run continues; only when EVERY series is empty does
    the run end failed-validation (nothing written).

    Revisions: compared on `value_text` (the publisher's verbatim token, so "2.0" -> "2.10" is a
    revision) against the currently served *verified fetched* value only, never legacy or
    unverified rows. A revision emits event(revision, {series_id, period, old, new}); the new
    value is stored as a new vintage (higher observation.id) either way.
    """
    if input_origin not in ("live", "recorded"):
        raise ValueError(f"input_origin must be 'live' or 'recorded', got {input_origin!r}")
    _check_preconditions(source, specs)
    ts = lambda: _iso(now())  # noqa: E731
    key = dataset_key(source.name, [s.id for s in specs])
    run_id = db.begin_run(source.name, key, ts(), input_origin=input_origin)

    def finish(state: str, event: str | None = None, detail: dict | None = None,
               n_written: int = 0, n_quarantined: int = 0) -> DatasetRunResult:
        t = ts()
        if event:
            db.add_event(t, event, run_id, detail)
        db.set_run_state(run_id, state, finished_at=t)
        return DatasetRunResult(state, run_id, n_written, n_quarantined)

    # Consume fetch incrementally: each response is stored as evidence the moment it arrives,
    # so pages received before a mid-pagination failure are kept (raw file + raw_fetch row).
    expected = getattr(source, "expected_format", None)
    responses: list[RawResponse] = []
    raws: list[tuple[int, str]] = []  # (raw_fetch id, fetched_at) per response, fetch order
    problems: list[dict] = []
    try:
        it = iter(source.fetch(specs, http))
    except Exception as e:
        return finish("failed-fetch", "fetch_failure", {"error": repr(e)})
    while True:
        try:
            resp = next(it)
        except StopIteration:
            break
        except Exception as e:  # network failure, possibly mid-pagination: no observations
            return finish("failed-fetch", "fetch_failure", {"error": repr(e)})
        problem = _fetch_problem(resp, expected)
        if resp.fetched_at is not None:
            # Recorded replay: the receipt's ORIGINAL fetch time is the data's retrieval
            # date. Invalid receipt -> failed-validation (never a silent 'now').
            try:
                fetched_at = _receipt_ts(resp.fetched_at)
            except ValueError as e:
                return finish("failed-validation", "format_change", {"error": str(e)})
        else:
            fetched_at = ts()
        raws.append((_record(db, store, source.name, run_id, resp, fetched_at, problem is None),
                     fetched_at))
        responses.append(resp)
        if problem:
            problems.append({"url": resp.url, "status": resp.status, "reason": problem})
    if not responses:
        return finish("failed-fetch", "fetch_failure", {"error": "source returned no responses"})
    if problems:
        return finish("failed-fetch", "fetch_failure", {"problems": problems})

    if _same_as_previous_verified(db, key, run_id):
        return finish("verified")

    try:
        parsed = source.parse(specs, responses)
        checked = []
        for s in specs:
            rows = parsed.get(s.id) or []
            bad = sorted({r.response_index for r in rows if r.response_index >= len(responses)})
            if bad:
                raise ValueError(f"series {s.id!r}: response_index {bad} out of range "
                                 f"(run has {len(responses)} responses)")
            checked.append((s, len(rows), *validate(s, rows)))
    except Exception as e:
        return finish("failed-validation", "format_change", {"error": repr(e)})

    # Ruling M: a series with zero valid observations is a format_change event, not a run failure,
    # unless every series of the dataset is in that state.
    empty = [{"series_id": s.id, "reason": "no_valid_observations", "n_raw_rows": n_raw,
              "n_quarantined": len(rej)} for s, n_raw, obs, rej in checked if not obs]
    if len(empty) == len(checked):
        t = ts()
        for detail in empty:
            db.add_event(t, "format_change", run_id, detail)
        return finish("failed-validation")

    try:
        with db.transaction():
            if input_origin == "recorded":
                _guard_recorded_not_stale(db, raws, checked)
            t = ts()
            for detail in empty:
                db.add_event(t, "format_change", run_id, detail)
            n_written, n_quarantined = _write(db, run_id, raws, checked, t)
            db.set_run_state(run_id, "pending-verification", finished_at=ts())
    except StaleRecordedError as e:  # rolled back atomically: nothing of this run remains
        return finish("blocked-stale", "stale_refusal", {"error": str(e)})
    except Exception as e:  # rolled back: none of this run's observations/quarantine remain
        return finish("failed-validation", "format_change", {"error": repr(e), "stage": "write"})
    return DatasetRunResult("pending-verification", run_id, n_written, n_quarantined)


def _guard_recorded_not_stale(db: Db, raws: list[tuple[int, str]], checked: list) -> None:
    """Recorded-replay continuity guard, called INSIDE the observation transaction (all SQL
    via Db). A recorded run's observations are only as new as their own OLDEST original
    collector receipt (the raw_fetch.fetched_at tied to each observation through the row's
    response_index; dataset-metadata and verifier responses carry no rows and never count).
    Per series, when the held VERIFIED fetched rows reach past that bound, inserting would
    let the served view's last-inserted tie-break replace NEWER verified data with old
    recorded rows: refuse the whole dataset atomically instead. Equal-time re-imports pass
    (the identical-payload short-circuit keeps them no-ops), genuinely newer bundles advance
    the data, and legacy-unverified rows never count as held verified data, so a legacy-only
    or empty database is free to accept any recorded bundle."""
    stale = []
    oldests = []
    for spec, _n_raw, observations, _rejections in checked:
        if not observations:
            continue
        # UTC ISO text: lexicographic = chronological; receipts back rows, never metadata
        oldest = min(raws[o.response_index][1] for o in observations)
        oldests.append(oldest)
        held = db.max_verified_fetched_at([spec.id])
        if held is not None and held > oldest:
            stale.append(f"{spec.id} (held verified fetched reaches {held})")
    if stale:
        raise StaleRecordedError(
            f"recorded replay refused for {len(stale)} series: this run's oldest original "
            f"collector receipt is {min(oldests)}, but the verified fetched data already "
            f"held is newer for {'; '.join(stale)}; a recorded replay never replaces NEWER "
            f"verified data")


def _record(db: Db, store: RawStore, source_name: str, run_id: int, resp: RawResponse,
            fetched_at: str, ok: bool) -> int:
    sha, path = store.save(source_name, resp.body)
    return db.record_raw_fetch(
        source_name=source_name, run_id=run_id, url=resp.url,
        params_json=json.dumps(resp.params, sort_keys=True) if resp.params is not None else None,
        fetched_at=fetched_at, http_status=resp.status, sha256=sha, path=str(path),
        n_bytes=len(resp.body), ok=ok)


def _write(db: Db, run_id: int, raws: list[tuple[int, str]],
           checked: list[tuple[SeriesSpec, int, list[Observation], list[Rejection]]],
           t: str) -> tuple[int, int]:
    n_written = n_quarantined = 0
    for spec, _, observations, rejections in checked:
        served = db.served_fetched_values(spec.id)
        for o in observations:
            old = served.get(o.period)
            if old is not None and old != o.value_text:
                db.add_event(t, "revision", run_id, {"series_id": spec.id, "period": o.period,
                                                     "old": old, "new": o.value_text})
        db.write_observations(run_id, [(o, *raws[o.response_index]) for o in observations])
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
