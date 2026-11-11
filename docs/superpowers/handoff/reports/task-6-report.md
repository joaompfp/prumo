# Task 6 report: Pipeline core (one dataset, one transaction)

Status: DONE_WITH_CONCERNS (concerns are design choices to confirm; nothing is broken)

Commits on `pipeline-rebuild`:
- `48a1709` ingest: polite HTTP client (throttle, retry, safe redirects) behind an Http protocol
- `e1dfaeb` ingest: dataset_key + raw_fetch run link (0002), Db methods for dataset runs
- `59e1337` ingest: run_dataset pipeline core and Source protocol

Full suite: `.venv-ci/bin/python -m pytest tests/ingest -q` gives `170 passed in 11.70s`.

## What I built

- `ingest/http.py`: `HttpResult`, the `Http` Protocol and `RequestsHttp` (Ruling L).
- `ingest/migrations/0002_dataset_key.sql`: adds `dataset_run.dataset_key` and `raw_fetch.dataset_run_id`, both nullable, each with an index. Migration 0001 is unchanged.
- `ingest/db.py`: new Db methods for dataset runs. All SQL stays in this file.
- `ingest/sources/__init__.py`: `RawResponse` and the `Source` Protocol.
- `ingest/pipeline.py`: `DatasetRunResult`, `dataset_key` and `run_dataset`.
- `tests/ingest/fakes.py`: `FakeHttp`, `FakeSource`, `spec()`, `payload()` and `ok()`.
- `tests/ingest/test_pipeline.py`: 26 tests.
- `tests/ingest/test_http.py`: 9 tests.
- `tests/ingest/test_db.py`: the migration-count test now compares against the migration files on disk instead of `== 1`, plus a new test for migration 0002.

## Public interfaces (exact signatures)

```python
# ingest/http.py
USER_AGENT = "prumo-ingest/1.0 (+https://cae.joao.date)"
@dataclass(frozen=True)
class HttpResult: status: int; body: bytes; url: str   # url = final URL incl. query
class Http(Protocol):
    def get(self, url: str, params: dict | None = None, headers: dict | None = None) -> HttpResult: ...
class RequestsHttp:
    def __init__(self, throttle_rps: float = 1.0, timeout: float = 30.0, *, retries: int = 3, backoff: float = 1.0)
    def get(self, url, params=None, headers=None) -> HttpResult

# ingest/sources/__init__.py
@dataclass(frozen=True)
class RawResponse: url: str; params: dict | None; status: int; body: bytes
class Source(Protocol):
    name: str
    expected_format: ClassVar[Literal["json","csv","xml","tsv"] | None]   # read via getattr(..., None)
    def fetch(self, specs: list[SeriesSpec], http: Http) -> list[RawResponse]: ...
    def parse(self, specs: list[SeriesSpec], responses: list[RawResponse]) -> dict[str, list[RawRow]]: ...

# ingest/pipeline.py
@dataclass(frozen=True)
class DatasetRunResult: state: str; run_id: int; n_written: int; n_quarantined: int
def dataset_key(source_name: str, series_ids: list[str]) -> str   # "<src>:<sha256('\n'.join(sorted(ids)))>"
def run_dataset(db: Db, store: RawStore, source: Source, specs: list[SeriesSpec], http: Http,
                now: Callable[[], datetime] = _utc_now) -> DatasetRunResult

# ingest/db.py (Db methods added)
begin_run(source_name: str, dataset_key: str, started_at: str) -> int
set_run_state(run_id: int, state: str, finished_at: str | None = None) -> None
run_state(run_id: int) -> str
previous_run(dataset_key: str, before_run_id: int) -> tuple[int, str] | None
record_raw_fetch(*, source_name, run_id, url, params_json, fetched_at, http_status, sha256, path, n_bytes, ok) -> int
raw_fetch_shas(run_id: int) -> list[str]
served_fetched_values(series_id: str) -> dict[str, str]          # period -> value_text, verified fetched only
write_observations(run_id: int, raw_fetch_id: int, fetched_at: str, observations: list[Observation]) -> None
write_quarantine(run_id: int, series_id: str, rejections: list[Rejection], created_at: str) -> None
add_event(ts: str, kind: str, run_id: int | None, detail: dict | None = None) -> None
```

The Db write methods run plain statements. Outside a transaction each statement commits on its own. Inside `with db.transaction():` they join that transaction.

## Behaviour of run_dataset

