# Task 16 independent spec review: E-REDES native PT15M pipeline

Verdict: **REQUEST_CHANGES**

Scope per controller instructions: spec compliance on commits ec62566 / a611a9a / 5a220e5 /
5bd312d against `task-16-brief.md`, read-only. No network, no production reads/writes, no code
or shared-doc edits. Targeted offline tests and adversarial probes only (scratch:
`~/.cache/../.hermes/cache/scratch/t16-spec-review-m0xk9/`, i.e. uniquely named under
`/home/joao/.hermes/cache/scratch`). Controller is running the fresh whole suite; the claimed
"1231 passed" was not re-verified here and the live E-REDES gate remains controller-owned and
unrun — this verdict addresses **code acceptance only**, not live acceptance.

## What was verified as compliant

- **PT15M DB contract (migration 0006)**: canonical 25-char spelling enforced by exact-length
  GLOB + strftime UTC round-trip + explicit hour/minute/second bounds on both insert and update
  triggers; served view re-created **verbatim** from 0005 (textually identical, diff-verified).
  Adversarial inserts on a scratch DB all rejected: `2026-02-30…`, `2026-11-31…`, `24:00:00`,
  `+01:00` offset, `Z` spelling, trailing junk, fullwidth-year token; A-series arm unchanged.
- **Populated-0005 upgrade**: `test_0006_upgrades_populated_0005_and_preserves_everything`
  exercises observations (fetched + legacy), raw_fetch provenance, verification rows, settings,
  served view + licence gate (blocked source serves zero, CC-BY serves), FK enforcement
  post-rebuild, repeated-open idempotence. Passes.
- **Genuine fixtures**: sha256 of all three bodies match MANIFEST.json; statuses 200, final
  URLs and fetch timestamps recorded; metadata independently decoded: dataset_id
  `energia-produzida-total-nacional`, licence `CC BY 4.0` + URL, publisher `E-REDES`, fields
  `dgm/pre/total` double with labels `Market (kWh)`/`Special Regime (kWh)`/`Total (kWh)`; JSON
  window has total_count 96 == 96 results, strictly ascending unique canonical timestamps; CSV
  has BOM/CRLF/expected header; **all 288 value tokens byte-identical between JSON and CSV**
  (recomputed). The report's 5 named genuine samples (925741.0, 523992.0, 1340285.0,
  1551219.0, 1097652.0) all match the fixture bytes. Discovery's truncated probes not reused.
- **Source adapter** (`ingest/sources/eredes.py`): explicit day-aligned `[from_ts, to_ts)`
  windows + bounded 3-complete-day default; per-day requests make the 100-record page /
  10000-offset caps unreachable (density beyond that raises, never truncates); per-window
  completeness asserted (constant total_count, contiguous offsets, chunk length == total_count);
  tagged JSON-number tokens (quoted numbers, duplicate keys rejected); plain `str` into RawRow;
  negative dgm preserved; echo columns dia/mes/ano/date/time asserted against datahora; unknown
  record keys / metadata drift / HTML-200 / non-2xx fail closed; metadata archived as evidence;
  RawRow.response_index points at the records page. Throttle: `RequestsHttp` default is 1 req/s
  and registry sets `schedule: 1d` (no throttle override needed; ≤1 rps holds).
- **Verifier** (`ingest/verifiers/eredes.py`): genuinely different endpoint+format
  (`/exports/csv?lang=pt&timezone=UTC`), no import from the collector (constants duplicated);
  periods string-matched from the CSV's own canonical tokens; missing row → `observed_text=None`
  (mismatch, not invention); unit evidence from metadata labels → kWh; observed_flag=None honest
  (no flag surface); `eredes-csv-evidence` v1 envelope carries deciding CSV + metadata bodies,
  final URLs, actual statuses.
- **Tests**: 173 targeted tests across test_migration_pt15m / test_models / test_registry_eredes_units /
  test_source_eredes / test_verifier_eredes all pass offline (`.venv-ci/bin/python`, 10.3 s),
  including registration-AST, subprocess independence, tamper (value + unit label), HTML on both
  channels, offline archive recovery + replay, served-under-CC-BY, run_with_refetch. Commit
  paths are all task-owned; controller dirty docs/plan/discovery files untouched; dadosgov and
  the legacy E-REDES collector preserved; no push/merge.

