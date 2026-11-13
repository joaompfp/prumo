### Task 7: Verification framework (independent sampling, 100% rule)

**Files:** Create `ingest/verify.py`, `ingest/verifiers/__init__.py`, `tests/ingest/test_verify.py`

**Interfaces:**
- Produces: `Verifier` protocol: `source_name: str`; `check(items: list[SampleItem], http) -> list[ItemResult]` where `SampleItem(series_id, period, expected_text, spec)` and `ItemResult(observed_text: str | None, evidence_url: str)`. `verify.draw_sample(db, run_id, seed: int, size: int) -> list[SampleItem]` (stratified by series, then by recency: at least the latest period of every series is included, rest random); `verify.verify_run(db, run_id, verifier, http, seed: int | None = None, size: int = 50) -> bool`; `verify.run_with_refetch(db, store, source, verifier, specs, http, max_attempts: int = 3) -> DatasetRunResult` — on any mismatch (or `observed_text is None`) marks the run `failed-verification`, writes `verification` + `verification_item` rows (seed, evidence) and `event(verification_failure)`, then re-runs the dataset with a **new** seed; after `max_attempts` leaves it unserved and returns `failed-verification`. Passing runs are set `verified`. A verifier whose module imports the source's parse module is rejected at registration (`register_verifier` raises `ValueError`).

- [ ] **Step 1: Failing tests:** `test_all_match_marks_verified`; `test_single_mismatch_marks_failed_and_not_served` (RF5); `test_none_observed_counts_as_mismatch`; `test_sample_always_includes_latest_period_of_each_series`; `test_sample_is_reproducible_from_seed`; `test_refetch_uses_new_seed_each_attempt`; `test_gives_up_after_max_attempts_and_stays_unserved`; `test_verifier_importing_parser_is_rejected` (RF5); `test_verification_items_store_evidence_url`.
- [ ] **Step 2–4:** FAIL → implement → PASS. **Step 5: Commit.**

---

