# Task 7 report: Verification framework (independent sampling, 100% rule)

Status: DONE_WITH_CONCERNS (see Concerns: three small interface additions)

## Commits (branch `pipeline-rebuild`, worktree /home/joao/projects/prumo-pipeline)
- `cc71d21` ingest: verifier contract, exact parse_decimal, seeded stratified draw_sample
- `795445f` ingest: verify_run (100% exact-decimal rule) and run_with_refetch with fresh seeds
- `39b31de` ingest: register_verifier rejects verifiers that import the collector's parser

Tests were green after each commit. Final: `.venv-ci/bin/python -m pytest tests/ingest -q` -> **230 passed** (`tests/` -> 234 passed).

## What was done
- **Refactor first** (models.py): pulled the strict number-cleaning logic out into `_canonical_number`. `parse_number` (float) and the new `parse_decimal` (exact `Decimal`) now share it, so both follow the same rules. The suite stayed green after the refactor (182 passed) before any new behaviour went in.
- `ingest/verifiers/__init__.py`: `SampleItem`, `ItemResult`, `Verifier` protocol, `register_verifier`, `get_verifier`.
- `ingest/verify.py`: `draw_sample`, `verify_run`, `run_with_refetch`. It does not import sqlite3, and the only use of float is a type guard that rejects float results.
- `ingest/db.py`: `observations_of_run`, `add_verification`, `add_verification_item`.
- `ingest/migrations/0003_verification_replay.sql`: adds `verification_item.observed_decimal` (CHECK '.' or ','), `observed_unit`, `observed_flag`, `note`.
- `tests/ingest/fakes.py`: adds `FakeVerifier` (scripted truths per call, echoes key, records calls, optional raise) and `truth_of`.
- `tests/ingest/test_verify.py` (48 tests), plus one `parse_decimal` test in `test_models.py`.

## Public interfaces (exact)
```python
# ingest/verifiers/__init__.py
@dataclass(frozen=True)
class SampleItem:
    series_id: str; period: str; expected_text: str; spec: SeriesSpec
    expected_unit: str; expected_flag: str | None
@dataclass(frozen=True)
class ItemResult:
    observed_text: str | None; evidence_url: str
    observed_decimal: Literal[".", ","] = "."
    observed_unit: str | None = None; observed_flag: str | None = None
    series_id: str | None = None; period: str | None = None   # ADDED (see decisions)
class Verifier(Protocol):
    source_name: str
    def check(self, items: list[SampleItem], http: Http) -> list[ItemResult]: ...
def register_verifier(verifier: Verifier) -> None
def get_verifier(source_name: str) -> Verifier          # KeyError if none (ADDED)

# ingest/models.py
def parse_decimal(text: str, decimal: str = ".") -> Decimal

# ingest/verify.py
def draw_sample(db, run_id: int, seed: int, size: int, *, specs: list[SeriesSpec]) -> list[SampleItem]
def verify_run(db, run_id: int, verifier, http, seed: int | None = None, size: int = 50, *,
               specs: list[SeriesSpec], now: Callable[[], datetime] = _utc_now) -> bool
def run_with_refetch(db, store, source, verifier, specs, http, max_attempts: int = 3,
                     size: int = 50, now=None) -> DatasetRunResult

# ingest/db.py
Db.observations_of_run(run_id) -> list[(series_id, period, value_text, status_flag)]  # ordered
Db.add_verification(run_id, seed, sample_size, passed, created_at) -> int
Db.add_verification_item(verification_id, *, series_id, period, expected_text, observed_text,
                         evidence_url, match, observed_decimal, observed_unit, observed_flag, note)
```

## Behaviour
- **Sampling**: sorted by (series_id, period, id). Every series always contributes its latest period. If there are more series than `size`, the sample grows to one item per series. The rest of the sample is `random.Random(seed).sample(...)` over the remaining observations, without replacement. The output is sorted, so the same db + seed + size gives the same list. `size < 1` or a series with no spec raises ValueError.
- **Comparison** (`_mismatch`, applied in this order):
  - The echoed key, if present, must equal the item's key.
  - `observed_text` must not be None and must be a `str`.
  - `observed_decimal` must be '.' or ','.
  - Values are compared as exact `Decimal`s. Expected is parsed with `spec.decimal`, observed with `observed_decimal`. There is no tolerance.
  - The unit is compared after strip, only if it was observed.
  - The flag is compared only if it was observed; blank and None count as equal.
  - Any exception during comparison counts as a mismatch with a note.
- **verify_run**:
  - Raises ValueError unless the run is `pending-verification`, or if the specs' source differs from `verifier.source_name`. Nothing is written in either case.
  - The seed is `secrets.randbits(63)` when None, and it is always stored.
  - If the verifier raises, or returns the wrong number of results, every item is marked as a mismatch with a note. The run is never left pending.
  - An empty sample cannot pass (`passed = bool(items) and not bad`).
  - One transaction writes: the `verification` row (with the actual sample size), the items, the `verification_failure` event (`{run_id, seed, n_items, n_mismatch, first_mismatches[:5]}`) and the state.
  - Non-str fields in a result are stored as NULL, so they cannot crash the STRICT insert.
- **run_with_refetch**:
  - Any state other than `pending-verification` is returned as-is. This covers failed-fetch, failed-validation and the short-circuit `verified` run.
  - Each attempt calls `verify_run` with a fresh seed.
  - On a failure that is not the last attempt, it emits `event(refetch, {failed_run_id, next_attempt, max_attempts})` and starts a new `run_dataset`.
  - After `max_attempts` it returns `failed-verification`.
  - It raises ValueError if `max_attempts < 1` or if the verifier and source names differ.
- **Registration**: the verifier's class module is parsed with `ast.walk` (nested imports included, relative imports resolved). It is rejected if it imports:
  - any `ingest.sources.<x>`;
  - `from ingest.sources import X` where X is not a plain non-module attribute of the package;
  - any dotted name with a component equal to `source_name` (except under `ingest.verifiers`).

  Registering the same source twice raises ValueError. A module with no source file is rejected.

## RED / GREEN evidence
Commit 1 RED:
```
tests/ingest/test_verify.py:9: in <module>
    from ingest.verify import draw_sample
E   ModuleNotFoundError: No module named 'ingest.verify'
ERROR tests/ingest/test_verify.py
```
GREEN: `tests/ingest/test_verify.py ..... test_models.py ... 70 passed`; full: `188 passed in 14.60s`.
(Honest note: the `parse_decimal` test went in together with the refactor that created the function, so it never had a separate RED.)

Commit 2 RED: `ERROR tests/ingest/test_verify.py ... 1 error during collection` (ImportError: verify_run / run_with_refetch).
GREEN: `tests/ingest/test_verify.py ............................... 31 passed`.
Then a hardening RED:
```
test_malformed_result_fields_are_failure_not_crash
E   AttributeError: 'int' object has no attribute 'strip'
1 failed, 31 passed
```
GREEN: `215 passed in 22.39s`.

Commit 3 RED: `1 failed, 32 passed, 14 errors` (no `_REGISTRY` / `register_verifier`).
The first implementation failed only in the full run: temp module names collided in `sys.modules` across tests. Fixed with uuid module names, giving `230 passed in 22.87s`. `tests/` gives `234 passed`.

## Decisions (beyond the brief)
1. **`specs` is a required keyword-only argument of `draw_sample` and `verify_run`.** `SampleItem.spec` needs the full SeriesSpec, and `spec.decimal` is needed for the exact comparison. Neither is stored in SQL (sync_registry drops decimal/schedule/throttle). `run_with_refetch` passes its own specs.
2. **`now` is a keyword argument of `verify_run`** (default UTC now) so timestamps are testable. It reuses `ingest.pipeline._iso` and `_utc_now`, which are private imports.
3. **`ItemResult.series_id` / `period` are optional echo fields.** Without them, results returned "out of order" could not be detected. When they are set they must equal the item's key, otherwise the item is a mismatch. FakeVerifier echoes them. Adapters SHOULD always set them.
4. **Migration 0003** stores `observed_decimal`, `observed_unit`, `observed_flag` and `note` per item. Without `observed_decimal`, an auditor cannot replay a comparison like "1,1" vs "1.10". `note` holds the item-level failure reason.
5. **`get_verifier(source_name)`** was added; without it the registry cannot be used.
6. **Extra guards:** `verify_run` and `run_with_refetch` reject a verifier for another source, and `run_with_refetch` rejects `max_attempts < 1`.
7. The `verification.sample_size` column stores the actual number of items, which can be larger than `size`.

## Concerns
- Decisions 1 and 3 change the plan's signatures. The source-adapter tasks (9-16) should set `series_id`/`period` on every ItemResult, and callers must pass `specs=`. The controller may prefer to make the echo fields required.
- If the DB itself fails while writing a verification, the exception propagates and the run stays `pending-verification`. That failure is loud, not silent, and pending runs are not served. I did not add a best-effort fallback.
- The import rule checks only the verifier's own module. Transitive imports and `importlib.import_module` are not caught; this is documented in the docstring.
- The name-component rule could give a false positive if a source name is a common word, e.g. `"http"`. No real source names look like that today.
- Pre-existing (Task 6): with `-W error`, 2 tests in `test_pipeline.py` raise ResourceWarning for unclosed raw-file reads. That is the 1 warning in `pytest tests/`. My new tests pass with `-W error`.
- The CLAUDE.md GitNexus impact / detect_changes steps could not be run because the GitNexus MCP tools are not available in this session. The only existing symbols changed are `parse_number` (behaviour-preserving refactor) and `Db` (additive methods).

---

# Fix round 1 (review findings I1-I6)

Commits: `a938395` (migration 0004 only; checked green on its own in a detached worktree: 230 passed), `3a2dee8` (all code and tests). Final: **256 passed** (`tests/ingest`), including 73 in `test_verify.py`.

## What changed, per finding, with the tests that cover it

**I1. Concurrent verify_run.** The state change is now `Db.transition_run_state(run_id, 'pending-verification', new)`, a compare-and-set `UPDATE ... WHERE id=? AND state=?` run inside the same transaction as the verification row, the items and the event. If no row is updated, the transaction raises `VerificationConflict(ValueError)` and everything from this verification is rolled back.
Test: `test_concurrent_verify_loser_is_rolled_back[inner fails | inner passes]`. Two connections to the same file reproduce the probe-8 interleaving. The loser gets VerificationConflict, exactly one `verification` row with 3 items remains, the final state and failure events match the winner, and what is served matches.

**I2. Ruling N.** `ItemResult(series_id: str, period: str, observed_text, evidence_url, observed_decimal='.', observed_unit=None, observed_flag=None, evidence=None)`. The key fields come first and are required. Each result is always compared with the item at the same position. Any difference is a per-item failure with a note, whether it is a different key, a different order, a duplicate, a malformed result or a wrong count.
Tests: `test_out_of_order_result_is_failure`, `test_duplicate_key_result_is_failure`, `test_wrong_result_count_is_failure` (short and doubled), `test_parser_swapped_periods_with_reordered_verifier_fails` (probe 2: fails on order; an honest, ordered verifier fails on value), `test_malformed_result_fields_are_failure_not_crash`.

**I3. Ruling O (blinded items).** `Verifier.check(items: list[BlindItem], http)` with `BlindItem(series_id, period, spec)` (frozen). `SampleItem` (which holds the expected fields) now lives in `ingest/verify.py`, and `SampleItem.blind()` makes the view the verifier gets.
Tests: `test_verifier_gets_blinded_items` checks that the item type is BlindItem, that `expected_text`/`expected_unit`/`expected_flag` raise AttributeError, that the attributes cannot be set, and that a verifier which tries to read them fails verification. `test_echoing_what_it_is_given_cannot_pass` covers probe 1.

**I4. Registered verifier only.** `run_with_refetch` raises ValueError unless `get_verifier(source.name) is verifier`, and does so before any run starts. `FakeVerifier` moved to its own module, `tests/ingest/fake_verifier.py`, which satisfies the rule. An autouse fixture empties the registry for each test.
Tests: `test_refetch_requires_the_registered_verifier` (not registered / another instance registered; no dataset_run created), `test_fake_verifier_module_passes_the_rule`; every run_with_refetch test registers its verifier.

**I5. Ruling Q.** `register_verifier` now runs two checks.
- (a) It AST-scans the verifier's module and rejects any of these: bare `import ingest` or `import ingest.sources`; `from ingest import sources` or `*`; `ingest.sources.<x>`; from `ingest.sources`, any name other than `Source` and `RawResponse`; any import whose dotted name has a component equal to the source name, compared case-insensitively (`ingest.verifiers.*` is exempt); any import or use of `importlib`, `__import__`, `exec` or `eval`; and `sys.modules` (either the attribute or `from sys import modules`).
- (b) A transitive shared-code check, done by reading files under `_INGEST_ROOT` and never executing them. It computes the closure of `ingest.*` modules reachable from the verifier's module and from `ingest/sources/<source_name>.py` (when that file exists). Descent stops at `SHARED_ALLOWED = {ingest, ingest.models, ingest.http, ingest.sources, ingest.verifiers, ingest.rawstore}`. It rejects any module the two closures share outside that set. I added the root `ingest` (an empty `__init__`) to the allow-list because both sides necessarily import it.
Tests: `test_verifier_importing_parser_is_rejected` (21 cases, covering the review table: `importlib.import_module`, `from importlib import`, `__import__`, `from ingest import sources [as s]`, `import ingest.sources`, `import ingest`, `exec`, `eval`, `sys.modules`, `from sys import modules`, `import ACME`, `from vendor.Acme import`, ...), `test_independent_verifier_is_registered` (5 allowed shapes), `test_shared_helper_with_parser_is_rejected` (direct helper, `from ingest import helper`, and a transitive path through `ingest.wrapper`), `test_only_allow_listed_shared_modules_is_accepted`. The transitive tests use a throwaway source tree in tmp_path via `monkeypatch.setattr(verifiers, "_INGEST_ROOT", ...)`. The docstring documents the limits.

