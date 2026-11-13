# Task 19 independent specification review

Verdict: REQUEST_CHANGES

The runtime documentation and registry catalogue meet the approved authored requirements in the checks below. The accompanying audit package still contains incorrect verification-time semantics and an overstated assertion-scope claim. These are authored-package discrepancies, separate from the known protected-file and observation gates. No implementation correction was made by this reviewer.

## Review boundary

Reviewed the current working-tree diff and untracked deliverables on `pipeline-rebuild`, HEAD/base `19536716ab27d340e8ef08d67b24bb83ccf5f93f`. Authority: `task-19-review-brief.md`, the complete `task-19-brief.md`, original Task 19 in `docs/superpowers/plans/2026-11-10-base-data-pipeline.md:206-212`, design requirements and applicable ledger rulings. Implementer reports were checked against actual files rather than accepted as independent proof.

Inspected README, DOCS_MAP, methodology, manual refresh, operations, generated sources, docgen, its tests, the CLI diff, controller checkpoint report, exporter, offline auditor, negative-probe receipt and manifested checkpoint artifacts. Relevant existing model/registry, pipeline, verification, serving and source-channel contracts were read for comparison. The runtime diff is confined to the additive nine-line CLI documentation branch plus the new renderer; no registry, dependency, SQL/model, parser, verifier or scheduler behavior change appears in that diff.

Only this review report was intentionally authored. No implementation, protected instructions, controller state documents, production services or source permissions were edited. No network requests, whole-suite rerun, commits, staging, delegation or acceptance transition were performed. Probe capsules and custom-registry input were supplied in memory, not written over evidence or implementation files.

## Findings requiring correction

### F1. The audit package labels a pre-verification timestamp as final verification/completion

Locations:

- `docs/superpowers/handoff/reports/evidence/task-18/worldbank-offline-audit.py:169-172`
- `docs/superpowers/handoff/reports/evidence/task-18/worldbank-live-export.py:33-35`
- `docs/superpowers/handoff/reports/task-18-observation-checkpoint.md:29`
- `docs/superpowers/handoff/reports/evidence/task-18/checkpoint-20261113T083638Z/worldbank-offline-audit-result.json:7`

The auditor returns `final_verified_at` from `max(dataset_run.finished_at)`. That field is set when parsing/writing finishes and the run enters `pending-verification`, before independent verification: `ingest/pipeline.py:175-188`. The actual verification timestamp is generated later and stored as `verification.created_at`: `ingest/verify.py:141-155` and `ingest/db.py:148-152`. The new exporter selects the verification's seed, sample size and pass state, but not that timestamp.

Concrete offline reproduction: the supplied gzip capsule replays successfully and returns `final_verified_at=2026-11-13T06:52:25.119769+00:00`, exactly the capsule's maximum dataset-run `finished_at`. Already archived status instead records `last_verified=2026-11-13T06:52:26.025416+00:00` for World Bank at `checkpoint-20261113T083638Z/status-20261113T083638Z.json:12453`. The successful final `SP.DYN.CDRT.IN` scheduler outcome is logged at `2026-11-13T06:52:26.027280+00:00` in the same folder's `worker-20261113T083638Z.log:66`.

The checkpoint report calls the earlier timestamp "Final group completion". This conflates dataset processing with subsequent verification and contradicts Task 19's requirement to retain distinct, truthful dates. It does not invalidate the later successful verification or the exact value comparisons, but it requires correction before the audit pack is accepted. Use an accurately named processing timestamp, or the real verification/status timestamp with its provenance; distinguish scheduler completion if reporting that too. Existing publisher bytes do not need alteration or a new production request.

### F2. The report overstates the auditor's fixed-scope count assertions

Locations:

- `docs/superpowers/handoff/reports/task-18-observation-checkpoint.md:51`
- `docs/superpowers/handoff/reports/evidence/task-18/worldbank-offline-audit.py:109-159,161-174`

The report says that the auditor "asserts all complete-scope counts" specific to this acceptance receipt. The code asserts 930 active series, 18 runs and 45,915 stored observations, and checks latest-series coverage. It does not assert the claimed 949-item comparison count. It reports the number of supplied items and checks each run's item count against the capsule's own `sample_size` fields.

Independent negative probe, entirely in memory: remove the historical sample for `worldbank.rnd_pct_gdp.MX`, period `2023`, and decrement the remaining items' declared `sample_size` for that run. The same auditor accepts this capsule and reports 948 independent CSV samples with all 930 latest-series samples still covered. This demonstrates that internal consistency is not the fixed 949-item scope assertion described in the report.

