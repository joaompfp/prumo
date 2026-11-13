# Task 19 scoped independent F1/F2 specification re-review

Verdict: PASS_AUTHORED_SCOPE

F1 and F2 are resolved in the corrected authored audit package. This verdict is limited to the requested specification re-review; it does not close protected-file approval, the real observation window, quality/controller gates or owner acceptance.

## Boundary

Reviewed in `/home/joao/projects/prumo-pipeline`, branch `pipeline-rebuild`, HEAD `19536716ab27d340e8ef08d67b24bb83ccf5f93f`. Read `task-19-spec-review.md` and `task-19-spec-fix-1.md`, then inspected the actual auditor, focused probe runner, checkpoint prose, gzip capsule, derived result, manifest, negative-probe receipt and relevant archived status/log records.

Only this report was authored. No implementation, evidence, protected instruction, state document or production write was performed. No network requests, delegation, application-suite execution, staging, commit or acceptance-state transition occurred. Python ran with bytecode writes disabled; focused Ruff used `--no-cache`. Previously passed docgen/CLI/documentation scope was not re-audited. The controller-supplied DOCS_MAP correction, controller result of 1,460 passed and unchanged tested application hashes are context, not results newly reproduced here.

## F1: PASS

`evidence/task-18/worldbank-offline-audit.py:179` now reports `last_processing_finished_at`, computed from the archived runs' maximum `finished_at`. The obsolete `final_verified_at` field is absent from actual replay output and the stored derived JSON.

Independently decoded the capsule, parsed the archived status JSON and parsed the worker JSON-lines log. The actual values are:

- Processing finish/pending verification: `2026-11-13T06:52:25.119769+00:00`, maximum capsule run `finished_at`.
- Recorded World Bank verification: `2026-11-13T06:52:26.025416+00:00`, World Bank source `last_verified` in `checkpoint-20261113T083638Z/status-20261113T083638Z.json:12453`.
- Verified scheduler outcome: `2026-11-13T06:52:26.027280+00:00`, source `worldbank`, group `SP.DYN.CDRT.IN`, run 60, state `verified`, in `worker-20261113T083638Z.log:66`.

Parsed datetime ordering confirms processing < verification < scheduler outcome. `task-18-observation-checkpoint.md:29-31` correctly distinguishes these values and their provenance from collector retrieval, checkpoint and export times. Verification is not claimed to exist as a newly added capsule timestamp. The capsule export remains `2026-11-13T08:46:19.608659+00:00`; checkpoint remains `2026-11-13T08:36:38.064186+00:00`.

## F2: PASS

Inspected explicit receipt-specific assertions at auditor lines 51-61, 105-109, 122-124 and 162-167. Independently counted the actual decoded capsule rather than relying solely on returned totals:

| Check | Actual outcome |
|---|---|
| Successful live runs | 18; positive auditor replay checks verified/live state |
| Active series | 930 |
| Stored observations | 45,915; positive replay validates exact original JSON tokens and provenance |
| Collector receipts / unique receipt IDs | 18 / 18 |
| Publisher numeric / null cells | 45,915 / 15,465 from separately decoded original response blobs |
| Other nonnumeric cells | 0 in successful auditor replay |
| Sample items / distinct `(dataset_run_id, series_id, period)` identities | 949 / 949 |
| Independent CSV evidence hashes/envelopes | 18 |
| Latest-observation series covered by samples | 930, independently reconstructed from stored periods |
| Historical failed runs | 17 failed-fetch / 9 failed-verification, counted by unique run ID |

An initial reviewer assertion incorrectly counted historical failure records directly. The capsule has 32 failure records but 26 unique failed run IDs; counting unique IDs reproduces the claimed 17/9 run totals. No evidence was changed to resolve that reviewer-side assertion.

`task-18-observation-checkpoint.md:35-39,51` matches the enforced receipt scope, explicitly requires unique sample identities and preserves the sampled-CSV limitation. It makes no all-row independent CSV agreement claim and does not generalize the fixed counts to future receipts.

## Actual offline executions

- Executed the real `worldbank-offline-audit.py` CLI against the original gzip: exit 0, empty stderr. Captured stdout in memory and compared it byte-for-byte with the stored derived result: identical, 850 bytes.
- Executed the real `worldbank-audit-probes.py`: exit 0, `all_expectations_passed=true`. Original gzip and decoded in-memory JSON positive replays agree. Fresh parsed output exactly equals the durable receipt's `fix_round_1.green` object.
- All supplied negative mutations were rejected: altered stored token, altered CSV result, missing latest sample, historical sample removal with adjusted declared size, count-preserving duplicate replacement, missing collector receipt, altered sample size and altered seed. Historical removal specifically fails with `expected 949 verification items`; duplicate replacement fails with `duplicate sample identity: (36, 'worldbank.rnd_pct_gdp.AO', '2016')`. The missing-latest probe now hits the fixed count assertion first; it is not presented as isolated proof of the later latest-coverage assertion.
- Additional independent in-memory mutations rejected a duplicate collector receipt ID while preserving list length, a removed observation and a removed active series. The duplicate receipt fails with `expected 18 collector receipts`.
- Independent reviewer socket audit hook forbade socket operations during the custom verification process; the exercised auditor also installs its own socket-denying hook. No network was used.
- Focused command `.venv-ci/bin/ruff check --no-cache` on the two evidence helpers: exit 0, `All checks passed!`. No application tests or whole-suite rerun.

## Manifest and byte preservation

Recomputed SHA-256 and byte length for every manifest entry: all six match. The real CLI output matches the derived JSON bytes, whose SHA-256 is `95a3a0598576c385e263fbe518d6730ed04d6c79ae46f159876a71ed06bcc257`.

Original gzip: 3,541,615 bytes, SHA-256 `4ac461bc853c36d82ab78763a923c9d7000a3ae7514397482e65975e0ecc04ba`, matching both the manifest and the original review/fix record. All mutations used in-memory copies. A before/after size-and-hash snapshot of every file under `evidence/task-18/` was identical across the independent replay and mutation checks. No original capsule, response blob, status, audit, summary, log, manifest or probe receipt was rewritten. This is local archive verification, not a fresh production or remote-store audit.

## Gates left open

Protected `CLAUDE.md` approval remains blocked/open. Task 18 remains open: its real observation cannot close before `2026-11-14T01:21:18.732242+00:00`, and still requires controller review of actual continuity, end receipts and source exceptions. This review obtained no later production evidence and did not change `task_18_closed=false`.

Owner acceptance, unresolved source/licence dispositions, controller reconciliation, separate quality review and later whole-branch/merge/deployment gates remain outside this verdict. Full Task 19 completion remains `BLOCKED_CLAUDE_APPROVAL_AND_TASK18_WINDOW`.