**I6. Ruling R (replay).** A new migration `0004_verification_audit.sql` adds `expected_decimal`, `expected_unit`, `expected_flag` and `evidence_sha256`. It also adds two columns beyond the ruling, `observed_series_id` and `observed_period`: the key the verifier answered for. Without them, a key or order mismatch could not be replayed to the same result. `ItemResult.evidence: bytes | None`. `verify_run(..., store: RawStore | None = None)` saves evidence with `store.save(f"verify-{source}", evidence)` and records the sha. It raises ValueError if evidence comes back and `store` is None; `run_with_refetch` passes its store. `replay_item(db, store, verification_item_id) -> bool` decides the item again from stored fields only, using the same `_row_mismatch` that verify_run uses: verify_run first builds the exact row it stores, then decides it, so the two cannot disagree. If evidence was kept, its file is loaded and integrity-checked.
Tests: `test_evidence_bytes_saved_and_items_replayable` (sha and file contents, expected_decimal/unit/flag, replay matches), `test_replay_needs_no_registry_and_reproduces_every_outcome` (6 verifier behaviours: pass, not found, unit, raise, order, ',' decimal mismatch; every item replays to its stored match), `test_replay_detects_tampered_evidence` (RawIntegrityError), `test_evidence_without_store_is_refused`.

Db additions: `add_verification_item(verification_id, item: dict)` (now takes a dict of the 16 item columns; keys are checked), `verification_item(item_id) -> dict`, `verification_item_source(item_id) -> str`, `transition_run_state(run_id, from_state, to_state) -> bool`.

## Evidence

RED: the reviewer's probes against the pre-fix code (39b31de):
```
$ .venv-ci/bin/python /tmp/t7probe/probe1.py
1 echo passes: True [('s1', '2024', '999'), ('s2', '2024', '1')]
2 swapped periods pass w/o echo: True [('s1', '2023', '2.0'), ('s1', '2024', '1.5'), ('s2', '2024', '10')]
3 '' . False
3 '   ' . False
3 '1,5' . False
3 '1.500' , False
3 '1,500' . False
4 extra: False
4b None return: False failed-verification
4c dict results: False
5 size0: ValueError('sample size must be >= 1, got 0') pending-verification
6 empty run: DatasetRunResult(state='failed-validation', run_id=1, n_written=0, n_quarantined=0)
7 dbfail: disk pending-verification (0,) (0,)
8 concurrent: True verified [(0,), (1,)] [('s1', '2024', '1.5'), ('s2', '2024', '10')]
$ .venv-ci/bin/python /tmp/t7probe/probe2.py
importlib                           ACCEPTED (bypass)
dunder                              ACCEPTED (bypass)
from ingest import sources          ACCEPTED (bypass)
from ingest import sources as s     ACCEPTED (bypass)
import ingest.sources; attr         ACCEPTED (bypass)
import ingest; attr                 ACCEPTED (bypass)
as alias                            rejected
transitive helper                   ACCEPTED (bypass)
exec                                ACCEPTED (bypass)
sys.modules                         ACCEPTED (bypass)
case EUROSTAT/acme upper            ACCEPTED (bypass)
```
RED: the new test file against the pre-fix code (detached worktree at 39b31de):
```
    from ingest.verifiers import BlindItem, ItemResult, get_verifier, register_verifier
E   ImportError: cannot import name 'BlindItem' from 'ingest.verifiers' (/tmp/claude-1000/-home-joao/0cf85576-cadd-4c92-a5b2-4aac697971e6/scratchpad/t7old/ingest/verifiers/__init__.py)
=========================== short test summary info ============================
ERROR tests/ingest/test_verify.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
=============================== 1 error in 0.47s ===============================
```
GREEN: probe2 unchanged, plus probe1 scenarios 1/2/8 adapted to the new API (scratchpad copy, not committed):
```
$ .venv-ci/bin/python /tmp/t7probe/probe2.py
importlib                           rejected
dunder                              rejected
from ingest import sources          rejected
from ingest import sources as s     rejected
import ingest.sources; attr         rejected
import ingest; attr                 rejected
as alias                            rejected
transitive helper                   ACCEPTED (bypass)
exec                                rejected
sys.modules                         rejected
case EUROSTAT/acme upper            rejected
$ .venv-ci/bin/python probe1_adapted.py
1 echo passes: False []
2 swapped periods + reordered verifier: False []
8 concurrent: VerificationConflict: run 1 is no longer pending-verification (now 'failed-verification'); this verification was rolled back
  state: failed-verification verification.passed: [(0,)] served: []
```
("transitive helper" is still accepted. The probe imports `helper_reexports`, a top-level, non-`ingest` module that does not exist. Ruling Q(b) follows only `ingest.*` modules; see Concerns.)

GREEN: `/home/joao/projects/prumo-pipeline/.venv-ci/bin/python -m pytest tests/ingest -v` (test_verify.py part and total):
```
tests/ingest/test_verify.py::test_sample_always_includes_latest_period_of_each_series PASSED [ 71%]
tests/ingest/test_verify.py::test_sample_is_reproducible_from_seed PASSED [ 72%]
tests/ingest/test_verify.py::test_sample_covers_every_series_even_when_size_smaller PASSED [ 72%]
tests/ingest/test_verify.py::test_sample_takes_every_observation_when_size_exceeds_run PASSED [ 73%]
tests/ingest/test_verify.py::test_sample_rejects_unknown_series_and_bad_size PASSED [ 73%]
tests/ingest/test_verify.py::test_all_match_marks_verified PASSED        [ 73%]
tests/ingest/test_verify.py::test_single_mismatch_marks_failed_and_not_served PASSED [ 74%]
tests/ingest/test_verify.py::test_none_observed_counts_as_mismatch PASSED [ 74%]
tests/ingest/test_verify.py::test_verification_items_store_evidence_url PASSED [ 75%]
tests/ingest/test_verify.py::test_decimal_comparison_is_exact_not_float[1.10-1,1-,-True] PASSED [ 75%]
tests/ingest/test_verify.py::test_decimal_comparison_is_exact_not_float[1.10-1.1-.-True] PASSED [ 75%]
tests/ingest/test_verify.py::test_decimal_comparison_is_exact_not_float[1 234.5-1.234,50-,-True] PASSED [ 76%]
tests/ingest/test_verify.py::test_decimal_comparison_is_exact_not_float[1.10-1.1000001-.-False] PASSED [ 76%]
tests/ingest/test_verify.py::test_decimal_comparison_is_exact_not_float[0.30000000000000004-0.3-.-False] PASSED [ 76%]
tests/ingest/test_verify.py::test_decimal_comparison_is_exact_not_float[1.10-1,1-.-False] PASSED [ 77%]
tests/ingest/test_verify.py::test_decimal_comparison_is_exact_not_float[1.10-n/d-.-False] PASSED [ 77%]
tests/ingest/test_verify.py::test_unit_or_flag_mismatch_fails[kw0-True] PASSED [ 78%]
tests/ingest/test_verify.py::test_unit_or_flag_mismatch_fails[kw1-True] PASSED [ 78%]
tests/ingest/test_verify.py::test_unit_or_flag_mismatch_fails[kw2-False] PASSED [ 78%]
tests/ingest/test_verify.py::test_unit_or_flag_mismatch_fails[kw3-False] PASSED [ 79%]
tests/ingest/test_verify.py::test_unit_or_flag_mismatch_fails[kw4-True] PASSED [ 79%]
tests/ingest/test_verify.py::test_verifier_exception_is_failure_not_pass PASSED [ 80%]
tests/ingest/test_verify.py::test_wrong_result_count_is_failure PASSED   [ 80%]
tests/ingest/test_verify.py::test_out_of_order_result_is_failure PASSED  [ 80%]
tests/ingest/test_verify.py::test_duplicate_key_result_is_failure PASSED [ 81%]
tests/ingest/test_verify.py::test_parser_swapped_periods_with_reordered_verifier_fails PASSED [ 81%]
tests/ingest/test_verify.py::test_verifier_gets_blinded_items PASSED     [ 82%]
tests/ingest/test_verify.py::test_echoing_what_it_is_given_cannot_pass PASSED [ 82%]
tests/ingest/test_verify.py::test_refuses_to_verify_non_pending_run PASSED [ 82%]
tests/ingest/test_verify.py::test_random_seed_is_stored_when_not_given PASSED [ 83%]
tests/ingest/test_verify.py::test_malformed_result_fields_are_failure_not_crash PASSED [ 83%]
tests/ingest/test_verify.py::test_concurrent_verify_loser_is_rolled_back[inner_truth0-failed-verification] PASSED [ 83%]
tests/ingest/test_verify.py::test_concurrent_verify_loser_is_rolled_back[inner_truth1-verified] PASSED [ 84%]
tests/ingest/test_verify.py::test_evidence_bytes_saved_and_items_replayable PASSED [ 84%]
tests/ingest/test_verify.py::test_replay_needs_no_registry_and_reproduces_every_outcome PASSED [ 85%]
tests/ingest/test_verify.py::test_replay_detects_tampered_evidence PASSED [ 85%]
tests/ingest/test_verify.py::test_evidence_without_store_is_refused PASSED [ 85%]
tests/ingest/test_verify.py::test_refetch_uses_new_seed_each_attempt PASSED [ 86%]
tests/ingest/test_verify.py::test_gives_up_after_max_attempts_and_stays_unserved PASSED [ 86%]
tests/ingest/test_verify.py::test_previously_verified_data_still_served_after_failed_verification PASSED [ 87%]
tests/ingest/test_verify.py::test_short_circuit_run_gets_no_verification_row PASSED [ 87%]
tests/ingest/test_verify.py::test_failed_fetch_is_returned_without_verification PASSED [ 87%]
tests/ingest/test_verify.py::test_refetch_requires_the_registered_verifier PASSED [ 88%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import ingest.sources.acme] PASSED [ 88%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from ingest.sources.acme import parse] PASSED [ 89%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from ingest.sources import acme] PASSED [ 89%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from ingest.sources import eurostat] PASSED [ 89%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import ingest.sources.eurostat as e] PASSED [ 90%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from ingest.sources import validate_helper] PASSED [ 90%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import importlib\nP = importlib.import_module('ingest.sources.acme')] PASSED [ 91%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from importlib import import_module] PASSED [ 91%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[P = __import__('ingest.sources.acme')] PASSED [ 91%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from ingest import sources\nP = sources.acme] PASSED [ 92%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from ingest import sources as s] PASSED [ 92%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import ingest.sources\nP = ingest.sources.acme] PASSED [ 92%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import ingest\nP = ingest.sources.acme] PASSED [ 93%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[exec('from ingest.sources.acme import parse')] PASSED [ 93%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[eval('1')] PASSED [ 94%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import sys\nP = sys.modules['ingest.sources.acme']] PASSED [ 94%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from sys import modules] PASSED [ 94%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import ACME] PASSED [ 95%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import acme] PASSED [ 95%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from vendor.Acme import parse] PASSED [ 96%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from vendor import acme] PASSED [ 96%]
tests/ingest/test_verify.py::test_independent_verifier_is_registered[] PASSED [ 96%]
tests/ingest/test_verify.py::test_independent_verifier_is_registered[from ingest.sources import RawResponse, Source] PASSED [ 97%]
tests/ingest/test_verify.py::test_independent_verifier_is_registered[from ingest.http import Http\nfrom ingest.models import parse_decimal\nimport json] PASSED [ 97%]
tests/ingest/test_verify.py::test_independent_verifier_is_registered[from ingest.verifiers import ItemResult, BlindItem] PASSED [ 98%]
tests/ingest/test_verify.py::test_independent_verifier_is_registered[import ingest.rawstore] PASSED [ 98%]
tests/ingest/test_verify.py::test_shared_helper_with_parser_is_rejected PASSED [ 98%]
tests/ingest/test_verify.py::test_only_allow_listed_shared_modules_is_accepted PASSED [ 99%]
tests/ingest/test_verify.py::test_duplicate_registration_is_rejected PASSED [ 99%]
tests/ingest/test_verify.py::test_fake_verifier_module_passes_the_rule PASSED [100%]
============================= 256 passed in 27.41s =============================
```

## Concerns (round 1)
- I5 follows only `ingest.*` modules (per the ruling). A non-`ingest` local helper shared by parser and verifier, like the probe's `helper_reexports`, is not followed; the per-adapter subprocess independence test has to cover it. Dynamic access such as `getattr(some_module, "x")` is not detected either.
- From `ingest.sources` only `Source`/`RawResponse` are importable, which is the strict reading of the ruling.
- `BlindItem.spec` still carries the registry's declared `unit`, as the ruling's shape requires; the stored unit is not exposed.
- 0004 adds `observed_series_id`/`observed_period`, two columns beyond the ruling's four. Without them a key or order failure could not be replayed.
- `verify_run` raises ValueError (and the run stays pending) when evidence comes back with `store=None`, as ruled. This is a loud caller error; `run_with_refetch` always passes a store.
- `BlindItem` is frozen but not `slots`: on 3.12, `slots=True` + `frozen=True` raises TypeError instead of FrozenInstanceError on setattr. Reading the expected attributes raises AttributeError, as required.

---

# Fix round 2 (I5 still open, plus two hardening items)

Commit: `a4bc4e1`. Final: **295 passed** (`tests/ingest`), including 112 in `test_verify.py`, which is also clean under `-W error`.

