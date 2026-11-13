# Task 19 specification fix round 1

Bounded F1/F2 corrections implemented and focused offline checks passed. This report does not grant specification acceptance, quality approval, Task 18 closure or final owner acceptance.

## Scope and impact

Worked in `/home/joao/projects/prumo-pipeline`, branch `pipeline-rebuild`, intake HEAD `1953671`. Read the assigned fix brief, F1/F2 specification findings, auditor, exporter, checkpoint report, manifest and existing probe receipt; checked adjacent references directly.

Before changing the existing `audit` function, ran local `gitnexus impact audit --direction upstream --repo prumo`. It returned `Target 'audit' not found`, risk `UNKNOWN`. GitNexus status reported the indexed/current commit as `1953671` and up-to-date, but this new untracked evidence helper is outside intake graph coverage. Its reported zero impacted count cannot establish zero real callers or affected processes. Direct reference inspection found the standalone CLI invocation in the checkpoint report and audit/review-package references, not an application integration. No reindex was performed.

Only authorized package paths were written:

- `evidence/task-18/worldbank-offline-audit.py`
- `task-18-observation-checkpoint.md`
- `evidence/task-18/checkpoint-20261113T083638Z/worldbank-offline-audit-result.json`
- `evidence/task-18/checkpoint-20261113T083638Z/MANIFEST.json`
- `evidence/task-18/worldbank-audit-negative-probes.json`
- New durable focused runner: `evidence/task-18/worldbank-audit-probes.py`
- This report: `task-19-spec-fix-1.md`

All paths in that list are relative to `docs/superpowers/handoff/reports/`. No application, registry, application-test, protected-instruction or controller-state document was edited. The exporter is unchanged. No network, production access, delegation, staging, commit, push, deployment or whole-suite execution occurred.

## F1: distinct recorded times

Renamed auditor output `final_verified_at` to `last_processing_finished_at`; its value still comes exclusively from the maximum run `finished_at`. No verification field was retrofitted into the original capsule.

The checkpoint report now distinguishes:

- Last processing finish/pending verification: `2026-11-13T06:52:25.119769+00:00`, from the archived run records.
- Actual recorded World Bank verification: `2026-11-13T06:52:26.025416+00:00`, read directly from `checkpoint-20261113T083638Z/status-20261113T083638Z.json:12453` (`last_verified`, World Bank source).
- Final `SP.DYN.CDRT.IN` verified scheduler outcome: `2026-11-13T06:52:26.027280+00:00`, read directly from `checkpoint-20261113T083638Z/worker-20261113T083638Z.log:66` (run 60).

Original collector receipt times, checkpoint `2026-11-13T08:36:38.064186+00:00`, and capsule export `2026-11-13T08:46:19.608659+00:00` remain separate and unchanged. The derived JSON contains processing time only; verification and scheduler times are attributed to their existing receipts in the report.

## F2: receipt-specific assertions

The helper now explicitly pins 949 verification items, 18 independent CSV evidence/table envelopes, 18 unique collector receipts, 15,465 null cells and zero other nonnumeric cells. It rejects duplicate `(dataset_run_id, series_id, period)` sample identities. Existing 18-run, 930-series, 45,915-observation, latest-series coverage, per-run sample-size/seed consistency and original evidence/value assertions remain intact. The checkpoint prose names the enforced scope and restricts it to this acceptance receipt, not future data. Independent CSV agreement remains sampled, never an all-row claim.

## Actual RED/GREEN and replay results

The durable stdlib runner was written and executed before editing the auditor. It mutates only in-memory copies, loads the real helper and tests the original gzip plus its decoded in-memory JSON contents.

Pre-fix RED, runner exit 1:

