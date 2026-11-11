### Task 6: Pipeline core (one dataset, one transaction)

**Files:** Create `ingest/pipeline.py`, `ingest/sources/__init__.py` (protocol), `tests/ingest/test_pipeline.py`, `tests/ingest/fakes.py`

**Interfaces:**
- Consumes: Tasks 2–5.
- Produces: `Source` protocol in `ingest/sources/__init__.py`: `name: str`; `fetch(specs: list[SeriesSpec], http) -> list[RawResponse]` (`RawResponse(url, params, status, body: bytes)`); `parse(specs: list[SeriesSpec], responses: list[RawResponse]) -> dict[str, list[RawRow]]` (keyed by `series_id`; `RawRow` from Task 5; `run_dataset` passes each list to `validate`). `pipeline.run_dataset(db: Db, store: RawStore, source: Source, specs: list[SeriesSpec], http, now: Callable[[], datetime]) -> DatasetRunResult(state, run_id, n_written, n_quarantined)`. Behaviour: opens `dataset_run` (`running`); saves every response to the raw store and `raw_fetch`; a non-2xx status, empty body or parse error → state `failed-fetch`/`failed-validation`, `event(fetch_failure|format_change)`, **no observations written**; otherwise one transaction writes observations + quarantine, state `pending-verification`. An observation whose `(series, period)` exists with a different value from an earlier verified run emits `event(revision)` and is stored as a new vintage; identical sha256 to the previous successful fetch → no new rows (state `verified` unchanged, event none).

- [ ] **Step 1: Failing tests** with a `FakeSource` and a `FakeHttp`: `test_happy_path_pending_verification`; `test_html_200_body_is_failed_fetch_and_serves_previous` (RF1); `test_empty_body_is_failed_fetch`; `test_truncated_json_is_failed_validation`; `test_identical_payload_is_idempotent` (RF2); `test_revision_creates_new_vintage_and_event`; `test_midway_failure_commits_nothing` (FakeHttp raises on page 2 → zero observation rows, run state `failed-fetch`) (RF3); `test_bad_rows_are_quarantined_not_written` (RF4).
- [ ] **Step 2–4:** FAIL → implement → PASS. **Step 5: Commit.**

---

