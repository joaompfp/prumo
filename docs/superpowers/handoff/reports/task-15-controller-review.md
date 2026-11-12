# Task 15 OECD - controller acceptance

Date: 2026-11-12. Worktree /home/joao/projects/prumo-pipeline, branch pipeline-rebuild. Code accepted at decc048, after 05fdd3b/8847d84/212cd17 (source/registry), ccaa0ed/5d27624 (verifier), 7b31909/e34c60f (source/verifier hardening), and 4b95bb1/4d178da/decc048 (quality fixes and report). No main merge, scheduler or deployment.

## Disposition

TECHNICALLY COMPLETE / LEGALLY WITHHELD. All six active OECD series passed a fresh registered full-history run_with_refetch over real f0nix egress, independent CSV comparison, whole-archive fidelity and offline evidence replay. No code-blocking Critical or Important review finding remains. `redistribution_ok=false` still excludes every OECD row from serving; the per-dataflow third-party rights check is unresolved. This acceptance does not grant publication rights.

## Reconciled starting boundary

The user-facing last checkpoint described OECD as unstarted. The worktree had already advanced ten commits beyond published 2fb6e28 to decc048, including completed source/verifier implementations and reviewed fixes. The uncommitted handoff described only Part A, and the ledger stopped at Task 14. The controller preserved these inherited changes, resumed the earliest unfinished quality re-review, and did not repeat implementation or infer deployment from branch progress.

## Independent review gates

| Gate | Range / scope | Verdict |
|---|---|---|
| Source specification | 2fb6e28..212cd17 | Scoped PASS with F1 Important, F2/F3 Minor to resolve |
| Verifier specification | 212cd17..5d27624 | REQUEST_CHANGES for executable network bounds |
| Whole code specification | 2fb6e28..e34c60f | PASS, source F1/F2/F3, dimension identities and network bounds re-probed |
| Whole code quality | 2fb6e28..e34c60f | REQUEST_CHANGES: unsorted endpoint assertion, empty quarantine assertion, incomplete archive-fidelity claim |
| Quality fix specification | e34c60f..decc048 | PASS |
| Quality fix independent quality | e34c60f..decc048 | APPROVED; 107 tests and 17 adversarial probes reproduced |

Reports: task-15-source-spec-review.md, task-15-verifier-spec-review.md, task-15-final-spec-review.md, task-15-quality-review.md, task-15-quality-fix-spec-review.md and task-15-quality-fix-quality-review.md in this directory. Review agents were separate from implementers; runtime reported kimi-k3. No inferred model routing or fabricated coauthor/session trailer.

## Controller fresh execution

`.venv-ci/bin/python -m pytest tests -q` at decc048:

1133 passed, 7 live deselected, 1 warning in 244.75 s. No production code changed after this run.

`.venv-ci/bin/ruff check` over all eight OECD-authored Python paths: All checks passed. Whitespace checks apply to authored code/reports only: the original discovery bodies retain publisher CRLF and the derived web text retains its original whitespace; a whole-tree whitespace check flags these intentionally preserved bytes. GitNexus refreshed on the exact prumo-pipeline worktree; compare against 2fb6e28 reported MEDIUM, five expected adapter/test flows. Extractor warnings mean the graph is incomplete; the full suite and actual diff remain the acceptance evidence. No stable engine, SQL, HTTP or registry model contract changed.

The controller reran the quality review's 17 adversarial probes in a fresh scratch directory: all passed, including row loss, unsampled value/flag drift, incorrect response linkage, duplicate provenance and invalid archived HTTP status. The first rerun reused the review's previously mutated scratch DB; its failure was resolved by a unique scratch directory, with no source change. This was a probe-isolation defect, not a publisher or adapter failure.

### Committed live pytest

`.venv-ci/bin/python -m pytest tests/ingest/test_verifier_oecd.py -m live -s --basetemp=/home/joao/.hermes/cache/scratch/prumo-oecd-task15-pytest-live-20261112-1640`

1 passed, 50 deselected in 46.95 s. Phase: verified, 12 physical HTTP attempts, 44.8 s, 12/12 sampled matches, zero served. Five business-series responses held 14 months each (2025-09..2026-10); unemployment held 13 (2025-09..2026-09). Expectations came from this run's fresh archive, including every stored value/flag/provenance tuple; no frozen fixture dates or counts. Client retries=0, dataset max_attempts=1, at most 18 attempts and a 150 s enforced deadline. Every sampled CSV envelope replayed offline.