1. It checks its inputs first. It raises `ValueError` if `specs` is empty, if any spec belongs to a different source, or if `now()` returns a datetime without a timezone.
2. It inserts a `dataset_run` row in state `running`, with its `dataset_key`.
3. It calls `source.fetch`.
   - If fetch raises (for example `http.get` fails on page 2), the run becomes `failed-fetch` with `event(fetch_failure, {error})`.
   - If fetch returns no responses, the run also becomes `failed-fetch`.
4. Every response is saved to the raw store and gets its own `raw_fetch` row, linked to the run. This happens outside the observation transaction because these rows are audit evidence.
   - `ok=0` when the status is not 2xx, the body is empty or whitespace-only, or the body is HTML while the source declares `expected_format`.
   - HTML detection: after stripping a BOM and leading whitespace, the body starts with `<!doctype html` or `<html`.
   - If any response has one of these problems, the run becomes `failed-fetch` with `event(fetch_failure, {problems: [{url, status, reason}]})`. `reason` is one of `http_status`, `empty_body` or `html_body`.
5. Identical-payload short-circuit (Ruling D). It applies only when the previous run with the same `dataset_key` is in state `verified` and both runs have the same payload fingerprint. The fingerprint is sha256 over the sorted response sha256s, read from `raw_fetch`.
   - The new run is set to `verified`. It writes no observations, no quarantine and no events, and has no verification of its own.
   - The rows already being served are unaffected.
   - After a previous run in any other state, identical bytes are parsed and validated again.
6. It runs `source.parse`, then checks that every spec has a non-empty row list, then calls `validate` for each spec.
   - Any exception, or a spec with no rows, makes the run `failed-validation` with `event(format_change, {error} | {series_without_rows})`.
7. One transaction then does all of the following, and the run ends `pending-verification`:
   - checks for revisions and writes their events;
   - writes the observations, in fetch order and series order;
   - writes the quarantine rows;
   - changes the run state.

   Any exception inside the transaction rolls all of it back. The run then becomes `failed-validation` with `event(format_change, {error, stage: "write"})`.

Only `verified` runs are served, so previously verified data stays served after every failure. This is tested for each failure kind.

## Decisions to confirm

- **Observation provenance (main concern).** Every observation in a run points to the run's first `raw_fetch` row, because `Source.parse` does not say which response a row came from. All of the run's payloads are still reachable through `raw_fetch.dataset_run_id`. Uniqueness holds because each run gets new `raw_fetch` rows and `validate` rejects duplicate periods within a series. For paginated sources, an observation's direct `raw_fetch_id` link may therefore point to the wrong page. Exact per-row attribution would need a field added to `RawRow`, or `parse` returning an index into the responses. I did not change Task 5's types.
- **Revisions compare `value_text`**, the publisher's token, after a match on the same period. So `"2.0"` changing to `"2.10"` counts as a revision, even though the numeric value is the same. This follows "keep the publisher's precision". The comparison is only against served, verified data of kind `fetched`, never legacy rows or unverified runs.
- **A series with zero raw rows means `failed-validation`.** Every spec handed to `run_dataset` is treated as expected to have data. A series whose rows are all quarantined still ends `pending-verification`, with zero rows written.
- **5xx after the last retry is returned, not raised.** `RequestsHttp` returns it as an `HttpResult` so the pipeline records it as evidence. Only network errors and timeouts raise, using the `requests` exception.
  - I added keyword-only `retries=3` and `backoff=1.0` so the tests run fast.
  - Redirects are followed by hand, at most 5. A redirect to a non-http(s) URL raises `ValueError`.
  - The throttle applies to every attempt, retry and redirect.
- **`now` has a default (UTC now)** because Task 7's planned `run_with_refetch` signature takes no `now`.
- **Timestamps** are stored as `datetime.astimezone(UTC).isoformat()`, for example `2026-11-10T12:00:02+00:00`.
- **The `fetched` run state is not used.** Runs go straight from `running` to their final state.
- **Note for Task 7.** When `run_dataset` returns `state == "verified"` (the short-circuit), Task 7 must not draw a sample or write a verification for that run.

## RED and GREEN evidence

HTTP client, RED:
```
$ .venv-ci/bin/python -m pytest tests/ingest/test_http.py -q
E   ModuleNotFoundError: No module named 'ingest.http'
ERROR tests/ingest/test_http.py
=============================== 1 error in 0.22s ===============================
```

HTTP client, GREEN:
```
tests/ingest/test_http.py .........                                      [100%]
============================== 9 passed in 5.41s ===============================
```

