# Task 19 controller review and owner audit package

Authored generator, catalogue, methodology, deployed/manual runbooks and evidence package: specification PASS_AUTHORED_SCOPE and independent quality APPROVED_AUTHORED_SCOPE after bounded corrections. Final controller suite: 1,471 passed / 7 live deselected / 3 warnings. This is not unconditional Task 19 or Project 1 completion: the required CLAUDE.md prefix update remains blocked by protected-file approval, Task 18's actual 24-hour observation is open, and final whole-branch/owner acceptance has not occurred. The source-catalogue code is committed as 9685cb636d49bd4f894dddab16c15ded19094576 on pipeline-rebuild. No new merge or deployment was performed in this continuation.

## Deliverables for owner review

- [Source catalogue](../../../data/sources.md): generated from registry/core.yaml by `python -m ingest docs`; source licences, attribution, exact series/key/native-code tuples, active/inactive/cross-check roles and independently reviewed verification channels.
- [Methodology](../../../data/methodology.md): raw/validated/served stages; native text versus REAL; status mappings; vintage, period/retrieval/processing/verification dates; exact sampled verification and limits; original recorded/legacy data and legal eligibility.
- [Production status and World Bank acceptance](task-18-observation-checkpoint.md): every active source at the intermediate checkpoint, honest source exceptions, complete World Bank fresh acceptance and independently replayable evidence.
- [Operations](../../../data/operations.md) and [manual refresh](../../../data/manual-refresh.md): actual f0nix paths and safe production-write procedure; original-file capture, exact receipt times and per-group stale protection.
- Owner decisions: [authoritative registry](../../../../registry/core.yaml), [overlaps](../../../../registry/overlaps.md), [deferred tail](../../../../registry/deferred-tail.md), [licence decisions](../../../../registry/licences-todo.md), [unverifiable definitions](../../../../registry/unverifiable.md).

All links above are repository-relative. The public app remains maintenance-only; a queryable SQL row is not a public dashboard display.

## Intake, implementation and attribution

Resumed pipeline-rebuild at 19536716ab27d340e8ef08d67b24bb83ccf5f93f. Main/runtime release was already installed on f0nix; the actual deployed image was not rebuilt or interrupted. The original handoff's first serial-pass checkpoint was historical. Read-only production results superseded the old World Bank availability blocker rather than redispatching accepted adapter work.

Fresh 19A and 19B implementers owned file-disjoint code/catalogue and human documentation scopes; reports task-19a-implementation.md and task-19b-implementation.md preserve their actual RED/GREEN checks. The controller owns this report, production receipts, audit synthesis, shared state and the documentation-map permission label. Generated sources retain exact registry/licence/attribution content, including literal typography; human-authored prose uses plain hyphens.

The native delegate_task attempts failed before implementation because pinned kimi-k3/Ollama entitlement was exhausted. A live gpt-6.1-sol/openai-codex one-call probe passed, and fresh implementers/reviewers were launched with per-invocation CLI provider/model flags, without permanent routing changes. Actual usage receipts are summarized in evidence/task-19/agent-routing-receipts.json. The 19B frontend detached with exit 3 on protected-file approval; the specific gateway admission was subsequently read back terminal/completed, with a truthful partial report. That was not permission to bypass the blocked write.

## Scope and regression evidence

The application change is a pure deterministic ingest/docgen.py renderer/registry wrapper and a minimal early docs branch in ingest/cli.py. It performs no operational path resolution, DB/raw-store construction, HTTP setup, verifier registration or ingestion. It honours --registry and retains every source definition, including empty-source fixtures, blocked definitions and inactive entries. The generated current registry catalogue covers all 9 sources and all 1,791 entries; 1,345 are active. Unknown channels stay undocumented. No source/parser/verifier/model/SQL/registry/scheduler/dependency behavior changed.

Controller commands and observed results:

```bash
.venv-ci/bin/python -m pytest tests -q \
  --basetemp=/home/joao/.hermes/cache/scratch/prumo-resume-task19-baseline
# 1435 passed / 7 live deselected / 3 warnings in 329.05s

.venv-ci/bin/python -m pytest tests -q \
  --basetemp=/home/joao/.hermes/cache/scratch/prumo-task19-controller-full
# 1460 passed / 7 live deselected / 3 warnings in 384.83s

.venv-ci/bin/python -m pytest tests -q \
  --basetemp=/home/joao/.hermes/cache/scratch/prumo-task19-final-full
# 1471 passed / 7 live deselected / 3 warnings in 383.22s

.venv-ci/bin/python -m pytest tests/test_manual_runbook.py \
  tests/test_docker_contract.py::test_operator_runbook_links_authoritative_manual_refresh_and_has_valid_shell \
  -q --basetemp=/home/joao/.hermes/cache/scratch/prumo-q1-controller-focused
# 12 passed in 0.19s
```

The final suite includes 25 generator tests and 11 new exact-runbook tests. Later shared-state/review reporting changes are prose/evidence only. Final tested-file hashes are in evidence/task-19/controller-final-test-evidence.json. The earlier 1,460 result is retained with its actual pre-Q1-test scope, not relabelled as a later rerun. These are local controller results, not a new hosted CI claim.

