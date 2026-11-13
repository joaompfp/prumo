# Task 19 independent quality review

Verdict: REQUEST_CHANGES

## Critical findings

None found in the bounded authored-package review.

## Important findings

### Q1. The production manual-import block continues after failed safety prerequisites

Locations: `docs/data/operations.md:299-300,302-328`, particularly the stop at line 321, destination refusal at line 323 and import/status sequence at lines 325-326. `docs/data/manual-refresh.md:104-109` designates this block as the exclusive production-write procedure.

The manual block does not establish failure handling or require a shell with `errexit` already enabled. The earlier `set -euo pipefail` at operations line 120 belongs to the separately authorized bootstrap section, which the current operator is explicitly told not to repeat. It is not a prerequisite of the standalone manual procedure.

In a normal Bash shell, failure of `bash -lic 'dc-web stop prumo-ingest'` does not prevent the subsequent copy and `run ... --bundle` against the shared production database. This can launch an independent writer while the worker is still running, contrary to the documented single-writer requirement. Likewise, a failed destination nonexistence test does not prevent copying into an existing bundle location. A failed import is followed by `status --json`, whose successful exit can hide the import's failure in the block's final status. This last case does not automatically restart the worker; the defect is continuation and loss of failure status, not an invented automatic restart.

Offline reproduction used the exact extracted Bash block from lines 303-327 in a clean `/bin/bash --noprofile --norc` subprocess with `errexit` disabled, as in an ordinary operator shell. All external commands were replaced by in-memory shell functions; no Docker, alias, source, filesystem write or network action occurred. Independently injected failures produced:

| Injected nonzero result | Actual subsequent execution | Block exit |
|---|---|---|
| Worker stop returns 1 | mkdir, destination check, copy, production import and status all execute | 0 |
| Destination nonexistence check returns 1 | copy, production import and status still execute | 0 |
| Bundle import returns 1 | status executes and replaces the final failure status | 0 |

Required correction: make this manual-write sequence self-contained and fail closed, independently of bootstrap shell history. Explicitly prevent copy/import after a failed stop, prevent copy/import after failed destination preparation or refusal, and retain a nonzero import result even if diagnostic status is subsequently collected. Keep the existing owner authorization, review-before-resume and renewed-observation requirements. Verify those negative paths with stubbed commands before accepting the corrected block. No implementation change or production interruption is needed to resolve this documentation defect.

## Minor findings

None requiring correction. No speculative output formats, generalized metadata frameworks or unrelated legacy changes are requested.

## Reviewed scope and passing checks

Reviewed the current authored package on `pipeline-rebuild`, HEAD `19536716ab27d340e8ef08d67b24bb83ccf5f93f`: the review contract, original specification review and F1/F2 re-review; actual `ingest/docgen.py`, nine-line `ingest/cli.py` diff, `tests/ingest/test_docgen.py`, generated sources, methodology, manual refresh, operations, README and DOCS_MAP. Also inspected the corrected World Bank exporter, offline auditor, focused mutation runner, checkpoint prose and Task 19 controller receipts. Settled source inclusion/disposition was not reopened.

### Renderer, separation of concerns and escaping

- `ingest/docgen.py:93-149` keeps rendering separate from registry reads and operational work. Its explicit source list preserves zero-series definitions, while sorted sources and sorted series provide stable output. The channel descriptions remain documentation-only; unknown channels do not acquire invented verifier claims.
- Independently decoded every generated table row and compared exact source/series/key/role/state/native-code tuples with the selected registry: all 9 sources and 1,791 rows match. Repeated rendering after independently shuffling source and series lists with eight seeds remained identical to the committed catalogue. This was an actual in-memory comparison, not reliance on author tests or a section-count-only check.
- Exercised `_cell` with raw HTML/event attributes, entity-shaped HTML, JavaScript Markdown links, data-URL images, CRLF/CR heading/table injection, Markdown metacharacters, angle-bracket autolinks and HTML comments. HTML delimiters and Markdown metacharacters were encoded; a single entity decode recovered the original visible text with the documented newline-to-`<br>` normalization. Entity-shaped input remained entity-shaped text rather than becoming a raw HTML tag. These were direct encoding/round-trip assertions, not a claim of testing every Markdown renderer.
- Inspected the authored tests' network guard, exact identity/state assertions, blocked/empty/inactive/cross-check fixtures, ordering/purity checks, validation failures and subprocess implementation-import boundary. No additional renderer defect was established by the independent probes.