Pipeline, RED:
```
$ .venv-ci/bin/python -m pytest tests/ingest/test_pipeline.py -v
tests/ingest/test_pipeline.py:9: in <module>
    from ingest.pipeline import DatasetRunResult, dataset_key, run_dataset
E   ModuleNotFoundError: No module named 'ingest.pipeline'
=============================== 1 error in 0.37s ===============================
```

Pipeline, GREEN:
```
tests/ingest/test_pipeline.py::test_happy_path_pending_verification PASSED
tests/ingest/test_pipeline.py::test_html_200_body_is_failed_fetch_and_serves_previous PASSED
tests/ingest/test_pipeline.py::test_empty_body_is_failed_fetch PASSED
tests/ingest/test_pipeline.py::test_non_2xx_is_failed_fetch PASSED
tests/ingest/test_pipeline.py::test_truncated_json_is_failed_validation PASSED
tests/ingest/test_pipeline.py::test_series_without_rows_is_failed_validation PASSED
tests/ingest/test_pipeline.py::test_identical_payload_is_idempotent PASSED
tests/ingest/test_pipeline.py::test_identical_payload_after_failed_verification_is_reprocessed[failed-verification] PASSED
tests/ingest/test_pipeline.py::test_identical_payload_after_failed_verification_is_reprocessed[pending-verification] PASSED
tests/ingest/test_pipeline.py::test_identical_payload_after_failed_verification_is_reprocessed[failed-validation] PASSED
tests/ingest/test_pipeline.py::test_identical_payload_is_reprocessed_when_previous_verified_run_was_another_dataset PASSED
tests/ingest/test_pipeline.py::test_revision_creates_new_vintage_and_event PASSED
tests/ingest/test_pipeline.py::test_no_revision_event_against_unverified_data PASSED
tests/ingest/test_pipeline.py::test_midway_failure_commits_nothing PASSED
tests/ingest/test_pipeline.py::test_failure_inside_write_transaction_commits_nothing PASSED
tests/ingest/test_pipeline.py::test_bad_rows_are_quarantined_not_written PASSED
tests/ingest/test_pipeline.py::test_previously_verified_data_still_served_after_each_failure_kind[html_200|empty|http_500|truncated_json|http_raises] PASSED (5)
tests/ingest/test_pipeline.py::test_previously_verified_data_still_served_after_write_failure PASSED
tests/ingest/test_pipeline.py::test_each_fetch_gets_its_own_raw_fetch_row PASSED
tests/ingest/test_pipeline.py::test_paginated_dataset_writes_rows_from_every_page PASSED
tests/ingest/test_pipeline.py::test_dataset_key_is_order_independent PASSED
tests/ingest/test_pipeline.py::test_rejects_naive_clock_and_foreign_specs PASSED
============================== 26 passed in 6.67s ==============================
```

Mutation checks, to confirm the tests catch real bugs:

| Mutation | Test that failed |
|---|---|
| Removed the `prev state == verified` condition (Ruling D) | all 3 `test_identical_payload_after_failed_verification_is_reprocessed` cases |
| Replaced `db.transaction()` with a no-op context | `test_failure_inside_write_transaction_commits_nothing` (Review Focus 3) |
| Turned off HTML sniffing | `test_html_200_body_is_failed_fetch_and_serves_previous` (Review Focus 1) |

The original file was restored and the full suite passed again: 170 passed.

Review Focus coverage:
- **RF1:** `test_html_200...`, `test_empty_body...`, `test_truncated_json...`, and `test_previously_verified_data_still_served_after_each_failure_kind`.
- **RF2:** `test_identical_payload_is_idempotent`.
- **RF3:** `test_midway_failure_commits_nothing` and `test_failure_inside_write_transaction_commits_nothing`.
- **RF4:** `test_bad_rows_are_quarantined_not_written`.

## Concerns

1. **Observation provenance for paginated sources.** An observation's `raw_fetch_id` is the run's first response, as described above. Exact per-page attribution would change the Task 5 or Task 6 contract.
2. **Revisions on `value_text`.** A change in the publisher's formatting with the same numeric value is logged as a revision.
3. **GitNexus checks skipped.** CLAUDE.md asks for GitNexus impact checks before edits, but those tools were not available in this session. The existing symbols I touched are additive changes to `Db` and the migration-count assertion in `test_db.py`.
4. **Slow HTTP tests.** `tests/ingest/test_http.py` takes about 5 s, because the local server waits for the slow-handler threads when it shuts down. This is harmless.