Ruff passed for app/, ingest/, the authored tests and the three read-only World Bank evidence helpers. git diff --check passed. The real CLI catalogue output equals the generated file. Controller also reran the documentation checker: 60 relative links including anchors, 18 Bash fences, two embedded Python blocks, supported CLI/scheduler help and generated-output equality passed; network events were absent and DB/raw sentinel paths remained uncreated. Shell syntax alone was not treated as manual-write safety evidence.

## Review findings and closure of authored issues

Initial independent specification review requested F1/F2 corrections in the controller audit package, while confirming the generator and human documentation requirements:

- F1: dataset_run.finished_at is processing/pending-verification time, not final verification. The helper now returns last_processing_finished_at. The report separately cites actual verification.created_at as surfaced by status.last_verified and the subsequent scheduler outcome from their unchanged original receipts.
- F2: the report claimed fixed sample-count assertions more strongly than the initial helper enforced. The receipt-specific helper now pins 949 unique sample identities, 18 collector receipts/CSV envelopes, 930 active series, 45,915 rows and 15,465 null cells, with the original per-run seed/size checks. Removal of a historical sample with self-consistently reduced sample_size and count-preserving duplicate replacement are both rejected.

A fresh fix implementer made the bounded corrections, preserving every original capsule/status/log byte. Independent scoped re-review PASS_AUTHORED_SCOPE: task-19-spec-rereview.md. Controller replay and all eight negative helper probes passed; complete archive hashes and derived-result manifest agree. The original 3,541,615-byte World Bank capsule SHA-256 remains 4ac461bc853c36d82ab78763a923c9d7000a3ae7514397482e65975e0ecc04ba.

Independent quality review then found Q1 in the manual-import runbook: a normal Bash shell could continue after failed stop/destination/import prerequisites because strict mode belonged only to a separate bootstrap example. A fresh fix implementer placed the exact standalone fence in its own strict-mode subshell, added stopped-state readback and permanent safe-stub regressions. Failed stop/readback/preparation/refusal/copy prevents import; failed import remains nonzero before status. No automatic restart was added, and the parent shell remains open with its options/variables unchanged.

Controller focused tests and the final full suite passed. Separate Q1 specification PASS_AUTHORED_SCOPE and quality APPROVED_AUTHORED_SCOPE are in task-19-q1-spec-rereview.md and task-19-quality-rereview.md. The reviewers independently exercised exact argument boundaries and failure paths without real Docker/network/production operations. No Critical or Important finding remains open within the authored package. Initial request-changes reports remain preserved as review history.

## Production and source disposition

The 08:36 UTC snapshot and the later 2026-11-13T09:16:34.648570+00:00 snapshot both confirmed running worker, zero restarts/OOM, integrity ok, unchanged legacy fingerprints, zero licence violations, all 1,345 active series verified, zero stale active series under the retrieval policy and no pending runs. Public maintenance and health GETs returned HTTP 200. The later receipt is evidence/task-19/observation-20261113T091634Z.json. It explicitly retains elapsed_24h=false and task_18_closed=false.

World Bank Task 13's fresh live gate is now established in deployed per-indicator operation: 18 successful groups, all 930 active series, 45,915 current fetched observations and 949 exact independent CSV sample comparisons covering the latest observation of every series. Collector tokens and provenance were checked for every stored row; independent CSV agreement remains sampled. The 17 failed-fetch and 9 failed-verification run histories remain intact. Original dated-data continuity/manual support remains available for future outages, without claiming permanent endpoint availability.

FRED/OECD/REN are technically verified but legally withheld. DGEG retains 17 inactive definitions, no new adapter and unresolved verification/reuse blockers. ERSE has zero core definitions; dadosgov remains historical/unresolved and retained. All source assignments/exclusions and the licence/deferred/overlap registers are surfaced above, not silently accepted on the owner's behalf.

## Explicit remaining gates

The planned human-prefix update to CLAUDE.md was rejected by a protected-file approval timeout. No retry, alternate tool, index write or generated-hunk reversal was attempted. Entire CLAUDE.md remains at intake SHA-256 035dbcb8ba48cafabe128e757cca08f0dd8b6d4b44f950618d375867f7843c2a; AGENTS.md remains at 3ca4c4f363717d9dc5cf90adce6a4a6515a217ba1dab588bc04bf4f05d2f2513. Their pre-existing generated dirt stays unstaged/uncommitted. Updating only the human prefix still needs fresh owner authorization.

Task 18's actual observation starts 2026-11-13T01:21:18.732242+00:00 and cannot close before 2026-11-14T01:21:18.732242+00:00. Existing local/no-agent job41f08dd25c5c is scheduled for01:24:32 UTC to collect evidence, not accept it. Review real end-window source results and uninterrupted uptime before closing. No worker stop, manual import or deployment occurred in this continuation.

Final whole-branch review and owner acceptance of status, sources and unresolved source/right dispositions remain open. Backoffice, derived data and UI projects have not started. Publish this verified authored scope only on pipeline-rebuild; do not infer fresh main-merge or deployment permission from this report.