## What changed
**I5 (Ruling Q), `ingest/verifiers/__init__.py` `_direct_violations`.** The rules are rewritten, and each violation message names its rule:
1. **`plain import binds 'ingest'`**: every `import ingest` / `import ingest.<x>` statement is rejected, aliased or not, so the name `ingest` is never bound. **`name binds 'ingest'`**: `from <x> import ingest` is rejected. Importing from the package must take the form `from ingest.<module> import <names>`. `from ingest import <module>` stays allowed except for `sources`, `db` and `*`; the probe lists it as a non-bypass positive.
2. **`attribute access to collector`** (defence in depth): any attribute chain whose root name, resolved through the module's import aliases (an unbound `ingest` is taken literally), gives `ingest.sources.<x>` with `<x>` not `Source`/`RawResponse`, or gives `ingest.sources` itself. This catches `.sources` on any name bound to the ingest package, e.g. `from ingest.verifiers import ingest as i; i.sources`.
3. **`dynamic import/DB access`**: any import of, import of a name equal to, or attribute chain resolving to the modules `importlib`, `builtins`, `runpy`, `pkgutil`, `sys`, `sqlite3` or `ingest.db`, in any alias form (`import sys as s`, `from sys import modules`, `from ingest.verifiers import sys`, `from ingest import db`). **`dynamic code`**: the names `__import__`, `exec`, `eval`, `compile`, `vars`, `globals`, `locals`, `__builtins__`, and the attributes `.__import__` / `.__builtins__`. `open` and `re.compile` (an attribute) are allowed.
4. Unchanged: **`collector import`** (`from ingest.sources import <submodule>|*`, `from ingest import sources`), **`source-named import`** (case-insensitive), the duplicate rejection, and the transitive shared-module check with its allow-list.
5. The docstring now lists what is still undetectable (non-`ingest` helper modules; code built at runtime beyond the denylist) and says each adapter task carries a subprocess independence test.

**Hardening (a), `verify.py`.** `_str` now requires `type(x) is str`. A result that is not exactly `ItemResult`, or whose evidence is not exactly `bytes`, is malformed. Any verifier-supplied text field (`series_id`, `period`, `observed_text`, `evidence_url`, `observed_decimal`, `observed_unit`, `observed_flag`) that is not None and not exactly `str` fails the item with the note `result fields must be exact str: <field>: <type>`, and is stored as NULL.

**Hardening (b), `verify.py`.** `replay_item` raises `ValueError("verification_item N is a legacy item (pre-0004): its comparison fields were not stored, cannot replay")` when `expected_decimal` is NULL (new code always sets it from `spec.decimal`).

## Covering tests (tests/ingest/test_verify.py)
- `test_registration_bypasses_are_rejected[...]`, 33 cases. Each asserts ValueError from `register_verifier` and that the message contains the rule. The cases cover every bypass from the re-review: `import ingest.http` + `ingest.sources.acme.parse_rows`, `import ingest.models`, `import ingest.rawstore`, `import ingest.http as h`, `import ingest`, `from ingest.verifiers import ingest as i` (+ `i.sources`), an attribute chain with no import, `import sys as s; s.modules`, `from sys import modules`, `from ingest.verifiers import sys`, `builtins.__import__`, `from builtins import __import__ as imp`, `runpy`, `pkgutil.resolve_name`, `importlib`, `from importlib import import_module`, `__import__`, `.__import__`, `vars(ingest)`, `globals()['__builtins__']`, `locals()`, `__builtins__`, `exec`, `eval`, `compile`, `from ingest.db import open_db`, `from ingest import db`, `import sqlite3`, the collector imports, and `import ACME`.
- `test_independent_verifier_is_registered[...]` (positive). This now includes the exact set from the re-review (`from ingest.http import HttpResult`, `from ingest.models import parse_number`, `from ingest.rawstore import RawStore`, `from ingest.sources import Source, RawResponse`, `from ingest.verifiers import ItemResult, BlindItem`) and `re.compile` + `open`. The former positive case `"import ingest.rawstore"` became `"from ingest.rawstore import RawStore"`.
- `test_shared_helper_with_parser_is_rejected` and `test_only_allow_listed_shared_modules_is_accepted` now use the `from ingest.x import y` form, so the shared-module check is what rejects them, not the plain-import rule.
- `test_verifier_importing_parser_is_rejected` (22 cases from round 1) still passes.
- (a) `test_str_subclass_fields_are_failure[observed_text|observed_unit|series_id]` uses a `str` subclass whose `__eq__` always returns True. Every item fails with the exact-str note.
- (b) `test_replay_refuses_legacy_item`: a row inserted without the 0004 columns makes `replay_item` raise ValueError "legacy item".