---

# Fix round 1 (review findings I1, I2, P2)

Commits:
- `5d52ee6` ingest: per-page observation provenance, empty-series format_change (Ruling M), incremental fetch evidence
- `1d16e86` ingest: Source.fetch contract is Iterable[RawResponse]; document response_index

The previous "Decisions to confirm" and "Concerns" about first-row provenance and "zero raw rows means failed-validation" are replaced by the behaviour below.

## I1: per-page provenance

Each observation now links to the raw_fetch row of the page its row came from.

- **`RawRow`** has a new field, `response_index: int = 0`. It is checked in `__post_init__` and must be an int, not a bool, and at least 0. Otherwise it raises `TypeError`.
- **`Observation`** has a new field, `response_index: int = Field(0, ge=0, exclude=True)`. This is provenance only, so it is left out of `model_dump`. `Observation.from_raw` takes a `response_index=0` keyword.
- **`validate`** passes the row's index through to its observation. Duplicate detection is unchanged: periods are still counted across the whole payload, across all pages.
- **Db:** the signature is now `write_observations(run_id, rows: list[tuple[Observation, raw_fetch_id, fetched_at]])`. Each observation gets the `raw_fetch_id` and `fetched_at` of its own response.
- **Out-of-range index:** a `response_index` at or beyond the number of responses ends the run `failed-validation` with `event(format_change, {error})`.

Covering tests:
- `test_observation_links_to_the_raw_fetch_of_its_own_page`
- `test_duplicate_period_across_pages_is_still_rejected`
- `test_out_of_range_response_index_is_failed_validation`
- `test_rawrow_response_index_must_be_non_negative_int[-1|True|0|1.0]`
- `test_response_index_is_carried_to_observation_and_duplicates_span_pages`

Task 5's existing tests are unchanged and pass.

## I2: Ruling M

A series ends the run with zero valid observations when parse gave it no rows, or when every one of its rows was quarantined.

- **Some series empty:** each empty series gets one `event(format_change, {series_id, reason: 'no_valid_observations', n_raw_rows, n_quarantined})`, written in the same transaction as the run's observations. The run continues to `pending-verification`.
- **Every series empty:** the run ends `failed-validation`. The per-series events are written, and no observations or quarantine rows are.

The old test `test_series_without_rows_is_failed_validation` was replaced. Covering tests:
- `test_zero_row_series_emits_format_change_run_continues`
- `test_all_quarantined_series_emits_format_change_but_run_continues`. This one also checks that previously verified s2 data is still served.
- `test_run_fails_when_every_series_empty`

## P2: pages received before a failure are kept

- `Source.fetch` now returns `Iterable[RawResponse]`. Adapters should prefer a generator, and a plain list is still accepted.
- `run_dataset` reads the responses one at a time with `next()`. Each one is saved to the raw store, with its own raw_fetch row and its own `fetched_at`, as soon as it arrives.
- Only exceptions raised by the iterator are classified as `failed-fetch`. Errors from the raw store or the Db are not caught as fetch failures.
- `FakeSource.fetch` is now a generator that requests `http://fake/data/<page>`, and its `parse` sets `response_index`. `ListFakeSource` returns a plain list.

Covering tests:
- `test_midway_failure_keeps_received_pages_as_evidence`: page 1's raw file is on disk with the matching sha256, its raw_fetch row has ok=1, the run is `failed-fetch` and there are no observations.
- `test_fetch_returning_a_plain_list_still_works`
- `test_midway_failure_commits_nothing`, unchanged.

## RED evidence

I ran the current tests against HEAD's pre-fix `ingest/`, from a scratch copy:

```
26 failed, 41 passed
```

The failures include:
- `test_zero_row_series_emits_format_change_run_continues`
- `test_all_quarantined_series_emits_format_change_but_run_continues`
- `test_run_fails_when_every_series_empty`
- `test_midway_failure_keeps_received_pages_as_evidence`
- `test_observation_links_to_the_raw_fetch_of_its_own_page`
- `test_duplicate_period_across_pages_is_still_rejected`
- `test_fetch_returning_a_plain_list_still_works`
- `test_response_index_is_carried_to_observation_and_duplicates_span_pages`

Many of the other failures come from the shared fakes. The fakes now pass `response_index`, which the old `RawRow` rejects.

`test_out_of_range_response_index_is_failed_validation` passed on the old code for an unrelated reason: the old `RawRow` raised `TypeError` on the unknown keyword, so the run failed anyway.