The original manifested capsule remains intact, has 949 distinct comparison keys, and passed its full replay. Its counts are not disputed, and this finding does not claim that the current archive lost evidence. Correct the assertion-scope prose to match what is actually enforced, or explicitly enforce the receipt-specific counts if retaining that claim. Do not present the successful altered-token/result/latest-sample probes as proof that every possible sample omission is rejected.

## Requirement checks that passed

| Requirement | Actual implementation/evidence reviewed |
|---|---|
| Raw, validated and served stages | `docs/data/methodology.md:29-77,141-167`; raw provenance, text versus REAL, quarantine, licence boundary and legacy distinction agree with the inspected implementations. |
| Vintages, flags and precision | `docs/data/methodology.md:61-97,151-167`; exact numeric comparison, INE `valor`/display caveat, lossy flag mappings, insertion-order precedence and withheld-source revision-event limitation are explicit. |
| Sampling, independent channel, mandatory sampled matches and refetch | `docs/data/methodology.md:99-139`; latest-per-populated-series sampling, historical fill limits, exact Decimal/no tolerance, default three attempts and the verified-byte shortcut match `ingest/verify.py` and `ingest/pipeline.py`. No all-row CSV claim is made. |
| Gap-month caveat and actual/original dates | `docs/data/methodology.md:169-202`; no invented April ingestion, current-vintage catch-up, recorded receipt preservation, future-skew policy and per-group stale protection are documented. F1 identifies the separate audit-package date discrepancy. |
| Registry-generated catalogue and required named test | `ingest/docgen.py:93-162`, `ingest/cli.py:91-93,337-345`, `tests/ingest/test_docgen.py:58-95`; real CLI stdout exactly equals `docs/data/sources.md`. The required test exists and passed in this review. |
| All source definitions and exact identifiers | Independent YAML-to-Markdown comparison covered every source and every exact source/ID/key/role/state/native-code tuple. All 9 current source definitions and 1,791 series are retained: 1,340 active primary, 427 inactive primary, 5 active cross-check and 19 inactive cross-check. ERSE is not invented as a source definition. |
| Licence, attribution, primary indicators and independent channel | `ingest/docgen.py:17-83,116-147`; metadata matches the selected registry. Reviewed channel descriptions were compared with the verifier contracts. DGEG is blocked/undocumented, and unknown custom sources stay undocumented. |
| Pure deterministic generation, custom registry and no operational setup | `ingest/docgen.py:87-162`, `ingest/cli.py:337-345`; default output equality, a custom virtual registry, zero-series source, inactive primary/cross-check entries, escaping and early return were exercised. A separate process denied implementation imports, SQLite opening and socket events while rendering successfully. No new dependency or generic output mechanism was introduced. |
| Current entrypoints and deployed operations | `README.md:3-27,46-99,113-116`, `DOCS_MAP.md:3-38`, `docs/data/operations.md:3-110`; maintenance-only HTTP, real f0nix deployment, shared paths, CLI `PRUMO_DB` versus worker `PRUMO_DB_PATH`, explicit global CLI options, licensing and open observation are documented. |
| Safe manual refresh | `docs/data/manual-refresh.md:3-22,39-155`, `docs/data/operations.md:286-343`; original-response bundles, per-group stale refusal, single linked stop/import/review/resume procedure and renewed observation after interruption are explicit. E-REDES `--to` is inclusive and native timestamps stay UTC. No April E-REDES legacy rows are inferred. |
| Actual production checkpoint and source exceptions | Archived status reconciles to all 1,791 current registry IDs. All 1,345 active entries have real `last_verified`, availability `verified`, and `stale=false` at that checkpoint. FRED/OECD/REN technical verification remains separate from legal withholding; DGEG has 17 inactive definitions/no new adapter, ERSE zero core entries and dadosgov retained/unresolved. |
| Evidence scope and historical preservation | Manifest hashes/sizes, positive World Bank replay and the supplied negative-probe classes were independently exercised. Original legacy fingerprints, the 17 failed fetches and 9 failed-verification subruns remain in the archived record. Full-row JSON token/provenance checks are distinguished from sampled CSV agreement. F1/F2 are the remaining audit-description discrepancies found here. |
| Approved uncommitted handoff | The brief amends the original commit step: implementation stays uncommitted for controller gates. This reviewer did not commit or treat absence of a commit as a specification failure. Historical files/data were not removed by the reviewed diff. |

## Concrete offline verification performed