## Spec gaps requiring changes

### R1 — Common migrator's integrity check is not atomic and silently disables itself afterwards

Contract (controller review spec): the common migrator must **fail atomically on constraints,
not leave a corrupt applied migration if the integrity check detects failure**.

Evidence in code (`ingest/db.py`):
- `_migrate` executes each pending file in its own `BEGIN; … COMMIT;` (line 241), including the
  `INSERT INTO schema_migration` record, so each file commits before the check runs.
- `PRAGMA foreign_key_check` runs **after** all commits (line 246) and merely raises.
- Line 228 `if not pending: return` means the check is skipped on every later open once the
  corrupt migration is recorded.

Adversarial probe (scratch `t16-spec-review-m0xk9/probe3.db`, synthetic `0007_bad.sql` inserting
a `series` row with `source_id=999` — invisible to triggers, allowed under FK-OFF):
first `open_db` raised `RuntimeError: foreign key violations after migration`, but the corrupt
row **and** the `0007_bad` record in `schema_migration` were already committed; the **second**
`open_db` then succeeded with the corruption intact, because `pending` was empty and no check
ran. The safety mechanism therefore detects failure exactly once, leaves the corrupt migration
applied and recorded, and never re-checks — precisely the non-atomic outcome the spec forbids.
(Failure requires a buggy future migration, but 0006's FK-OFF rebuild makes that reachable; the
check exists to catch exactly this.) Fix direction (not applied): run the integrity check inside
each migration's transaction before COMMIT, or wrap the pending set + check in one outer
transaction so failure rolls back the `schema_migration` record too.

### R2 — `normalize_period` PT15M arm silently accepts non-ASCII / non-canonical spellings via `_fold`

Contract (brief §"Frequency"): single canonical UTC spelling, **ASCII digits required**,
non-canonical spellings rejected rather than guessed; the module comment claims
"non-ASCII digits … is rejected".

Evidence (`ingest/models.py`): the PT15M pattern (lines 37-38) is matched against
`text = _fold(raw)` (line 46), where `_fold` applies NFKD + lower + strip. Consequences,
probe-verified:
- `'２０２６-１１-１０Ｔ２３：４５：００＋００：００'` (fullwidth digits/colon/plus) is
  **accepted** and canonicalized to `2026-11-10T23:45:00+00:00` — non-ASCII digits normalized
  instead of rejected, contradicting both the brief and the inline comment.
- Lowercase `'…t23:45:00+00:00'` and surrounding whitespace (`'…+00:00 '`) are also accepted
  (the case fold is documented in the implementation report; the digit/whitespace folds are not
  documented anywhere).

Impact is bounded: `EredesSource.parse` rejects any non-ASCII-canonical `datahora` before
normalization, and the SQL triggers' GLOBs are ASCII-only, so no malformed token can reach
stored observations through the T16 adapter. But `normalize_period` is the shared contract
(GitNexus CRITICAL, 4 direct callers) and the PT15M arm deviates from the stated strictness; a
future PT15M producer relying on the contract alone would admit folded tokens. Fix direction:
match the PT15M pattern against the raw string (skip `_fold`) or assert `raw == emitted`.

## Process notes (not code findings)

- TDD "failing tests before implementation" cannot be evidenced from history — tests and
  implementation share each slice commit. Unverifiable, not asserted as a violation.
- The "1231 passed" full-suite claim was not re-run here by instruction; targeted offline suites
  (173 tests) pass. Live acceptance (fresh E-REDES portal fetch/verify) is controller-owned,
  unrun, and remains the gate.
- The implementation report's value-tokens claim, named samples, fixture budget/URLs/statuses,
  and migration-safety narrative were independently re-verified and (except R1/R2) hold.

Reviewed by: independent spec reviewer (subagent), 2026-11-12. Task 16 **not** marked closed.