## GREEN evidence

Command:

```
/home/joao/projects/prumo-pipeline/.venv-ci/bin/python -m pytest tests/ingest -v
```

Output (pipeline and new validate lines, plus the summary):

```
tests/ingest/test_pipeline.py::test_happy_path_pending_verification PASSED
tests/ingest/test_pipeline.py::test_html_200_body_is_failed_fetch_and_serves_previous PASSED
tests/ingest/test_pipeline.py::test_empty_body_is_failed_fetch PASSED
tests/ingest/test_pipeline.py::test_non_2xx_is_failed_fetch PASSED
tests/ingest/test_pipeline.py::test_truncated_json_is_failed_validation PASSED
tests/ingest/test_pipeline.py::test_zero_row_series_emits_format_change_run_continues PASSED
tests/ingest/test_pipeline.py::test_all_quarantined_series_emits_format_change_but_run_continues PASSED
tests/ingest/test_pipeline.py::test_run_fails_when_every_series_empty PASSED
tests/ingest/test_pipeline.py::test_identical_payload_is_idempotent PASSED
tests/ingest/test_pipeline.py::test_identical_payload_after_failed_verification_is_reprocessed[failed-verification] PASSED
tests/ingest/test_pipeline.py::test_identical_payload_after_failed_verification_is_reprocessed[pending-verification] PASSED
tests/ingest/test_pipeline.py::test_identical_payload_after_failed_verification_is_reprocessed[failed-validation] PASSED
tests/ingest/test_pipeline.py::test_identical_payload_is_reprocessed_when_previous_verified_run_was_another_dataset PASSED
tests/ingest/test_pipeline.py::test_revision_creates_new_vintage_and_event PASSED
tests/ingest/test_pipeline.py::test_no_revision_event_against_unverified_data PASSED
tests/ingest/test_pipeline.py::test_midway_failure_commits_nothing PASSED
tests/ingest/test_pipeline.py::test_midway_failure_keeps_received_pages_as_evidence PASSED
tests/ingest/test_pipeline.py::test_failure_inside_write_transaction_commits_nothing PASSED
tests/ingest/test_pipeline.py::test_bad_rows_are_quarantined_not_written PASSED
tests/ingest/test_pipeline.py::test_previously_verified_data_still_served_after_each_failure_kind[html_200] PASSED
tests/ingest/test_pipeline.py::test_previously_verified_data_still_served_after_each_failure_kind[empty] PASSED
tests/ingest/test_pipeline.py::test_previously_verified_data_still_served_after_each_failure_kind[http_500] PASSED
tests/ingest/test_pipeline.py::test_previously_verified_data_still_served_after_each_failure_kind[truncated_json] PASSED
tests/ingest/test_pipeline.py::test_previously_verified_data_still_served_after_each_failure_kind[http_raises] PASSED
tests/ingest/test_pipeline.py::test_previously_verified_data_still_served_after_write_failure PASSED
tests/ingest/test_pipeline.py::test_each_fetch_gets_its_own_raw_fetch_row PASSED
tests/ingest/test_pipeline.py::test_paginated_dataset_writes_rows_from_every_page PASSED
tests/ingest/test_pipeline.py::test_dataset_key_is_order_independent PASSED
tests/ingest/test_pipeline.py::test_rejects_naive_clock_and_foreign_specs PASSED
tests/ingest/test_pipeline.py::test_observation_links_to_the_raw_fetch_of_its_own_page PASSED
tests/ingest/test_pipeline.py::test_duplicate_period_across_pages_is_still_rejected PASSED
tests/ingest/test_pipeline.py::test_out_of_range_response_index_is_failed_validation PASSED
tests/ingest/test_pipeline.py::test_fetch_returning_a_plain_list_still_works PASSED
tests/ingest/test_validate.py::test_rawrow_response_index_must_be_non_negative_int[-1] PASSED
tests/ingest/test_validate.py::test_rawrow_response_index_must_be_non_negative_int[True] PASSED
tests/ingest/test_validate.py::test_rawrow_response_index_must_be_non_negative_int[0] PASSED
tests/ingest/test_validate.py::test_rawrow_response_index_must_be_non_negative_int[1.0] PASSED
tests/ingest/test_validate.py::test_response_index_is_carried_to_observation_and_duplicates_span_pages PASSED
============================= 182 passed in 13.72s =============================
```

After commit `1d16e86`, `tests/ingest -q` gives `182 passed in 13.32s`.