### Full-history production-egress acceptance

Fresh real GETs through f0nix, 2026-11-12T16:38:45.875530Z..16:39:37.297137Z. Application code and isolated SQLite ran locally; the HTTP bridge ran in memory over SSH, with no remote files, credentials, service changes or production DB access.

| Series | Observations | First | Last |
|---|---|---|---|
| oecd.cli.PT | 478 | 1987-01 | 2026-10 |
| oecd.employment.PT | 478 | 1987-01 | 2026-10 |
| oecd.order_books.PT | 478 | 1987-01 | 2026-10 |
| oecd.production.PT | 478 | 1987-01 | 2026-10 |
| oecd.selling_prices.PT | 478 | 1987-01 | 2026-10 |
| oecd.unemp_m.PT | 525 | 1983-01 | 2026-09 |

Result: verified, 2915 written, zero quarantined, all six active series covered, 120/120 exact sampled matches, zero served. Twelve original HTTP 200 responses: six complete JSON histories and six independent labelled CSV responses spanning each sampled series' min/max. Network phase 51.307 s, minimum request spacing 4.5 s, no client retries, dataset max_attempts=1, 18-request budget and 180 s hard wall deadline, each remote request bounded to at most 12 s. Redirects were not followed by the remote bridge, so every dispatched get was one physical request.

Full DB/archive comparison covered all 2915 original value tokens, flags and raw-response positions. The independent channel covered the 120 sampled observations; this does not claim independently verifying every unsampled CSV observation. Every compared unit and flag was recovered from the publisher CSV body. No conversion, rounding or tolerance was used; exact Decimal equality admits only publisher formatting differences such as JSON -6.0 vs CSV -6.

## Durable evidence

`docs/superpowers/handoff/evidence/task-15-oecd/live/live-acceptance-capsule.tar.gz`: controller-created audit capsule, NOT a publisher ZIP; 305756 bytes, SHA256 `2f40615a8705c6d4a75612663da975040f23760497c1f82d3d21a8410b144409`, 33 safe regular members. The capsule contains exact original bodies, raw-store envelopes, isolated DB, source-spec snapshot, request manifest, controller acceptance script and offline audit script. The checkpointed DB includes a zero-byte WAL and its SHM audit artifact.

The archive was extracted into disjoint scratch, every one of its 32 manifested files rehashed, then its offline audit executed with socket audit events forbidden after dependency imports: passed, six collector responses, 2915 observations, 120 comparisons, six CSV bundles, zero served, no network. SQLite integrity_check was ok and foreign_key_check empty. All sampled envelope bodies matched their original wire-body hashes, final URLs and actual HTTP 200 statuses. Live/summary.json, wire.json, capsule-manifest.json, archive-record.json and offline-replay-result.json retain machine-readable results. Scratch paths inside manifests document the execution and are not durable dependencies; replay resolves raw evidence by stored hash.

Discovery's 20 records were independently rehashed, including 17 original HTTP captures and three derived web-text documents. Discovery budget prose is reconciled to that manifest: no audited total of 21 requests or <=360 s full-phase claim is made. The f0nix CMS challenge was reported but not archived; the original f0nix data probe was archived. Publisher bytes and their original manifests were not edited. This documentation correction closes quality M1 without inventing provenance.

## Remaining limitations and next gate

Only OBS_STATUS=A (Normal value) is admitted in the reviewed flows. Unknown status/dimension/multiplier/shape still fails closed, never guessed or bypassed by inactivation. The full histories also parsed successfully under this rule. The legacy id oecd.cli.PT remains the BCICP business-confidence series, not headline LI. OECD unemployment remains a cross_check with INE primary.

Non-blocking review notes: CSV quoting is framing rather than a numeric difference; dataflow version digits are pattern-checked while agency/dataflow and dimensions are pinned; helper defensive defaults/duplicate guards are redundant under the current parser/schema. Existing withheld-source revision-event limitation is unchanged. Per-dataflow third-party rights remain unconfirmed; technical acceptance does not waive them.

Task 16 is conditionally not applicable: no E-REDES/dadosgov source or series exists in the authoritative registry, including inactive entries. See task-16-scope-disposition.md. Next unstarted implementation is Task 17; it must register OecdVerifier in addition to the six earlier verifier classes and preserve explicit World Bank locale orchestration, DGEG blocked reporting and all licence gates. Task 13 fresh-live verification remains OPEN by owner-authorized order, without new probe loops. No main merge or deployment.