- Ran the actual CLI entrypoint with socket events forbidden and captured stdout in memory: exit 0, empty stderr, byte-for-byte catalogue equality. SHA-256: `5612508b8297ff09ab78194f84a1e79d5308b6463aa2b5e582c0b15e0b555849`.
- Independently parsed current YAML and decoded rendered table cells; compared the complete tuple multisets and source licence/URL/attribution fields. Repeated generation is current. Custom `--registry` passed through the real loader/CLI using an in-memory virtual path while path resolution and DB opening were forbidden.
- Independently rendered with an import finder rejecting `ingest.sources*` and `ingest.verifiers*`, SQLite connections forbidden and a socket audit hook installed: passed. A separate CLI-import probe recorded and denied one `socket.__new__` event during imports; no connection was permitted. This is not a claim that CLI module import never attempts socket construction.
- Executed only focused authored tests, not the whole suite: `env -u PYTHONPATH -u PYTHONHOME PYTHONDONTWRITEBYTECODE=1 .venv-ci/bin/python -B -m pytest -p no:cacheprovider -q tests/ingest/test_docgen.py::test_sources_md_lists_every_source_with_licence tests/ingest/test_docgen.py::test_sources_md_contains_every_exact_series_identity_and_state tests/ingest/test_docgen.py::test_generated_sources_is_current_and_repeatable` -> 3 passed in 19.58 seconds.
- Checked 60 relative documentation links, including heading targets; 18 Bash blocks with `bash -n`; embedded Python blocks with `ast.parse` (2). Checked prose for em-dashes/replacement characters and terminal newlines. All passed. Literal registry/publisher typography in generated sources was not rewritten.
- Ran `.venv-ci/bin/ruff check ingest/docgen.py ingest/cli.py tests/ingest/test_docgen.py` and `git diff --check 19536716ab27d340e8ef08d67b24bb83ccf5f93f`: both passed.
- Rehashed every artifact listed in the checkpoint `MANIFEST.json`: all 6 byte counts and SHA-256 values match. This validates the local copies against the manifest; it is not fresh production access or independent rehashing of the full remote raw store.
- Replayed `worldbank-offline-audit.py` against the actual gzip capsule with network forbidden. Output exactly matches the supplied result: 18 successful live groups, 930 active series, 45,915 exact JSON-token/provenance rows, 15,465 null cells, 949 exact CSV sample comparisons, latest-series coverage 930 and 18 CSV envelopes. Verified distinct sample keys independently. No all-row CSV equality is inferred.
- In-memory altered stored token, altered recorded CSV result and removed latest-series sample were each rejected. The additional historical-sample/count mutation was accepted as detailed in F2. Original evidence files were not changed.
- Archived summary readback confirms the intermediate worker state: running, zero restarts/OOM, `elapsed_24h=false`, `task_18_closed=false`. Archived audit records zero licence violations, unchanged legacy fingerprint, 337 checked raw files and 217 checked evidence objects. Those whole-store checks are attributed controller receipts, not a new direct DB audit by this reviewer.
- Current protected-file hashes equal the recorded intake hashes: AGENTS `3ca4c4f363717d9dc5cf90adce6a4a6515a217ba1dab588bc04bf4f05d2f2513`; CLAUDE `035dbcb8ba48cafabe128e757cca08f0dd8b6d4b44f950618d375867f7843c2a`. Their base-relative generated dirt was not attributed to Task 19 authorship or reverted.

## Still-open gates, separate from authored-scope findings

- CLAUDE approval: BLOCKED. The required human-prefix update remains unapplied after protected-file approval timed out. `CLAUDE.md:9-37` still lacks the intended current scheduler/shared-path/environment/open-observation/navigation update. The amended review contract explicitly reserves this permission gate. No retry, alternate write or silent waiver occurred.
- Task 18 observation: OPEN. Start `2026-11-13T01:21:18.732242+00:00`; no closure before `2026-11-14T01:21:18.732242+00:00`, followed by controller review of actual uninterrupted operation, end evidence and source exceptions. The intermediate checkpoint and scheduled local evidence job do not close it. This offline review did not inspect a later end-window receipt.
- Controller full-suite/quality gates: not granted here. The supplied baseline is 1,435 passed / 7 live deselected / 3 warnings; a replacement full suite was described as running. That is not a verified final result in this report. No duplicate full suite was run. Separate quality review must wait for specification acceptance of the corrected package.
- Controller state reconciliation: still controller-owned. `HANDOFF.md:3` acknowledges the new checkpoint and Task 19 in progress, while `HANDOFF.md:40,65` retain older "not started" statements. The brief assigns state-document updates to the controller. This discrepancy is recorded, not repaired or treated as implementer permission to edit shared state.
- Owner acceptance: OPEN. Provisional registry assignments, unresolved licence/source dispositions, the status report and generated sources must still be surfaced to the owner. Existing deployment approval is not final Project 1 acceptance. Whole-branch review and any later merge/deployment remain separate gates.

Full Task 19 completion remains `BLOCKED_CLAUDE_APPROVAL_AND_TASK18_WINDOW`, with owner acceptance and the other controller gates above still required. F1/F2 additionally prevent `PASS_AUTHORED_SCOPE` for this reviewed package.