### CLI and operational boundary

- The new branch at `ingest/cli.py:337-345` returns before path resolution, DB/raw setup, registry synchronization or verifier registration. The actual CLI was exercised against an in-memory virtual custom registry containing an untrusted metadata source and an empty source.
- That probe denied `_resolve_paths`, operational `load_registry`, `open_db`, `RawStore`, `sync_registry`, `run_all`, `_http_for`, verifier setup and SQLite connection creation; it supplied a forbidden HTTP seam and installed a network-denying audit hook. The command returned 0 with stdout only and retained both custom source definitions. No destination DB/raw path was created.
- The CLI module retains pre-existing operational imports; the additive branch does not claim to make the entire CLI import graph implementation-free. The pure renderer's documentation channel map does not import adapters/verifiers to discover channels.
- The manual's per-group stale-bundle protection, original receipt handling, inclusive E-REDES bounds and native UTC preservation are explicit. Q1 concerns the shell's orchestration of those existing controls, not a request for a new ingestion lock or changed pipeline semantics.

### Corrected audit helpers and evidence limits

- Replayed the actual original gzip capsule through the corrected offline auditor with network forbidden. Its result equals the stored derived JSON: 18 live groups, 930 active series, 45,915 exact collector-token/provenance observations, 15,465 null cells, 949 exact independent CSV samples, latest-series sample coverage 930 and 18 CSV envelopes. Historical unique failed-run counts remain 17 failed-fetch and 9 failed-verification.
- Executed the actual focused probe runner: all supplied mutation expectations passed, including historical sample removal with adjusted declared size, count-preserving duplicate replacement, altered stored token/CSV result, missing latest sample/collector receipt and inconsistent sample-size/seed changes. Independently constructed a count-preserving historical duplicate replacement; the auditor rejected it with `duplicate sample identity: (36, 'worldbank.rnd_pct_gdp.AO', '2016')`.
- F1's corrected output is `last_processing_finished_at=2026-11-13T06:52:25.119769+00:00`; `final_verified_at` is absent. The checkpoint prose separately attributes actual verification and scheduler completion. F2's fixed receipt counts and unique sample-identity assertions are present. No further concrete helper defect was found within this receipt-specific review.
- The catalogue, methodology and checkpoint report distinguish registry rights from technical verification, original retrieval from processing/verification, full-row collector fidelity from sampled independent CSV agreement, and current snapshots from a completed observation. Their rights, date and sample limitations remain substantive and explicit.

### Existing controller results and local checks

- Recomputed the hashes of all files listed in `evidence/task-19/controller-test-evidence.json`; all six match the recorded tested bytes, including application code, registry, authored tests and dependency/test configuration. The controller's 1,460 passed / 7 live deselected / 3 warnings is attributed evidence, not a suite newly run by this reviewer. No whole-suite rerun occurred.
- Read `evidence/task-19/observation-20261113T091634Z.json`: the supplied receipt is explicitly nonfinal, with `elapsed_24h=false`, `task_18_closed=false`, zero restarts/OOM and zero licence violations. This is a local controller receipt, not fresh production access by this reviewer.
- Focused Ruff with `--no-cache` passed on docgen, CLI, authored docgen tests and the corrected offline auditor/probe runner.
- Before/after SHA-256 snapshots of the protected instruction files and every existing evidence file were identical across the successful independent renderer/CLI/audit probe process. Bytecode writes were disabled. Probe input and command stubs stayed in memory; no original evidence was mutated.

## Boundary and remaining gates

Only this report was authored. No implementation, generated catalogue, protected file, shared state, evidence, permissions or production service was edited. No network requests, delegation, whole-suite execution, commit, push or deployment occurred.

The specification gate remains the supplied `PASS_AUTHORED_SCOPE` after F1/F2 corrections. This independent quality gate requests the bounded Q1 runbook correction before authored-scope quality approval.

Protected `CLAUDE.md` approval remains open. The real Task 18 observation cannot close before `2026-11-14T01:21:18.732242+00:00` and still requires actual continuity/end evidence and controller review. Final whole-branch review, controller reconciliation, unresolved owner/source-rights decisions and owner acceptance remain open regardless of any later scoped quality approval. Production remains unchanged by this review.