## Evidence
p_reg.py BEFORE (the reviewer's script as-is; it loads `ingest` from /tmp/t7fix/repo):
```
$ .venv-ci/bin/python /tmp/t7fix/p_reg.py
import ingest.http; ingest.sources.acme attr     ACCEPTED
import ingest.models; ingest.sources.acme        ACCEPTED
from ingest import http; (no bypass, positive)   ACCEPTED
import sys as s; s.modules                       ACCEPTED
import builtins; builtins.__import__             ACCEPTED
from builtins import __import__ as imp           ACCEPTED
getattr(builtins,'exec')                         ACCEPTED
runpy                                            ACCEPTED
pkgutil                                          ACCEPTED
shared helper ingest.helpers.numparse            rejected: ares code with its parser through imports of ['ingest.helpers', 'ingest.helpers.numparse']
shared helper via pkg                            rejected: ares code with its parser through imports of ['ingest.helpers', 'ingest.helpers.numparse']
ingest.validate (parser uses)                    rejected: verifier for 'acme' shares code with its parser through imports of ['ingest.validate']
ingest.verify                                    rejected: verifier for 'acme' shares code with its parser through imports of ['ingest.validate']
ingest.pipeline                                  rejected: verifier for 'acme' shares code with its parser through imports of ['ingest.validate']
ingest.db (read expected from DB)                ACCEPTED
sqlite3 (read expected)                          ACCEPTED
from ingest.sources import Source (positive)     ACCEPTED
from ingest.sources import *                     rejected: me' must be independent of the collector, but its module imports/uses ['ingest.sources.*']
import ingest.sources.acme as x                  rejected:  must be independent of the collector, but its module imports/uses ['ingest.sources.acme']
from ingest.sources.acme import parse_rows       rejected:  must be independent of the collector, but its module imports/uses ['ingest.sources.acme']
from ingest.sources import acme                  rejected:  must be independent of the collector, but its module imports/uses ['ingest.sources.acme']
import ACME (case)                               import error ModuleNotFoundError("No module named 'ACME'")
vars(ingest)                                     ACCEPTED
globals builtins                                 ACCEPTED
dup acme rejected a verifier for source 'acme' is already registered
dup ACME ACCEPTED
```
p_reg.py AFTER. The script is identical except that it points at a scratchpad copy of /tmp/t7fix/repo (real `ingest/sources/acme.py` parser, `ingest/helpers/numparse.py`) whose `ingest/verifiers/__init__.py` was replaced with this commit's version (`diff -q` was empty):
```
$ .venv-ci/bin/python p_reg_after.py
import ingest.http; ingest.sources.acme attr     rejected: ector: ingest.sources.acme.parse_rows', "plain import binds 'ingest': import ingest.http"]
import ingest.models; ingest.sources.acme        rejected: s to collector: ingest.sources.acme', "plain import binds 'ingest': import ingest.models"]
from ingest import http; (no bypass, positive)   ACCEPTED
import sys as s; s.modules                       rejected: rts/uses ['dynamic import/DB access: import sys', 'dynamic import/DB access: sys.modules']
import builtins; builtins.__import__             rejected: namic import/DB access: builtins.__import__', 'dynamic import/DB access: import builtins']
from builtins import __import__ as imp           rejected:  builtins import __import__', 'dynamic import/DB access: from builtins import __import__']
getattr(builtins,'exec')                         rejected: odule imports/uses ['dynamic code: builtins', 'dynamic import/DB access: import builtins']
runpy                                            rejected: ', 'dynamic import/DB access: import runpy', 'dynamic import/DB access: runpy.run_module']
pkgutil                                          rejected: namic import/DB access: import pkgutil', 'dynamic import/DB access: pkgutil.resolve_name']
shared helper ingest.helpers.numparse            rejected: ares code with its parser through imports of ['ingest.helpers', 'ingest.helpers.numparse']
shared helper via pkg                            rejected: ares code with its parser through imports of ['ingest.helpers', 'ingest.helpers.numparse']
ingest.validate (parser uses)                    rejected: verifier for 'acme' shares code with its parser through imports of ['ingest.validate']
ingest.verify                                    rejected: verifier for 'acme' shares code with its parser through imports of ['ingest.validate']
ingest.pipeline                                  rejected: ector, but its module imports/uses ["plain import binds 'ingest': import ingest.pipeline"]
ingest.db (read expected from DB)                rejected: r, but its module imports/uses ['dynamic import/DB access: from ingest.db import open_db']
sqlite3 (read expected)                          rejected: of the collector, but its module imports/uses ['dynamic import/DB access: import sqlite3']
from ingest.sources import Source (positive)     ACCEPTED
from ingest.sources import *                     rejected:  collector, but its module imports/uses ['collector import: from ingest.sources import *']
import ingest.sources.acme as x                  rejected: t binds 'ingest': import ingest.sources.acme", 'source-named import: ingest.sources.acme']
from ingest.sources.acme import parse_rows       rejected: st.sources.acme import parse_rows', 'source-named import: ingest.sources.acme.parse_rows']
from ingest.sources import acme                  rejected: ctor import: from ingest.sources import acme', 'source-named import: ingest.sources.acme']
import ACME (case)                               import error ModuleNotFoundError("No module named 'ACME'")
vars(ingest)                                     rejected: ule imports/uses ['dynamic code: vars', "plain import binds 'ingest': import ingest.http"]
globals builtins                                 rejected: ust be independent of the collector, but its module imports/uses ['dynamic code: globals']
dup acme rejected a verifier for source 'acme' is already registered
dup ACME ACCEPTED
```
(Every bypass is rejected; the two positive cases are still accepted. `import ACME` fails in the probe because the module does not exist at import time; the unit test covers it with the import in a function body.)

GREEN: `/home/joao/projects/prumo-pipeline/.venv-ci/bin/python -m pytest tests/ingest -v` (test_verify.py part and total):
```
tests/ingest/test_verify.py::test_sample_always_includes_latest_period_of_each_series PASSED [ 62%]
tests/ingest/test_verify.py::test_sample_is_reproducible_from_seed PASSED [ 62%]
tests/ingest/test_verify.py::test_sample_covers_every_series_even_when_size_smaller PASSED [ 63%]
tests/ingest/test_verify.py::test_sample_takes_every_observation_when_size_exceeds_run PASSED [ 63%]
tests/ingest/test_verify.py::test_sample_rejects_unknown_series_and_bad_size PASSED [ 63%]
tests/ingest/test_verify.py::test_all_match_marks_verified PASSED        [ 64%]
tests/ingest/test_verify.py::test_single_mismatch_marks_failed_and_not_served PASSED [ 64%]
tests/ingest/test_verify.py::test_none_observed_counts_as_mismatch PASSED [ 64%]
tests/ingest/test_verify.py::test_verification_items_store_evidence_url PASSED [ 65%]
tests/ingest/test_verify.py::test_decimal_comparison_is_exact_not_float[1.10-1,1-,-True] PASSED [ 65%]
tests/ingest/test_verify.py::test_decimal_comparison_is_exact_not_float[1.10-1.1-.-True] PASSED [ 65%]
tests/ingest/test_verify.py::test_decimal_comparison_is_exact_not_float[1 234.5-1.234,50-,-True] PASSED [ 66%]
tests/ingest/test_verify.py::test_decimal_comparison_is_exact_not_float[1.10-1.1000001-.-False] PASSED [ 66%]
tests/ingest/test_verify.py::test_decimal_comparison_is_exact_not_float[0.30000000000000004-0.3-.-False] PASSED [ 66%]
tests/ingest/test_verify.py::test_decimal_comparison_is_exact_not_float[1.10-1,1-.-False] PASSED [ 67%]
tests/ingest/test_verify.py::test_decimal_comparison_is_exact_not_float[1.10-n/d-.-False] PASSED [ 67%]
tests/ingest/test_verify.py::test_unit_or_flag_mismatch_fails[kw0-True] PASSED [ 67%]
tests/ingest/test_verify.py::test_unit_or_flag_mismatch_fails[kw1-True] PASSED [ 68%]
tests/ingest/test_verify.py::test_unit_or_flag_mismatch_fails[kw2-False] PASSED [ 68%]
tests/ingest/test_verify.py::test_unit_or_flag_mismatch_fails[kw3-False] PASSED [ 68%]
tests/ingest/test_verify.py::test_unit_or_flag_mismatch_fails[kw4-True] PASSED [ 69%]
tests/ingest/test_verify.py::test_verifier_exception_is_failure_not_pass PASSED [ 69%]
tests/ingest/test_verify.py::test_wrong_result_count_is_failure PASSED   [ 69%]
tests/ingest/test_verify.py::test_out_of_order_result_is_failure PASSED  [ 70%]
tests/ingest/test_verify.py::test_duplicate_key_result_is_failure PASSED [ 70%]
tests/ingest/test_verify.py::test_parser_swapped_periods_with_reordered_verifier_fails PASSED [ 70%]
tests/ingest/test_verify.py::test_verifier_gets_blinded_items PASSED     [ 71%]
tests/ingest/test_verify.py::test_echoing_what_it_is_given_cannot_pass PASSED [ 71%]
tests/ingest/test_verify.py::test_refuses_to_verify_non_pending_run PASSED [ 71%]
tests/ingest/test_verify.py::test_random_seed_is_stored_when_not_given PASSED [ 72%]
tests/ingest/test_verify.py::test_malformed_result_fields_are_failure_not_crash PASSED [ 72%]
tests/ingest/test_verify.py::test_str_subclass_fields_are_failure[observed_text] PASSED [ 72%]
tests/ingest/test_verify.py::test_str_subclass_fields_are_failure[observed_unit] PASSED [ 73%]
tests/ingest/test_verify.py::test_str_subclass_fields_are_failure[series_id] PASSED [ 73%]
tests/ingest/test_verify.py::test_replay_refuses_legacy_item PASSED      [ 73%]
tests/ingest/test_verify.py::test_concurrent_verify_loser_is_rolled_back[inner_truth0-failed-verification] PASSED [ 74%]
tests/ingest/test_verify.py::test_concurrent_verify_loser_is_rolled_back[inner_truth1-verified] PASSED [ 74%]
tests/ingest/test_verify.py::test_evidence_bytes_saved_and_items_replayable PASSED [ 74%]
tests/ingest/test_verify.py::test_replay_needs_no_registry_and_reproduces_every_outcome PASSED [ 75%]
tests/ingest/test_verify.py::test_replay_detects_tampered_evidence PASSED [ 75%]
tests/ingest/test_verify.py::test_evidence_without_store_is_refused PASSED [ 75%]
tests/ingest/test_verify.py::test_refetch_uses_new_seed_each_attempt PASSED [ 76%]
tests/ingest/test_verify.py::test_gives_up_after_max_attempts_and_stays_unserved PASSED [ 76%]
tests/ingest/test_verify.py::test_previously_verified_data_still_served_after_failed_verification PASSED [ 76%]
tests/ingest/test_verify.py::test_short_circuit_run_gets_no_verification_row PASSED [ 77%]
tests/ingest/test_verify.py::test_failed_fetch_is_returned_without_verification PASSED [ 77%]
tests/ingest/test_verify.py::test_refetch_requires_the_registered_verifier PASSED [ 77%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import ingest.sources.acme] PASSED [ 78%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from ingest.sources.acme import parse] PASSED [ 78%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from ingest.sources import acme] PASSED [ 78%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from ingest.sources import eurostat] PASSED [ 79%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import ingest.sources.eurostat as e] PASSED [ 79%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from ingest.sources import validate_helper] PASSED [ 80%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import importlib\nP = importlib.import_module('ingest.sources.acme')] PASSED [ 80%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from importlib import import_module] PASSED [ 80%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[P = __import__('ingest.sources.acme')] PASSED [ 81%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from ingest import sources\nP = sources.acme] PASSED [ 81%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from ingest import sources as s] PASSED [ 81%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import ingest.sources\nP = ingest.sources.acme] PASSED [ 82%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import ingest\nP = ingest.sources.acme] PASSED [ 82%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[exec('from ingest.sources.acme import parse')] PASSED [ 82%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[eval('1')] PASSED [ 83%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import sys\nP = sys.modules['ingest.sources.acme']] PASSED [ 83%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from sys import modules] PASSED [ 83%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import ACME] PASSED [ 84%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import acme] PASSED [ 84%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from vendor.Acme import parse] PASSED [ 84%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from vendor import acme] PASSED [ 85%]
tests/ingest/test_verify.py::test_independent_verifier_is_registered[] PASSED [ 85%]
tests/ingest/test_verify.py::test_independent_verifier_is_registered[from ingest.sources import RawResponse, Source] PASSED [ 85%]
tests/ingest/test_verify.py::test_independent_verifier_is_registered[from ingest.http import Http\nfrom ingest.models import parse_decimal\nimport json] PASSED [ 86%]
tests/ingest/test_verify.py::test_independent_verifier_is_registered[from ingest.verifiers import ItemResult, BlindItem] PASSED [ 86%]
tests/ingest/test_verify.py::test_independent_verifier_is_registered[from ingest.rawstore import RawStore] PASSED [ 86%]
tests/ingest/test_verify.py::test_independent_verifier_is_registered[code5] PASSED [ 87%]
tests/ingest/test_verify.py::test_independent_verifier_is_registered[import re\nP = re.compile('x')\nwith open('f') as f:\n    pass] PASSED [ 87%]
tests/ingest/test_verify.py::test_shared_helper_with_parser_is_rejected PASSED [ 87%]
tests/ingest/test_verify.py::test_only_allow_listed_shared_modules_is_accepted PASSED [ 88%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import ingest.http\nP = ingest.sources.acme.parse_rows-plain import binds 'ingest'] PASSED [ 88%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import ingest.models\nP = ingest.sources.acme-plain import binds 'ingest'] PASSED [ 88%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import ingest.rawstore-plain import binds 'ingest'] PASSED [ 89%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import ingest.http as h-plain import binds 'ingest'] PASSED [ 89%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import ingest-plain import binds 'ingest'] PASSED [ 89%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.verifiers import ingest as i-name binds 'ingest'] PASSED [ 90%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = ingest.sources.acme.parse_rows-attribute access to collector: ingest.sources.acme] PASSED [ 90%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.verifiers import ingest as i\nP = i.sources-attribute access to collector] PASSED [ 90%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import sys as s\nP = s.modules['ingest.sources.acme']-dynamic import/DB access] PASSED [ 91%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from sys import modules-dynamic import/DB access] PASSED [ 91%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.verifiers import sys-dynamic import/DB access] PASSED [ 91%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import builtins\nP = builtins.__import__('ingest.sources.acme')-dynamic import/DB access] PASSED [ 92%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from builtins import __import__ as imp\nP = imp('x')-dynamic import/DB access] PASSED [ 92%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import runpy\nruns = runpy.run_module-dynamic import/DB access] PASSED [ 92%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import pkgutil\nP = pkgutil.resolve_name('ingest.sources.acme:parse_rows')-dynamic import/DB access] PASSED [ 93%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import importlib-dynamic import/DB access] PASSED [ 93%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from importlib import import_module-dynamic import/DB access] PASSED [ 93%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = __import__('ingest.sources.acme')-dynamic code: __import__] PASSED [ 94%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[x = object().__import__-dynamic code: .__import__] PASSED [ 94%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = vars(ingest)['sources']-dynamic code: vars] PASSED [ 94%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = globals()['__builtins__']['__imp' + 'ort__']-dynamic code: globals] PASSED [ 95%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = locals()-dynamic code: locals] PASSED [ 95%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = __builtins__-dynamic code: __builtins__] PASSED [ 95%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[exec('import ingest.sources.acme')-dynamic code: exec] PASSED [ 96%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[eval('1')-dynamic code: eval] PASSED [ 96%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = compile('1', 'f', 'eval')-dynamic code: compile] PASSED [ 96%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.db import open_db-dynamic import/DB access: from ingest.db] PASSED [ 97%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest import db-dynamic import/DB access: from ingest import db] PASSED [ 97%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import sqlite3-dynamic import/DB access: import sqlite3] PASSED [ 97%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.sources import acme-collector import] PASSED [ 98%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.sources.acme import parse_rows-collector import] PASSED [ 98%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest import sources-collector import] PASSED [ 98%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import ACME-source-named import] PASSED [ 99%]
tests/ingest/test_verify.py::test_duplicate_registration_is_rejected PASSED [ 99%]
tests/ingest/test_verify.py::test_fake_verifier_module_passes_the_rule PASSED [100%]
============================= 295 passed in 28.36s =============================
```

## Concerns (round 2)
- `dup ACME ACCEPTED` (last line of p_reg): the registry is keyed on the exact `source_name`, so a verifier named `ACME` can still be registered next to `acme`. The source-name match is case-insensitive for imports only. I left this alone because it was outside the round-2 scope; making the duplicate check case-insensitive is a one-line change if wanted.
- `from ingest import <module>` (other than sources/db/*) is allowed, matching the probe's "positive" label rather than the strictest reading of rule 1.
- Runtime-built access remains undetectable, e.g. getattr with computed strings on objects that are not on the denylist. That is documented; the per-adapter subprocess test is the backstop.

---

# Fix round 3 (Ruling S: allowlists + runtime guard)

Commits: `d88a903` (static allowlist; green on its own: 336 passed) and `0f766b2` (runtime guard + tests). Final: **341 passed** (`tests/ingest`). `test_verify.py` + `test_independence.py` are clean under `-W error` (158 passed).

## 1. Static check is now allowlist-based (`ingest/verifiers/__init__.py`)
- `VERIFIER_INGEST_IMPORTS`: `ingest.http` {HttpResult, Http}, `ingest.models` {parse_number, SeriesSpec}, `ingest.rawstore` {RawStore}, `ingest.sources` {Source, RawResponse}, `ingest.verifiers` {ItemResult, BlindItem, Verifier}. Only `from ingest.<module> import <names>` within this allowlist is accepted. These are rejected, each with its own rule text: `import ingest...` in any form, `from ingest import x`, any other ingest module, any other name (private names and modules-as-names included), star imports from ANY module, and relative imports.
- `VERIFIER_STDLIB_IMPORTS` holds the ruled stdlib list; nothing else may be imported (requests, sys, os, importlib, builtins, runpy, pkgutil, sqlite3, third-party...). A name taken from an allowed stdlib module with `from` must not be private and must not be a module outside the allowlist; `from logging import sys` is rejected.
- These are rejected: every attribute whose name starts with `__`; the bare names `__import__, __builtins__, __loader__, __spec__, __globals__, exec, eval, compile, vars, globals, locals, getattr, setattr, delattr, type, super, open`.
- Added: an attribute chain on an imported name may not reach a module outside the allowlists (and their parent packages). The chain is resolved on the already-imported allow-listed objects, which closes stdlib re-exports such as `logging.sys.modules` and `urllib.request`.
- Kept: the source-named import check (case-insensitive), the duplicate check, and the transitive shared-module check against `ingest.sources.<source_name>`. Its findings are now reported together with the static ones in one ValueError. `SHARED_ALLOWED = {"ingest", *VERIFIER_INGEST_IMPORTS}`, so the same constant drives both checks.
- The docstring says the static check is a lint-level guard and the runtime test is the guarantee.

## 2. Runtime guard (`ingest/verifiers/independence.py`)
`assert_verifier_independent(verifier_module: str, entrypoint: str, *, source_name: str, blocked_prefixes: tuple[str, ...] = (), extra_sys_path: tuple[str, ...] = (), timeout: float = 60.0) -> None`
- Runs `sys.executable -I -c <child>` with cwd = repo root. The child's first act is to install a `sys.meta_path` finder that raises ImportError for every `ingest.sources.<x>`, for `ingest.sources.<source_name>` and for `blocked_prefixes`. Only after that does it prepend `extra_sys_path` + repo root to `sys.path`, import `verifier_module`, and call `entrypoint` (either a name in that module or `"module:func"`). It then prints the loaded `ingest.*` modules as JSON after a marker.
- The parent raises AssertionError in these cases: the child exited non-zero (the message includes the stderr tail); a blocked module was loaded; or a loaded `ingest.*` module is outside the shared runtime set. That set is `SHARED_ALLOWED` plus the `ingest.*` modules those modules import themselves, read from the files: today that adds `ingest.validate` (via `ingest.sources`) and the guard module itself.
- Two additions to the ruled signature: `extra_sys_path`, needed by the tests' temporary modules and scratch layout, and `timeout`.
- The module docstring says every adapter task must call it.

## Covering tests
- `test_verify.py::test_registration_bypasses_are_rejected[...]`, 69 cases. Each asserts ValueError plus the rule text. They cover the earlier rounds' cases, updated to the new messages, and A (`v.ingest.sources.acme`, `v.sys.modules`, `m.re`, `h.requests`, `from ingest.http import requests|time`, `from ingest.verifiers import sys`, `logging.sys.modules`, `urllib.request`, `from logging import sys`, `from collections import _collections_abc`), B (`parse_number.__globals__[...]`, `.__builtins__`, `RawResponse.__init__`, `type(BlindItem).__mro__`, `BlindItem.__mro__`, `__loader__`, `__spec__`, `__globals__`, `getattr/setattr/delattr/super/open/vars/globals/locals/exec/eval/compile/__import__/__builtins__`) and C (`_REGISTRY`, `get_verifier`, `inspect`, `ast`, `dataclass`, `urljoin`, `Observation`, `rawstore.Path`, `from . import acme`, `from .. import sources`), plus imports inside `if TYPE_CHECKING:` and `try:`.
- `test_star_imports_are_rejected[...]`, 5 cases at module level (ingest.http/models/verifiers/sources, json).
- `test_independent_verifier_is_registered[...]`, 8 positive cases: the full allowlisted ingest set, re, json/csv/decimal/dataclasses, `urllib.parse`, `xml.etree.ElementTree as ET`, logging, and TYPE_CHECKING.
- `test_shared_helper_with_parser_is_rejected` (the error now lists both the allowlist rule and `shares code with its parser: ingest.sdmx`); `test_only_allow_listed_shared_modules_is_accepted`; `test_verifier_importing_parser_is_rejected` (22 cases); `test_fake_verifier_module_passes_the_rule`; `test_duplicate_registration_is_rejected`.
- `test_independence.py` uses real subprocesses over a scratch copy of the `ingest` package that has a real `ingest/sources/acme.py`:
  - `test_clean_verifier_passes` covers a name entrypoint and a `module:func` entrypoint building a BlindItem;
  - `test_helper_importing_the_parser_fails`: a non-ingest helper does `import ingest.sources.acme`. A control subprocess without the guard proves the parser really is reachable; under the guard it fails with `blocked by independence guard: ingest.sources.acme`;
  - `test_non_shared_ingest_modules_fail` (a helper pulls in ingest.pipeline, which brings ingest.db);
  - `test_blocked_prefixes_are_enforced`;
  - `test_entrypoint_exception_is_readable` (the message includes `RuntimeError: boom in check`).

## Evidence
p.py BEFORE (reviewer script as-is against /tmp/t7r3/repo; 39 ACCEPTED, of which 5 are the intended positives):
```
$ .venv-ci/bin/python /tmp/t7r3/p.py
import ingest.http                             rejected: lector: ingest.sources.acme', "plain import binds 'ingest': import ingest.http"]
import sys as s                                rejected: 'dynamic import/DB access: import sys', 'dynamic import/DB access: sys.modules']
vars                                           rejected: independent of the collector, but its module imports/uses ['dynamic code: vars']
pos http                                       ACCEPTED
pos models                                     ACCEPTED
pos rawstore                                   ACCEPTED
pos sources                                    ACCEPTED
pos verifiers                                  ACCEPTED
v.__dict__                                     ACCEPTED
v.ingest.sources                               ACCEPTED
v.sys.modules                                  ACCEPTED
v.ingest (just name)                           ACCEPTED
from ingest.verifiers import inspect           ACCEPTED
h.__spec__                                     ACCEPTED
from ingest.http import __builtins__           rejected: t its module imports/uses ['dynamic code: from ingest.http import __builtins__']
RawResponse.__init__.__globals__               ACCEPTED
func __globals__ via ItemResult                ACCEPTED
BlindItem __mro__                              ACCEPTED
__loader__                                     ACCEPTED
__spec__ name                                  ACCEPTED
__name__ w/o                                   ACCEPTED
rel from . import acme                         import error ImportError
rel from .. import sources                     import error ImportError
S.__module__                                   ACCEPTED
from ingest import http as h; h.requests       ACCEPTED
from ingest import pipeline                    rejected: er for 'acme' shares code with its parser through imports of ['ingest.validate']
from ingest import pipeline as p; p.Source     import error AttributeError
from ingest import rawstore                    ACCEPTED
from ingest import verify                      import error AttributeError
from ingest import validate                    rejected: er for 'acme' shares code with its parser through imports of ['ingest.validate']
from ingest import registry                    ACCEPTED
from ingest import models as m                 ACCEPTED
if TYPE_CHECKING import                        rejected: .acme import parse_rows', 'source-named import: ingest.sources.acme.parse_rows']
try import                                     rejected: .acme import parse_rows', 'source-named import: ingest.sources.acme.parse_rows']
func-local import                              rejected: ngest': import ingest.sources.acme", 'source-named import: ingest.sources.acme']
func-local from                                rejected: t: from ingest.sources import acme', 'source-named import: ingest.sources.acme']
star from http                                 ACCEPTED
star from models                               ACCEPTED
star from verifiers                            ACCEPTED
star from sources                              rejected: , but its module imports/uses ['collector import: from ingest.sources import *']
from ingest.http import time                   ACCEPTED
from ingest.http import requests               ACCEPTED
from ingest.rawstore import os/Path            ACCEPTED
from ingest.verifiers import _REGISTRY         ACCEPTED
from ingest.verifiers import get_verifier      ACCEPTED
from ingest.verifiers import _module_file      ACCEPTED
from ingest.verifiers import ast               ACCEPTED
from ingest.http import urljoin                ACCEPTED
from ingest.verifiers import dataclass         ACCEPTED
from ingest.models import SeriesSpec; SeriesSpec.__init__.__globals__ ACCEPTED
func __globals__ plain                         ACCEPTED
func __globals__ -> import                     ACCEPTED
func __builtins__attr                          rejected: nt of the collector, but its module imports/uses ['dynamic code: .__builtins__']
__import__ via http module sys                 ACCEPTED
ACME alias                                     ACCEPTED
```
p.py AFTER. The script is the same except that it points at a scratchpad copy of /tmp/t7r3/repo whose `ingest/verifiers/` was replaced by this round's `__init__.py` + `independence.py`:
```
$ .venv-ci/bin/python r3_p_after.py
import ingest.http                             rejected: ort not allowed (use 'from ingest.<module> import <name>'): import ingest.http"]
import sys as s                                rejected:  be independent of the collector: ['module not in stdlib allowlist: import sys']
vars                                           rejected: rifier for 'acme' must be independent of the collector: ['forbidden name: vars']
pos http                                       ACCEPTED
pos models                                     ACCEPTED
pos rawstore                                   ACCEPTED
pos sources                                    ACCEPTED
pos verifiers                                  ACCEPTED
v.__dict__                                     rejected: ute: .__dict__', 'ingest module not in allowlist: from ingest import verifiers']
v.ingest.sources                               rejected:  the collector: ['ingest module not in allowlist: from ingest import verifiers']
v.sys.modules                                  rejected:  the collector: ['ingest module not in allowlist: from ingest import verifiers']
v.ingest (just name)                           rejected:  the collector: ['ingest module not in allowlist: from ingest import verifiers']
from ingest.verifiers import inspect           rejected: endent of the collector: ['name not in allowlist for ingest.verifiers: inspect']
h.__spec__                                     rejected: ttribute: .__spec__', 'ingest module not in allowlist: from ingest import http']
from ingest.http import __builtins__           rejected: endent of the collector: ['name not in allowlist for ingest.http: __builtins__']
RawResponse.__init__.__globals__               rejected: the collector: ['dunder attribute: .__globals__', 'dunder attribute: .__init__']
func __globals__ via ItemResult                rejected: the collector: ['dunder attribute: .__globals__', 'dunder attribute: .__init__']
BlindItem __mro__                              rejected: pendent of the collector: ['dunder attribute: .__mro__', 'forbidden name: type']
__loader__                                     rejected:  for 'acme' must be independent of the collector: ['forbidden name: __loader__']
__spec__ name                                  rejected: er for 'acme' must be independent of the collector: ['forbidden name: __spec__']
__name__ w/o                                   ACCEPTED
rel from . import acme                         import error ImportError
rel from .. import sources                     import error ImportError
S.__module__                                   rejected: r 'acme' must be independent of the collector: ['dunder attribute: .__module__']
from ingest import http as h; h.requests       rejected: nt of the collector: ['ingest module not in allowlist: from ingest import http']
from ingest import pipeline                    rejected: t: from ingest import pipeline', 'shares code with its parser: ingest.validate']
from ingest import pipeline as p; p.Source     import error AttributeError
from ingest import rawstore                    rejected: f the collector: ['ingest module not in allowlist: from ingest import rawstore']
from ingest import verify                      import error AttributeError
from ingest import validate                    rejected: t: from ingest import validate', 'shares code with its parser: ingest.validate']
from ingest import registry                    rejected: f the collector: ['ingest module not in allowlist: from ingest import registry']
from ingest import models as m                 rejected:  of the collector: ['ingest module not in allowlist: from ingest import models']
if TYPE_CHECKING import                        rejected: ts parser: ingest.sources.acme', 'shares code with its parser: ingest.validate']
try import                                     rejected: ts parser: ingest.sources.acme', 'shares code with its parser: ingest.validate']
func-local import                              rejected: ts parser: ingest.sources.acme', 'shares code with its parser: ingest.validate']
func-local from                                rejected: ts parser: ingest.sources.acme', 'shares code with its parser: ingest.validate']
star from http                                 rejected: pendent of the collector: ['star import not allowed: from ingest.http import *']
star from models                               rejected: ndent of the collector: ['star import not allowed: from ingest.models import *']
star from verifiers                            rejected: nt of the collector: ['star import not allowed: from ingest.verifiers import *']
star from sources                              rejected: dent of the collector: ['star import not allowed: from ingest.sources import *']
from ingest.http import time                   rejected: be independent of the collector: ['name not in allowlist for ingest.http: time']
from ingest.http import requests               rejected: ndependent of the collector: ['name not in allowlist for ingest.http: requests']
from ingest.rawstore import os/Path            rejected: ndependent of the collector: ['name not in allowlist for ingest.rawstore: Path']
from ingest.verifiers import _REGISTRY         rejected: dent of the collector: ['name not in allowlist for ingest.verifiers: _REGISTRY']
from ingest.verifiers import get_verifier      rejected: t of the collector: ['name not in allowlist for ingest.verifiers: get_verifier']
from ingest.verifiers import _module_file      rejected: .verifiers: _module_file', 'name not in allowlist for ingest.verifiers: _parse']
from ingest.verifiers import ast               rejected: ndependent of the collector: ['name not in allowlist for ingest.verifiers: ast']
from ingest.http import urljoin                rejected: independent of the collector: ['name not in allowlist for ingest.http: urljoin']
from ingest.verifiers import dataclass         rejected: dent of the collector: ['name not in allowlist for ingest.verifiers: dataclass']
from ingest.models import SeriesSpec; SeriesSpec.__init__.__globals__ rejected: the collector: ['dunder attribute: .__globals__', 'dunder attribute: .__init__']
func __globals__ plain                         rejected:  'acme' must be independent of the collector: ['dunder attribute: .__globals__']
func __globals__ -> import                     rejected:  'acme' must be independent of the collector: ['dunder attribute: .__globals__']
func __builtins__attr                          rejected: 'acme' must be independent of the collector: ['dunder attribute: .__builtins__']
__import__ via http module sys                 rejected: nt of the collector: ['ingest module not in allowlist: from ingest import http']
ACME alias                                     ACCEPTED
```
Seven cases are still ACCEPTED. Five are the intended positives (`pos ...`). `P = __name__` is a plain string. `from ingest.models import parse_number as acme` only names an alias `acme` for `parse_number`. Neither of the last two reaches the parser.

rt.py BEFORE / AFTER (same output by construction: it shows that, inside a process where the parser is already loaded, Python can reach it; no static rule can change that):
```
<module 'ingest.sources.acme' from '/tmp/t7r3/repo/ingest/sources/acme.py'>
<module 'ingest.sources.acme' from '/tmp/t7r3/repo/ingest/sources/acme.py'>
<module 'ingest.sources.acme' from '/tmp/t7r3/repo/ingest/sources/acme.py'>
--- after (against the scratch copy with this round's code) ---
<module 'ingest.sources.acme' from '/tmp/claude-1000/-home-joao/0cf85576-cadd-4c92-a5b2-4aac697971e6/scratchpad/t7r3repo/ingest/sources/acme.py'>
<module 'ingest.sources.acme' from '/tmp/claude-1000/-home-joao/0cf85576-cadd-4c92-a5b2-4aac697971e6/scratchpad/t7r3repo/ingest/sources/acme.py'>
<module 'ingest.sources.acme' from '/tmp/claude-1000/-home-joao/0cf85576-cadd-4c92-a5b2-4aac697971e6/scratchpad/t7r3repo/ingest/sources/acme.py'>
```
The same three accesses inside the guard's child (`_CHILD`, blocker installed; scratch copy with a real parser):
```
v.ingest.sources.acme -> AttributeError module 'ingest' has no attribute 'sources'
v.sys.modules -> KeyError 'ingest.sources.acme'
__globals__ __import__ -> ImportError blocked by independence guard: ingest.sources.acme
 exit 0
```

GREEN: `/home/joao/projects/prumo-pipeline/.venv-ci/bin/python -m pytest tests/ingest -v` (verification-related part and total):
```
tests/ingest/test_independence.py::test_clean_verifier_passes PASSED     [  7%]
tests/ingest/test_independence.py::test_helper_importing_the_parser_fails PASSED [  7%]
tests/ingest/test_independence.py::test_non_shared_ingest_modules_fail PASSED [  8%]
tests/ingest/test_independence.py::test_blocked_prefixes_are_enforced PASSED [  8%]
tests/ingest/test_independence.py::test_entrypoint_exception_is_readable PASSED [  8%]
tests/ingest/test_verify.py::test_sample_always_includes_latest_period_of_each_series PASSED [ 55%]
tests/ingest/test_verify.py::test_sample_is_reproducible_from_seed PASSED [ 55%]
tests/ingest/test_verify.py::test_sample_covers_every_series_even_when_size_smaller PASSED [ 56%]
tests/ingest/test_verify.py::test_sample_takes_every_observation_when_size_exceeds_run PASSED [ 56%]
tests/ingest/test_verify.py::test_sample_rejects_unknown_series_and_bad_size PASSED [ 56%]
tests/ingest/test_verify.py::test_all_match_marks_verified PASSED        [ 56%]
tests/ingest/test_verify.py::test_single_mismatch_marks_failed_and_not_served PASSED [ 57%]
tests/ingest/test_verify.py::test_none_observed_counts_as_mismatch PASSED [ 57%]
tests/ingest/test_verify.py::test_verification_items_store_evidence_url PASSED [ 57%]
tests/ingest/test_verify.py::test_decimal_comparison_is_exact_not_float[1.10-1,1-,-True] PASSED [ 58%]
tests/ingest/test_verify.py::test_decimal_comparison_is_exact_not_float[1.10-1.1-.-True] PASSED [ 58%]
tests/ingest/test_verify.py::test_decimal_comparison_is_exact_not_float[1 234.5-1.234,50-,-True] PASSED [ 58%]
tests/ingest/test_verify.py::test_decimal_comparison_is_exact_not_float[1.10-1.1000001-.-False] PASSED [ 58%]
tests/ingest/test_verify.py::test_decimal_comparison_is_exact_not_float[0.30000000000000004-0.3-.-False] PASSED [ 59%]
tests/ingest/test_verify.py::test_decimal_comparison_is_exact_not_float[1.10-1,1-.-False] PASSED [ 59%]
tests/ingest/test_verify.py::test_decimal_comparison_is_exact_not_float[1.10-n/d-.-False] PASSED [ 59%]
tests/ingest/test_verify.py::test_unit_or_flag_mismatch_fails[kw0-True] PASSED [ 60%]
tests/ingest/test_verify.py::test_unit_or_flag_mismatch_fails[kw1-True] PASSED [ 60%]
tests/ingest/test_verify.py::test_unit_or_flag_mismatch_fails[kw2-False] PASSED [ 60%]
tests/ingest/test_verify.py::test_unit_or_flag_mismatch_fails[kw3-False] PASSED [ 60%]
tests/ingest/test_verify.py::test_unit_or_flag_mismatch_fails[kw4-True] PASSED [ 61%]
tests/ingest/test_verify.py::test_verifier_exception_is_failure_not_pass PASSED [ 61%]
tests/ingest/test_verify.py::test_wrong_result_count_is_failure PASSED   [ 61%]
tests/ingest/test_verify.py::test_out_of_order_result_is_failure PASSED  [ 62%]
tests/ingest/test_verify.py::test_duplicate_key_result_is_failure PASSED [ 62%]
tests/ingest/test_verify.py::test_parser_swapped_periods_with_reordered_verifier_fails PASSED [ 62%]
tests/ingest/test_verify.py::test_verifier_gets_blinded_items PASSED     [ 63%]
tests/ingest/test_verify.py::test_echoing_what_it_is_given_cannot_pass PASSED [ 63%]
tests/ingest/test_verify.py::test_refuses_to_verify_non_pending_run PASSED [ 63%]
tests/ingest/test_verify.py::test_random_seed_is_stored_when_not_given PASSED [ 63%]
tests/ingest/test_verify.py::test_malformed_result_fields_are_failure_not_crash PASSED [ 64%]
tests/ingest/test_verify.py::test_str_subclass_fields_are_failure[observed_text] PASSED [ 64%]
tests/ingest/test_verify.py::test_str_subclass_fields_are_failure[observed_unit] PASSED [ 64%]
tests/ingest/test_verify.py::test_str_subclass_fields_are_failure[series_id] PASSED [ 65%]
tests/ingest/test_verify.py::test_replay_refuses_legacy_item PASSED      [ 65%]
tests/ingest/test_verify.py::test_concurrent_verify_loser_is_rolled_back[inner_truth0-failed-verification] PASSED [ 65%]
tests/ingest/test_verify.py::test_concurrent_verify_loser_is_rolled_back[inner_truth1-verified] PASSED [ 65%]
tests/ingest/test_verify.py::test_evidence_bytes_saved_and_items_replayable PASSED [ 66%]
tests/ingest/test_verify.py::test_replay_needs_no_registry_and_reproduces_every_outcome PASSED [ 66%]
tests/ingest/test_verify.py::test_replay_detects_tampered_evidence PASSED [ 66%]
tests/ingest/test_verify.py::test_evidence_without_store_is_refused PASSED [ 67%]
tests/ingest/test_verify.py::test_refetch_uses_new_seed_each_attempt PASSED [ 67%]
tests/ingest/test_verify.py::test_gives_up_after_max_attempts_and_stays_unserved PASSED [ 67%]
tests/ingest/test_verify.py::test_previously_verified_data_still_served_after_failed_verification PASSED [ 68%]
tests/ingest/test_verify.py::test_short_circuit_run_gets_no_verification_row PASSED [ 68%]
tests/ingest/test_verify.py::test_failed_fetch_is_returned_without_verification PASSED [ 68%]
tests/ingest/test_verify.py::test_refetch_requires_the_registered_verifier PASSED [ 68%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import ingest.sources.acme] PASSED [ 69%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from ingest.sources.acme import parse] PASSED [ 69%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from ingest.sources import acme] PASSED [ 69%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from ingest.sources import eurostat] PASSED [ 70%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import ingest.sources.eurostat as e] PASSED [ 70%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from ingest.sources import validate_helper] PASSED [ 70%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import importlib\nP = importlib.import_module('ingest.sources.acme')] PASSED [ 70%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from importlib import import_module] PASSED [ 71%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[P = __import__('ingest.sources.acme')] PASSED [ 71%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from ingest import sources\nP = sources.acme] PASSED [ 71%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from ingest import sources as s] PASSED [ 72%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import ingest.sources\nP = ingest.sources.acme] PASSED [ 72%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import ingest\nP = ingest.sources.acme] PASSED [ 72%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[exec('from ingest.sources.acme import parse')] PASSED [ 73%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[eval('1')] PASSED [ 73%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import sys\nP = sys.modules['ingest.sources.acme']] PASSED [ 73%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from sys import modules] PASSED [ 73%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import ACME] PASSED [ 74%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import acme] PASSED [ 74%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from vendor.Acme import parse] PASSED [ 74%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from vendor import acme] PASSED [ 75%]
tests/ingest/test_verify.py::test_independent_verifier_is_registered[] PASSED [ 75%]
tests/ingest/test_verify.py::test_independent_verifier_is_registered[code1] PASSED [ 75%]
tests/ingest/test_verify.py::test_independent_verifier_is_registered[import re\nP = re.compile('x')] PASSED [ 75%]
tests/ingest/test_verify.py::test_independent_verifier_is_registered[import json\nimport csv\nfrom decimal import Decimal\nfrom dataclasses import dataclass] PASSED [ 76%]
tests/ingest/test_verify.py::test_independent_verifier_is_registered[import urllib.parse\nP = urllib.parse.urlencode({})] PASSED [ 76%]
tests/ingest/test_verify.py::test_independent_verifier_is_registered[import xml.etree.ElementTree as ET\nP = ET.fromstring] PASSED [ 76%]
tests/ingest/test_verify.py::test_independent_verifier_is_registered[import logging\nlog = logging.getLogger('x')] PASSED [ 77%]
tests/ingest/test_verify.py::test_independent_verifier_is_registered[from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from ingest.http import Http] PASSED [ 77%]
tests/ingest/test_verify.py::test_shared_helper_with_parser_is_rejected PASSED [ 77%]
tests/ingest/test_verify.py::test_only_allow_listed_shared_modules_is_accepted PASSED [ 78%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import ingest.http\nP = ingest.sources.acme.parse_rows-import not allowed (use 'from ingest.<module> import <name>')] PASSED [ 78%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import ingest.models\nP = ingest.sources.acme-import not allowed (use 'from ingest.<module> import <name>')] PASSED [ 78%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import ingest.rawstore-import not allowed (use 'from ingest.<module> import <name>')] PASSED [ 78%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import ingest.http as h-import not allowed (use 'from ingest.<module> import <name>')] PASSED [ 79%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import ingest-import not allowed (use 'from ingest.<module> import <name>')] PASSED [ 79%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.verifiers import ingest as i\nP = i.sources-name not in allowlist for] PASSED [ 79%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import sys as s\nP = s.modules['ingest.sources.acme']-module not in stdlib allowlist] PASSED [ 80%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from sys import modules-module not in stdlib allowlist] PASSED [ 80%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import builtins\nP = builtins.__import__('ingest.sources.acme')-module not in stdlib allowlist] PASSED [ 80%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from builtins import __import__ as imp-module not in stdlib allowlist] PASSED [ 80%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import runpy-module not in stdlib allowlist] PASSED [ 81%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import pkgutil\nP = pkgutil.resolve_name('ingest.sources.acme:parse_rows')-module not in stdlib allowlist] PASSED [ 81%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import importlib-module not in stdlib allowlist] PASSED [ 81%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from importlib import import_module-module not in stdlib allowlist] PASSED [ 82%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import sqlite3-module not in stdlib allowlist] PASSED [ 82%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import requests-module not in stdlib allowlist] PASSED [ 82%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import os-module not in stdlib allowlist] PASSED [ 82%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.db import open_db-ingest module not in allowlist] PASSED [ 83%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest import db-ingest module not in allowlist] PASSED [ 83%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.sources.acme import parse_rows-ingest module not in allowlist] PASSED [ 83%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest import sources-ingest module not in allowlist] PASSED [ 84%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.sources import acme-name not in allowlist for] PASSED [ 84%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from ingest.sources.acme import parse_rows-ingest module not in allowlist] PASSED [ 84%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[try:\n    from ingest.sources import acme\nexcept ImportError:\n    pass-name not in allowlist for] PASSED [ 85%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import ACME-source-named import] PASSED [ 85%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest import verifiers as v\nP = v.ingest.sources.acme-ingest module not in allowlist] PASSED [ 85%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest import verifiers as v\nP = v.sys.modules['ingest.sources.acme']-ingest module not in allowlist] PASSED [ 85%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest import models as m\nP = m.re-ingest module not in allowlist] PASSED [ 86%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest import http as h\nP = h.requests-ingest module not in allowlist] PASSED [ 86%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.http import requests-name not in allowlist for] PASSED [ 86%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.http import time-name not in allowlist for] PASSED [ 87%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.verifiers import sys-name not in allowlist for] PASSED [ 87%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import logging\nP = logging.sys.modules-attribute chain reaches module not in allowlist] PASSED [ 87%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import urllib.parse\nP = urllib.request-attribute chain reaches module not in allowlist] PASSED [ 87%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from logging import sys-module not in stdlib allowlist] PASSED [ 88%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from collections import _collections_abc-private name not allowed] PASSED [ 88%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[code36-dunder attribute] PASSED [ 88%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.models import parse_number\nP = parse_number.__builtins__-dunder attribute] PASSED [ 89%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.sources import RawResponse\nP = RawResponse.__init__-dunder attribute] PASSED [ 89%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.verifiers import BlindItem\nP = type(BlindItem).__mro__-forbidden name] PASSED [ 89%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.verifiers import BlindItem\nP = BlindItem.__mro__-dunder attribute] PASSED [ 90%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[x = object().__import__-dunder attribute] PASSED [ 90%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = __loader__-forbidden name] PASSED [ 90%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = __spec__-forbidden name] PASSED [ 90%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = __globals__-forbidden name] PASSED [ 91%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = __import__('ingest.sources.acme')-forbidden name] PASSED [ 91%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = __builtins__-forbidden name] PASSED [ 91%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = vars(object)-forbidden name] PASSED [ 92%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = globals()['__builtins__']-forbidden name] PASSED [ 92%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = locals()-forbidden name] PASSED [ 92%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[exec('import ingest.sources.acme')-forbidden name] PASSED [ 92%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[eval('1')-forbidden name] PASSED [ 93%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = compile('1', 'f', 'eval')-forbidden name] PASSED [ 93%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = getattr(object, 'x')-forbidden name] PASSED [ 93%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[setattr(object, 'x', 1)-forbidden name] PASSED [ 94%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[delattr(object, 'x')-forbidden name] PASSED [ 94%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = super-forbidden name] PASSED [ 94%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = open('f')-forbidden name] PASSED [ 95%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.verifiers import _REGISTRY-name not in allowlist for] PASSED [ 95%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.verifiers import get_verifier-name not in allowlist for] PASSED [ 95%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.verifiers import inspect-name not in allowlist for] PASSED [ 95%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.verifiers import ast-name not in allowlist for] PASSED [ 96%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.verifiers import dataclass-name not in allowlist for] PASSED [ 96%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.http import urljoin-name not in allowlist for] PASSED [ 96%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.models import Observation-name not in allowlist for] PASSED [ 97%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.rawstore import Path-name not in allowlist for] PASSED [ 97%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from . import acme-relative import not allowed] PASSED [ 97%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from .. import sources-relative import not allowed] PASSED [ 97%]
tests/ingest/test_verify.py::test_star_imports_are_rejected[from ingest.http import *] PASSED [ 98%]
tests/ingest/test_verify.py::test_star_imports_are_rejected[from ingest.models import *] PASSED [ 98%]
tests/ingest/test_verify.py::test_star_imports_are_rejected[from ingest.verifiers import *] PASSED [ 98%]
tests/ingest/test_verify.py::test_star_imports_are_rejected[from ingest.sources import *] PASSED [ 99%]
tests/ingest/test_verify.py::test_star_imports_are_rejected[from json import *] PASSED [ 99%]
tests/ingest/test_verify.py::test_duplicate_registration_is_rejected PASSED [ 99%]
tests/ingest/test_verify.py::test_fake_verifier_module_passes_the_rule PASSED [100%]
============================= 341 passed in 31.70s =============================
```

## Concerns (round 3)
- After the allowlist, the transitive shared-module check can only fire for a verifier that the allowlist already rejects. Every import it allows is in SHARED_ALLOWED, and descent stops there. It is kept as ruled and is still exercised by `test_shared_helper_with_parser_is_rejected`, but it is effectively redundant.
- The attribute-chain rule calls `getattr` on objects of already allow-listed modules (stdlib or ingest infrastructure) when a verifier registers. It is static in spirit, but it does touch objects.
- The bare name `ingest` with no import (e.g. `P = ingest.sources.acme`) is not rejected statically: it would be a NameError at runtime, since nothing can bind `ingest` under the allowlist.
- The runtime set allows `ingest.validate`, because `ingest.sources` (allow-listed for `Source`/`RawResponse`) imports it. A verifier still cannot import it directly (static allowlist).
- `extra_sys_path` and `timeout` are additions to the ruled signature.
- Deferred, as instructed: the case-insensitive registry key, verify_run not checking registration, and orphan evidence files.

---

# Fix round 4 (typing/eval gadget: parser loaded under a non-ingest name)

Commit: `5de6053`. Final: **366 passed** (`tests/ingest`). `test_verify.py` + `test_independence.py` are clean under `-W error` (183 passed).

## What changed
**1. Runtime guard (`ingest/verifiers/independence.py`, primary fix).** The child's first acts, before anything else, are:
- install `sys.addaudithook`, which records the real path of every file the process opens (the official audit API; no stdlib patching);
- install the existing `sys.meta_path` blocker.

It locates `ingest.sources` and each `blocked_prefixes` module on disk with `importlib.machinery.PathFinder.find_spec`. That bypasses meta_path and executes nothing. It then runs the entrypoint and reports `{modules: {name: realpath of __file__ / __spec__.origin}, opened: [...], sources: [tree, dir], protected: [...]}`.

The parent keeps the existing name checks and adds two:
- **any module under ANY name** whose origin is inside `ingest/sources/` (other than `__init__.py` and its `__pycache__` bytecode) or inside a blocked prefix's file or package fails with `loaded collector/blocked code under another name: ['zz from …/ingest/sources/acme.py']`;
- **any such file that was opened at all**, source or its bytecode, fails with `opened collector/blocked files: [...]`.

The second check is needed because `spec_from_file_location` + `module_from_spec` + `exec_module` runs the parser without ever entering `sys.modules`.

I also hardened the report channel: the marker includes a per-run random nonce and exactly one report line is required. That was a small change inside the reporting code being rewritten anyway: a verifier printing a fake report and then `os._exit(0)` now fails.

**2. Static check (defence in depth).** `_EVALUATING_NAMES = {get_type_hints, ForwardRef, _eval_type, _evaluate, register, evaluate, resolve_name}` is rejected in three forms:
- as a bare name (`forbidden name`);
- as an attribute (`forbidden attribute`);
- as an imported name (`forbidden name: from typing import get_type_hints`; aliasing it does not help).

The existing `_FORBIDDEN_NAMES` are now also rejected when imported with `from`. A string-constant annotation on any `ast.arg` (args, *args, **kwargs), any `AnnAssign`, or any `returns` of def / async def is rejected with `string annotation not allowed`. Unquoted annotations stay fine, including under `from __future__ import annotations`. Dataclasses (with `Literal['.', ',']` inside a subscript, `field(...)`, and annotated locals) still register.

**3. Docstrings.** register_verifier: the static check is lint; the runtime guard checks module names AND file origins (and opened files). independence.py lists what remains undetectable: a verifier that embeds a re-implementation of the parser's logic. Reading is not importing, and adapter reviewers must confirm the verifier reads the independent channel. Note that merely *opening* the parser's source file from inside the verifier's run is now caught by the opened-files check.

## Covering tests
- `test_independence.py::test_parser_loaded_by_path_under_another_name_fails[True|False]`. This is the gadget in the scratch layout: `typing.get_type_hints` on a function whose string annotation calls `_load()`, which loads `ingest/sources/acme.py` by path as `zz` via `exec_module`, with and without `sys.modules['zz'] = m`. Each case fails with a message naming the module (`zz from …/acme.py`) or the opened file. A LEAK file written by the scratch parser proves the parser really ran in the child.
- `test_clean_verifier_importing_sources_package_passes` (importing `ingest.sources` for Source/RawResponse opens only the shared `__init__`), plus the existing `test_clean_verifier_passes`.
- `test_verify.py::test_registration_bypasses_are_rejected[...]` gains 20 cases: the 7 names as names, attributes (incl. `singledispatch(len).register`, `typing._eval_type`, `x._evaluate`) and imports (incl. `as g`), and string annotations on arg, *args/**kwargs, returns, async returns and AnnAssign.
- Positive: `test_independent_verifier_is_registered[...]` gains a dataclass/annotation case; `test_future_annotations_module_with_dataclass_is_registered` is new.

## Evidence
RED: the new tests against the round-3 code (0f766b2, detached worktree):
```
FAILED tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from typing import get_type_hints-forbidden name]
FAILED tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from typing import get_type_hints as g\nP = g-forbidden name]
FAILED tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from typing import ForwardRef-forbidden name]
FAILED tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = get_type_hints-forbidden name]
FAILED tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = ForwardRef-forbidden name]
FAILED tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = register-forbidden name]
FAILED tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = evaluate-forbidden name]
FAILED tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = resolve_name-forbidden name]
FAILED tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import typing\nP = typing.get_type_hints-forbidden attribute]
FAILED tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import typing\nP = typing.ForwardRef('x')-forbidden attribute]
FAILED tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import typing\nP = typing._eval_type-forbidden attribute]
FAILED tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[x = object()\nP = x._evaluate-forbidden attribute]
FAILED tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from functools import singledispatch\nP = singledispatch(len).register-forbidden attribute]
FAILED tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[x = object()\nP = x.evaluate-forbidden attribute]
FAILED tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[x = object()\nP = x.resolve_name-forbidden attribute]
FAILED tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[def f(x: '__import__("os")'):\n    pass-string annotation not allowed]
FAILED tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[def f(*a: 'int', **k: 'int'):\n    pass-string annotation not allowed]
FAILED tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[def f() -> 'int':\n    pass-string annotation not allowed]
FAILED tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[async def f() -> 'int':\n    pass-string annotation not allowed]
FAILED tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[x: 'int' = 1-string annotation not allowed]
FAILED tests/ingest/test_independence.py::test_parser_loaded_by_path_under_another_name_fails[True-loaded collector/blocked code under another name: \\['zz from .*/ingest/sources/acme\\.py'\\]]
FAILED tests/ingest/test_independence.py::test_parser_loaded_by_path_under_another_name_fails[False-opened collector/blocked files: \\['.*/ingest/sources/acme\\.py']
======================= 22 failed, 161 passed in 17.60s ========================
```
Gadget probe BEFORE (reviewer's h.py + cases.py against a scratchpad copy of /tmp/t7r4/repo with the round-3 code; LEAK path redirected):
```
PATH load executes parser                STATIC-ACCEPT  GUARD-PASS(evades)
PATH load exec_module                    STATIC-ACCEPT  guard-catches: TypeError: Forward references must evaluate to types. Got (None, 1).
catch ImportError & continue             STATIC-ACCEPT  GUARD-PASS(evades)
catch ImportError, import ok name        static-reject: ode with its parser: ingest.sources.acme', 'shares code with its parser: ingest.validate']
stdout noise                             STATIC-ACCEPT  GUARD-PASS(evades)
hang                                     STATIC-ACCEPT  guard-catches: verifier vm_293b3de1 timed out after 15s
sys.exit(0) partial                      STATIC-ACCEPT  guard-catches: verifier vm_17e2a934: no module report from the child
nonzero exit                             STATIC-ACCEPT  guard-catches: verifier vm_f9647a5d failed under the independence guard (exit 3):
prepopulate sys.modules(typing hint)     STATIC-ACCEPT  guard-catches: verifier vm_b1e84bdf loaded blocked modules: ['ingest.sources.acme']
fake report via stdout, exit 0 early     STATIC-ACCEPT  guard-catches: verifier vm_c459f5ad: no module report from the child
```
Gadget probe AFTER (same, with this commit's `ingest/verifiers/`): the gadgets are now rejected statically:
```
PATH load executes parser                static-reject: ter/ingest/sources/acme.py\'), __import__(\'importlib.util\').util.module_from_spec(m)]"']
PATH load exec_module                    static-reject: 6/scratchpad/t7r4after/ingest/sources/acme.py\')))(__import__(\'importlib.util\').util)"']
catch ImportError & continue             static-reject: : get_type_hints', 'string annotation not allowed: "__import__(\'ingest.sources.acme\')"']
catch ImportError, import ok name        static-reject: ode with its parser: ingest.sources.acme', 'shares code with its parser: ingest.validate']
stdout noise                             STATIC-ACCEPT  GUARD-PASS(evades)
hang                                     STATIC-ACCEPT  guard-catches: verifier vm_2084ddc2 timed out after 15s
sys.exit(0) partial                      STATIC-ACCEPT  guard-catches: verifier vm_875ce6e7: expected one report from the child, got 0
nonzero exit                             STATIC-ACCEPT  guard-catches: verifier vm_747fbe59 failed under the independence guard (exit 3):
prepopulate sys.modules(typing hint)     static-reject: ation not allowed: "__import__(\'sys\').modules.__setitem__(\'ingest.sources.acme\', 1)"']
fake report via stdout, exit 0 early     static-reject: den name: get_type_hints', 'string annotation not allowed: "__import__(\'os\')._exit(0)"']
```
Guard alone (registration skipped, so every case reaches the runtime guard). "PATH load exec_module" in cases.py fails on its own TypeError (the annotation returns a tuple), so two `-> int` variants were added; the scratch parser appends its process's argv[0] to LEAK (`-c` = the guard's child, otherwise h.py's own parent process, which imports the parser at the top):
```
== r4h_one
PATH load executes parser                (static skipped)  GUARD-PASS(evades)
LEAK:
parser executed in argv0=/tmp/claude-1000/-home-joao/0cf85576-cadd-4c92-a5b2-4aac697971e6/scratchpad/r4h_one.py
== r4h_focus
PATH load executes parser                (static skipped)  GUARD-PASS(evades)
PATH load exec_module -> int (variant)   (static skipped)  guard-catches: verifier vm_20a553a7 opened collector/blocked files: ['/tmp/claude-1000/-home-joao/0cf8557
PATH load exec_module + sys.modules['zz'] (variant) (static skipped)  guard-catches: verifier vm_754ea2f6 loaded collector/blocked code under another name: ['zz from /tmp/clau
LEAK:
parser executed in argv0=/tmp/claude-1000/-home-joao/0cf85576-cadd-4c92-a5b2-4aac697971e6/scratchpad/r4h_focus.py
parser executed in argv0=-c
parser executed in argv0=-c
```
Reading of this output:
- "PATH load executes parser" passes the guard, but it only calls `spec_from_file_location` + `module_from_spec`, which neither execute nor open the parser. LEAK shows the parser ran only in the parent, never in the child.
- Both variants that actually run the parser in the child are caught: one by the opened-files check, one by the module-origin check (`zz from …`).
- "catch ImportError & continue", "catch ImportError, import ok name" and "stdout noise" pass the guard because the parser is never loaded (blocked, or just a printed string). Correct.

Full guard-only run over the reviewer's cases:
```
PATH load executes parser                (static skipped)  GUARD-PASS(evades)
PATH load exec_module                    (static skipped)  guard-catches: TypeError: Forward references must evaluate to types. Got (None, 1).
catch ImportError & continue             (static skipped)  GUARD-PASS(evades)
catch ImportError, import ok name        (static skipped)  GUARD-PASS(evades)
stdout noise                             (static skipped)  GUARD-PASS(evades)
hang                                     (static skipped)  guard-catches: verifier vm_ece4f435 timed out after 15s
sys.exit(0) partial                      (static skipped)  guard-catches: verifier vm_e7ca0d2b: expected one report from the child, got 0
nonzero exit                             (static skipped)  guard-catches: verifier vm_dfc41cbf failed under the independence guard (exit 3):
prepopulate sys.modules(typing hint)     (static skipped)  guard-catches: verifier vm_c142ab25 loaded blocked modules: ['ingest.sources.acme']
fake report via stdout, exit 0 early     (static skipped)  guard-catches: verifier vm_b1cb6a29: expected one report from the child, got 0
```

GREEN: `/home/joao/projects/prumo-pipeline/.venv-ci/bin/python -m pytest tests/ingest -v` (verification-related part and total):
```
tests/ingest/test_independence.py::test_clean_verifier_passes PASSED     [  7%]
tests/ingest/test_independence.py::test_helper_importing_the_parser_fails PASSED [  7%]
tests/ingest/test_independence.py::test_non_shared_ingest_modules_fail PASSED [  7%]
tests/ingest/test_independence.py::test_blocked_prefixes_are_enforced PASSED [  7%]
tests/ingest/test_independence.py::test_entrypoint_exception_is_readable PASSED [  8%]
tests/ingest/test_independence.py::test_parser_loaded_by_path_under_another_name_fails[True-loaded collector/blocked code under another name: \\['zz from .*/ingest/sources/acme\\.py'\\]] PASSED [  8%]
tests/ingest/test_independence.py::test_parser_loaded_by_path_under_another_name_fails[False-opened collector/blocked files: \\['.*/ingest/sources/acme\\.py'] PASSED [  8%]
tests/ingest/test_independence.py::test_clean_verifier_importing_sources_package_passes PASSED [  9%]
tests/ingest/test_verify.py::test_sample_always_includes_latest_period_of_each_series PASSED [ 52%]
tests/ingest/test_verify.py::test_sample_is_reproducible_from_seed PASSED [ 52%]
tests/ingest/test_verify.py::test_sample_covers_every_series_even_when_size_smaller PASSED [ 53%]
tests/ingest/test_verify.py::test_sample_takes_every_observation_when_size_exceeds_run PASSED [ 53%]
tests/ingest/test_verify.py::test_sample_rejects_unknown_series_and_bad_size PASSED [ 53%]
tests/ingest/test_verify.py::test_all_match_marks_verified PASSED        [ 53%]
tests/ingest/test_verify.py::test_single_mismatch_marks_failed_and_not_served PASSED [ 54%]
tests/ingest/test_verify.py::test_none_observed_counts_as_mismatch PASSED [ 54%]
tests/ingest/test_verify.py::test_verification_items_store_evidence_url PASSED [ 54%]
tests/ingest/test_verify.py::test_decimal_comparison_is_exact_not_float[1.10-1,1-,-True] PASSED [ 54%]
tests/ingest/test_verify.py::test_decimal_comparison_is_exact_not_float[1.10-1.1-.-True] PASSED [ 55%]
tests/ingest/test_verify.py::test_decimal_comparison_is_exact_not_float[1 234.5-1.234,50-,-True] PASSED [ 55%]
tests/ingest/test_verify.py::test_decimal_comparison_is_exact_not_float[1.10-1.1000001-.-False] PASSED [ 55%]
tests/ingest/test_verify.py::test_decimal_comparison_is_exact_not_float[0.30000000000000004-0.3-.-False] PASSED [ 56%]
tests/ingest/test_verify.py::test_decimal_comparison_is_exact_not_float[1.10-1,1-.-False] PASSED [ 56%]
tests/ingest/test_verify.py::test_decimal_comparison_is_exact_not_float[1.10-n/d-.-False] PASSED [ 56%]
tests/ingest/test_verify.py::test_unit_or_flag_mismatch_fails[kw0-True] PASSED [ 56%]
tests/ingest/test_verify.py::test_unit_or_flag_mismatch_fails[kw1-True] PASSED [ 57%]
tests/ingest/test_verify.py::test_unit_or_flag_mismatch_fails[kw2-False] PASSED [ 57%]
tests/ingest/test_verify.py::test_unit_or_flag_mismatch_fails[kw3-False] PASSED [ 57%]
tests/ingest/test_verify.py::test_unit_or_flag_mismatch_fails[kw4-True] PASSED [ 57%]
tests/ingest/test_verify.py::test_verifier_exception_is_failure_not_pass PASSED [ 58%]
tests/ingest/test_verify.py::test_wrong_result_count_is_failure PASSED   [ 58%]
tests/ingest/test_verify.py::test_out_of_order_result_is_failure PASSED  [ 58%]
tests/ingest/test_verify.py::test_duplicate_key_result_is_failure PASSED [ 59%]
tests/ingest/test_verify.py::test_parser_swapped_periods_with_reordered_verifier_fails PASSED [ 59%]
tests/ingest/test_verify.py::test_verifier_gets_blinded_items PASSED     [ 59%]
tests/ingest/test_verify.py::test_echoing_what_it_is_given_cannot_pass PASSED [ 59%]
tests/ingest/test_verify.py::test_refuses_to_verify_non_pending_run PASSED [ 60%]
tests/ingest/test_verify.py::test_random_seed_is_stored_when_not_given PASSED [ 60%]
tests/ingest/test_verify.py::test_malformed_result_fields_are_failure_not_crash PASSED [ 60%]
tests/ingest/test_verify.py::test_str_subclass_fields_are_failure[observed_text] PASSED [ 60%]
tests/ingest/test_verify.py::test_str_subclass_fields_are_failure[observed_unit] PASSED [ 61%]
tests/ingest/test_verify.py::test_str_subclass_fields_are_failure[series_id] PASSED [ 61%]
tests/ingest/test_verify.py::test_replay_refuses_legacy_item PASSED      [ 61%]
tests/ingest/test_verify.py::test_concurrent_verify_loser_is_rolled_back[inner_truth0-failed-verification] PASSED [ 62%]
tests/ingest/test_verify.py::test_concurrent_verify_loser_is_rolled_back[inner_truth1-verified] PASSED [ 62%]
tests/ingest/test_verify.py::test_evidence_bytes_saved_and_items_replayable PASSED [ 62%]
tests/ingest/test_verify.py::test_replay_needs_no_registry_and_reproduces_every_outcome PASSED [ 62%]
tests/ingest/test_verify.py::test_replay_detects_tampered_evidence PASSED [ 63%]
tests/ingest/test_verify.py::test_evidence_without_store_is_refused PASSED [ 63%]
tests/ingest/test_verify.py::test_refetch_uses_new_seed_each_attempt PASSED [ 63%]
tests/ingest/test_verify.py::test_gives_up_after_max_attempts_and_stays_unserved PASSED [ 63%]
tests/ingest/test_verify.py::test_previously_verified_data_still_served_after_failed_verification PASSED [ 64%]
tests/ingest/test_verify.py::test_short_circuit_run_gets_no_verification_row PASSED [ 64%]
tests/ingest/test_verify.py::test_failed_fetch_is_returned_without_verification PASSED [ 64%]
tests/ingest/test_verify.py::test_refetch_requires_the_registered_verifier PASSED [ 65%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import ingest.sources.acme] PASSED [ 65%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from ingest.sources.acme import parse] PASSED [ 65%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from ingest.sources import acme] PASSED [ 65%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from ingest.sources import eurostat] PASSED [ 66%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import ingest.sources.eurostat as e] PASSED [ 66%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from ingest.sources import validate_helper] PASSED [ 66%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import importlib\nP = importlib.import_module('ingest.sources.acme')] PASSED [ 66%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from importlib import import_module] PASSED [ 67%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[P = __import__('ingest.sources.acme')] PASSED [ 67%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from ingest import sources\nP = sources.acme] PASSED [ 67%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from ingest import sources as s] PASSED [ 68%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import ingest.sources\nP = ingest.sources.acme] PASSED [ 68%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import ingest\nP = ingest.sources.acme] PASSED [ 68%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[exec('from ingest.sources.acme import parse')] PASSED [ 68%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[eval('1')] PASSED [ 69%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import sys\nP = sys.modules['ingest.sources.acme']] PASSED [ 69%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from sys import modules] PASSED [ 69%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import ACME] PASSED [ 69%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[import acme] PASSED [ 70%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from vendor.Acme import parse] PASSED [ 70%]
tests/ingest/test_verify.py::test_verifier_importing_parser_is_rejected[from vendor import acme] PASSED [ 70%]
tests/ingest/test_verify.py::test_independent_verifier_is_registered[] PASSED [ 71%]
tests/ingest/test_verify.py::test_independent_verifier_is_registered[code1] PASSED [ 71%]
tests/ingest/test_verify.py::test_independent_verifier_is_registered[import re\nP = re.compile('x')] PASSED [ 71%]
tests/ingest/test_verify.py::test_independent_verifier_is_registered[import json\nimport csv\nfrom decimal import Decimal\nfrom dataclasses import dataclass] PASSED [ 71%]
tests/ingest/test_verify.py::test_independent_verifier_is_registered[import urllib.parse\nP = urllib.parse.urlencode({})] PASSED [ 72%]
tests/ingest/test_verify.py::test_independent_verifier_is_registered[import xml.etree.ElementTree as ET\nP = ET.fromstring] PASSED [ 72%]
tests/ingest/test_verify.py::test_independent_verifier_is_registered[import logging\nlog = logging.getLogger('x')] PASSED [ 72%]
tests/ingest/test_verify.py::test_independent_verifier_is_registered[from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from ingest.http import Http] PASSED [ 72%]
tests/ingest/test_verify.py::test_independent_verifier_is_registered[code8] PASSED [ 73%]
tests/ingest/test_verify.py::test_future_annotations_module_with_dataclass_is_registered PASSED [ 73%]
tests/ingest/test_verify.py::test_shared_helper_with_parser_is_rejected PASSED [ 73%]
tests/ingest/test_verify.py::test_only_allow_listed_shared_modules_is_accepted PASSED [ 74%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import ingest.http\nP = ingest.sources.acme.parse_rows-import not allowed (use 'from ingest.<module> import <name>')] PASSED [ 74%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import ingest.models\nP = ingest.sources.acme-import not allowed (use 'from ingest.<module> import <name>')] PASSED [ 74%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import ingest.rawstore-import not allowed (use 'from ingest.<module> import <name>')] PASSED [ 74%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import ingest.http as h-import not allowed (use 'from ingest.<module> import <name>')] PASSED [ 75%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import ingest-import not allowed (use 'from ingest.<module> import <name>')] PASSED [ 75%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.verifiers import ingest as i\nP = i.sources-name not in allowlist for] PASSED [ 75%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import sys as s\nP = s.modules['ingest.sources.acme']-module not in stdlib allowlist] PASSED [ 75%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from sys import modules-module not in stdlib allowlist] PASSED [ 76%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import builtins\nP = builtins.__import__('ingest.sources.acme')-module not in stdlib allowlist] PASSED [ 76%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from builtins import __import__ as imp-module not in stdlib allowlist] PASSED [ 76%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import runpy-module not in stdlib allowlist] PASSED [ 77%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import pkgutil\nP = pkgutil.resolve_name('ingest.sources.acme:parse_rows')-module not in stdlib allowlist] PASSED [ 77%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import importlib-module not in stdlib allowlist] PASSED [ 77%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from importlib import import_module-module not in stdlib allowlist] PASSED [ 77%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import sqlite3-module not in stdlib allowlist] PASSED [ 78%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import requests-module not in stdlib allowlist] PASSED [ 78%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import os-module not in stdlib allowlist] PASSED [ 78%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.db import open_db-ingest module not in allowlist] PASSED [ 78%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest import db-ingest module not in allowlist] PASSED [ 79%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.sources.acme import parse_rows-ingest module not in allowlist] PASSED [ 79%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest import sources-ingest module not in allowlist] PASSED [ 79%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.sources import acme-name not in allowlist for] PASSED [ 80%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from ingest.sources.acme import parse_rows-ingest module not in allowlist] PASSED [ 80%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[try:\n    from ingest.sources import acme\nexcept ImportError:\n    pass-name not in allowlist for] PASSED [ 80%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import ACME-source-named import] PASSED [ 80%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest import verifiers as v\nP = v.ingest.sources.acme-ingest module not in allowlist] PASSED [ 81%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest import verifiers as v\nP = v.sys.modules['ingest.sources.acme']-ingest module not in allowlist] PASSED [ 81%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest import models as m\nP = m.re-ingest module not in allowlist] PASSED [ 81%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest import http as h\nP = h.requests-ingest module not in allowlist] PASSED [ 81%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.http import requests-name not in allowlist for] PASSED [ 82%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.http import time-name not in allowlist for] PASSED [ 82%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.verifiers import sys-name not in allowlist for] PASSED [ 82%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import logging\nP = logging.sys.modules-attribute chain reaches module not in allowlist] PASSED [ 83%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import urllib.parse\nP = urllib.request-attribute chain reaches module not in allowlist] PASSED [ 83%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from logging import sys-module not in stdlib allowlist] PASSED [ 83%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from collections import _collections_abc-private name not allowed] PASSED [ 83%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[code36-dunder attribute] PASSED [ 84%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.models import parse_number\nP = parse_number.__builtins__-dunder attribute] PASSED [ 84%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.sources import RawResponse\nP = RawResponse.__init__-dunder attribute] PASSED [ 84%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.verifiers import BlindItem\nP = type(BlindItem).__mro__-forbidden name] PASSED [ 84%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.verifiers import BlindItem\nP = BlindItem.__mro__-dunder attribute] PASSED [ 85%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[x = object().__import__-dunder attribute] PASSED [ 85%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = __loader__-forbidden name] PASSED [ 85%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = __spec__-forbidden name] PASSED [ 86%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = __globals__-forbidden name] PASSED [ 86%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = __import__('ingest.sources.acme')-forbidden name] PASSED [ 86%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = __builtins__-forbidden name] PASSED [ 86%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = vars(object)-forbidden name] PASSED [ 87%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = globals()['__builtins__']-forbidden name] PASSED [ 87%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = locals()-forbidden name] PASSED [ 87%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[exec('import ingest.sources.acme')-forbidden name] PASSED [ 87%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[eval('1')-forbidden name] PASSED [ 88%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = compile('1', 'f', 'eval')-forbidden name] PASSED [ 88%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = getattr(object, 'x')-forbidden name] PASSED [ 88%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[setattr(object, 'x', 1)-forbidden name] PASSED [ 89%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[delattr(object, 'x')-forbidden name] PASSED [ 89%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = super-forbidden name] PASSED [ 89%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = open('f')-forbidden name] PASSED [ 89%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from typing import get_type_hints-forbidden name] PASSED [ 90%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from typing import get_type_hints as g\nP = g-forbidden name] PASSED [ 90%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from typing import ForwardRef-forbidden name] PASSED [ 90%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = get_type_hints-forbidden name] PASSED [ 90%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = ForwardRef-forbidden name] PASSED [ 91%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = register-forbidden name] PASSED [ 91%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = evaluate-forbidden name] PASSED [ 91%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[P = resolve_name-forbidden name] PASSED [ 92%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import typing\nP = typing.get_type_hints-forbidden attribute] PASSED [ 92%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import typing\nP = typing.ForwardRef('x')-forbidden attribute] PASSED [ 92%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[import typing\nP = typing._eval_type-forbidden attribute] PASSED [ 92%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[x = object()\nP = x._evaluate-forbidden attribute] PASSED [ 93%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from functools import singledispatch\nP = singledispatch(len).register-forbidden attribute] PASSED [ 93%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[x = object()\nP = x.evaluate-forbidden attribute] PASSED [ 93%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[x = object()\nP = x.resolve_name-forbidden attribute] PASSED [ 93%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[def f(x: '__import__("os")'):\n    pass-string annotation not allowed] PASSED [ 94%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[def f(*a: 'int', **k: 'int'):\n    pass-string annotation not allowed] PASSED [ 94%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[def f() -> 'int':\n    pass-string annotation not allowed] PASSED [ 94%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[async def f() -> 'int':\n    pass-string annotation not allowed] PASSED [ 95%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[x: 'int' = 1-string annotation not allowed] PASSED [ 95%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.verifiers import _REGISTRY-name not in allowlist for] PASSED [ 95%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.verifiers import get_verifier-name not in allowlist for] PASSED [ 95%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.verifiers import inspect-name not in allowlist for] PASSED [ 96%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.verifiers import ast-name not in allowlist for] PASSED [ 96%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.verifiers import dataclass-name not in allowlist for] PASSED [ 96%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.http import urljoin-name not in allowlist for] PASSED [ 96%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.models import Observation-name not in allowlist for] PASSED [ 97%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from ingest.rawstore import Path-name not in allowlist for] PASSED [ 97%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from . import acme-relative import not allowed] PASSED [ 97%]
tests/ingest/test_verify.py::test_registration_bypasses_are_rejected[from .. import sources-relative import not allowed] PASSED [ 98%]
tests/ingest/test_verify.py::test_star_imports_are_rejected[from ingest.http import *] PASSED [ 98%]
tests/ingest/test_verify.py::test_star_imports_are_rejected[from ingest.models import *] PASSED [ 98%]
tests/ingest/test_verify.py::test_star_imports_are_rejected[from ingest.verifiers import *] PASSED [ 98%]
tests/ingest/test_verify.py::test_star_imports_are_rejected[from ingest.sources import *] PASSED [ 99%]
tests/ingest/test_verify.py::test_star_imports_are_rejected[from json import *] PASSED [ 99%]
tests/ingest/test_verify.py::test_duplicate_registration_is_rejected PASSED [ 99%]
tests/ingest/test_verify.py::test_fake_verifier_module_passes_the_rule PASSED [100%]
============================= 366 passed in 32.61s =============================
```

## Concerns (round 4)
- The audit-hook record and the report are data inside the child process. A verifier with arbitrary runtime code could in principle tamper with them, e.g. by finding the hook's set through introspection, which static rules forbid but runtime-built code could reach. The guard is a strong test harness, not a sandbox; the adapter review stays the backstop.
- `_EVALUATING_NAMES` includes generic words (`register`, `evaluate`). A verifier attribute or method with those names (e.g. `self.register`) is rejected. Deliberate, per the ruling, and cheap to rename.
- Only top-level string annotations are rejected (as ruled). A quoted forward ref nested in a subscript (`list["X"]`) is allowed, which is harmless without an evaluator, and those are forbidden.