- Original positive replay passed.
- Processing-only timestamp expectation failed.
- Removing `worldbank.rnd_pct_gdp.MX` period `2023` and decrementing that run's remaining `sample_size` declarations was accepted: 948 samples, all 930 latest series covered.
- Replacing that historical item with another item from the same run was accepted: 949 items, all 930 latest series covered. This preserved count and per-run metadata while duplicating a sample identity.
- Altered stored token, altered CSV result, missing latest sample, missing collector receipt, altered sample size and altered seed were already rejected. The missing-receipt pre-fix rejection was a `KeyError`; the receipt records that actual outcome.

Post-fix GREEN, identical runner exit 0:

- Original gzip and in-memory JSON positive replays pass with equal results.
- Processing-only field/value check passes and `final_verified_at` is absent.
- All eight negative probes are rejected. Historical omission fails with `expected 949 verification items`; duplicate replacement fails with `duplicate sample identity`; missing receipt now fails with `expected 18 collector receipts`. Existing token/result/latest/sample-size/seed rejection checks pass.
- A subsequent fresh runner execution exactly matches the appended durable GREEN receipt. Existing original probe fields/results were retained, with actual RED/GREEN outcomes added under `fix_round_1`; no invented subprocess exit codes were assigned to individual in-memory calls.

Commands exercised with the existing environment:

```bash
.venv-ci/bin/python -B docs/superpowers/handoff/reports/evidence/task-18/worldbank-audit-probes.py
.venv-ci/bin/python -B docs/superpowers/handoff/reports/evidence/task-18/worldbank-offline-audit.py docs/superpowers/handoff/reports/evidence/task-18/checkpoint-20261113T083638Z/worldbank-live-evidence.json.gz
.venv-ci/bin/ruff check docs/superpowers/handoff/reports/evidence/task-18/worldbank-offline-audit.py docs/superpowers/handoff/reports/evidence/task-18/worldbank-audit-probes.py
```

Focused Ruff: `All checks passed!`, exit 0. No application behavior tests were run. The controller-provided application-suite result remains separately scoped: 1,460 passed / 7 live deselected / 3 warnings in 384.83 seconds; this run did not independently reproduce it or replace the earlier historical baseline.

## Derived result and byte preservation

Generated the derived result by actually executing the fixed auditor CLI against the original gzip. A fresh second CLI execution matches the stored output byte-for-byte:

- Derived result: 850 bytes, SHA-256 `95a3a0598576c385e263fbe518d6730ed04d6c79ae46f159876a71ed06bcc257`.
- Original capsule: 3,541,615 bytes, SHA-256 `4ac461bc853c36d82ab78763a923c9d7000a3ae7514397482e65975e0ecc04ba`.

Updated only the derived result's hash/size entry in `MANIFEST.json`. All six artifact entries rehash correctly; all five original capsule/audit/status/summary/log entries and manifest metadata match the intake manifest exactly. Original failed-fetch and failed-verification history remains in the capsule and replay output.

An intake SHA-256 snapshot covered all 30 then-current modified/untracked files. Final comparison found only the authorized existing package edits plus out-of-scope hash drift in `DOCS_MAP.md`. This run never wrote that file and did not revert or absorb the concurrent change. The initial strict preservation assertion correctly failed on that drift; the subsequent check reported it explicitly and confirmed every other unrelated intake file unchanged. Therefore this report does not claim that the entire shared working tree stayed byte-identical throughout the run. New paths were confined to the authorized focused runner and this report.

## Still-open gates

Controller independent verification and a separate scoped specification re-review are still required, followed by quality review. F1/F2 implementation here is not an acceptance transition.

Protected `CLAUDE.md` approval remains blocked/open; no protected-file repair or approval bypass occurred. The real Task 18 observation remains open: start `2026-11-13T01:21:18.732242+00:00`, no closure before `2026-11-14T01:21:18.732242+00:00`, then controller review of actual continuity, end receipts and source exceptions. This offline run obtained no later production receipt. `task_18_closed` remains false.

Final owner acceptance, unresolved source/licence dispositions, controller state reconciliation, whole-branch review and any later merge/deployment remain separate open gates. Full Task 19 completion remains `BLOCKED_CLAUDE_APPROVAL_AND_TASK18_WINDOW`.
