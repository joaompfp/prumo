# Task 19 Q1 independent quality re-review

Verdict: APPROVED_AUTHORED_SCOPE

## Scope and findings

No remaining Critical or Important finding was established in the bounded Q1 correction.

Read Q1 in `task-19-quality-review.md`, the correction report `task-19-quality-fix-1.md`, and `task-19-q1-spec-rereview.md` with its `PASS_AUTHORED_SCOPE` verdict. Independently inspected the actual standalone manual fence and adjacent authorization/resumption prose at `docs/data/operations.md:286-352`, and all of `tests/test_manual_runbook.py`. Review used the current dirty worktree on `pipeline-rebuild`; it did not assume the correction was committed.

The earlier full-package acceptance of other areas remains undisturbed. Generator, audit-helper, catalogue and unrelated settled behavior were not re-audited. This approval covers only Q1's authored runbook correction and its offline tests.

## Actual fence and failure handling

- `operations.md:307-308,336` encloses the sequence in a subshell with its own `set -euo pipefail`. It does not depend on bootstrap history or alter the parent shell's options or assigned variables.
- The stop at line 327 is a standalone prerequisite. Its failure prevents inspection, copying and import. The inspection assignment at line 328 separately propagates a failed command substitution; successful inspection must then pass the exact `false` comparison at line 329. Failed inspection or unacceptable output prevents destination preparation and import.
- Directory creation, destination nonexistence refusal and copy are separate commands at lines 330-332. Each failure stops the sequence. In particular, destination refusal prevents copy, and failed copy prevents the independent writer.
- Import at line 333 must succeed before status at line 334 can execute. Failed import remains nonzero and is not replaced by a successful diagnostic status. Status failure after successful import also remains nonzero.
- Source, bundle and global ingestion options remain quoted and ordered. The existing original E-REDES inclusive bounds and optional World Bank indicator remain intact.
- No start/restart was added to the manual-import fence. Lines 339-345 retain a separate, explicitly approved resume procedure after result review and the silent SOPS prerequisite. Lines 292-304 retain owner authorization, no concurrent CLI writer, and separate diagnostics after failure.

These checks apply to the documented standalone fence in a normal clean Bash parent with errexit initially disabled. They do not establish a new concurrency lock or promise safety after embedding the fence in an errexit-suppressing conditional wrapper. The existing single-writer requirement remains necessary.

## Executed offline evidence

Ran only the authored safe-stub test file, with bytecode, plugin autoload and pytest cache disabled, using the existing project interpreter:

    PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv-ci/bin/python -m pytest tests/test_manual_runbook.py -q -p no:cacheprovider --basetemp=<isolated TMPDIR scratch>/pytest

Actual result: 11 passed in 0.18s, exit 0; Python 3.12.3 and pytest 9.2.0. This includes the exact-fence Bash syntax check. No whole-suite or unrelated contract test was run.

Inspected the harness before running it. It extracts the actual fence, replaces `basename`, `test`, `bash` and `docker` with shell functions, removes executable directories from PATH, and uses a DEBUG command allowlist. Its failure tests prevent import after stop/readback/destination/copy failures; its import-failure assertion requires exit 23 with no status. Success paths retain World Bank/E-REDES arguments and reject unexpected Docker operations. It also checks parent survival, initially disabled parent errexit and an empty isolated working directory. Some command recognition uses flattened `$*`; the independent probes below instead recorded argument boundaries.

Executed an additional in-memory Python/Bash harness without importing the authored test harness. It independently extracted and executed the exact fence in `/bin/bash --noprofile --norc`, outside any conditional wrapper. Every external command in the inspected fence was replaced by an in-memory function; PATH contained no executable directory. Calls were captured with each argument separately delimited. No actual alias, Docker, filesystem-copy, source or network command from the fence ran.

All 16 independent cases passed:

| Injected case | Observed result |
|---|---|
| Successful World Bank and E-REDES | Exit 0; copy and import retain the space-bearing bundle path as one argument; correct global options, source and indicator/day bounds |
| Manifest failure | Exit 40; no copy, import or status |
| Stop failure | Exit 41; no copy, import or status |
| Inspection emits `false` but exits nonzero | Exit 42; no copy, import or status |
| Directory creation failure | Exit 43; no copy, import or status |
| Existing-destination refusal | Exit 43; no copy, import or status |
| Copy failure | Exit 43; no import or status |
| Import failure with otherwise successful status stub | Exit 43; import attempted, status absent |
| Status failure after successful import | Exit 43; failure remains visible |
| Empty, `true`, `False`, `false extra`, or repeated `false` readback | Exit 1 in each case; no copy, import or status |
| Unsupported source | Exit 2; no import or status |

Every independent case asserted parent survival and exact preservation of parent shell flags and `SHELLOPTS`. Parent sentinel values for `BUNDLE_NAME`, `BUNDLE_TARGET`, `WORKER_RUNNING` and the `RUN_ARGS` array were unchanged. No restart appeared in captured traces; unexpected Docker or stop-command forms were rejected. The independent probe working directory remained empty.

Before/after SHA-256 comparison was unchanged for `AGENTS.md`, `CLAUDE.md`, the operations document, the authored test file, and the Q1 quality-review, correction and specification re-review reports. This is a bounded input-integrity check, not a claim of hashing every concurrent controller artifact.

## Boundaries and remaining gates

Only this report was authored in the repository. Temporary pytest/probe directories were confined to the configured scratch directory and removed after execution. No implementation, tests, runbook, shared/protected file or original evidence was edited. No external operation, network access, production access, delegation, whole-suite run, commit, push or deployment occurred. Historical author RED results and controller suite results were not relabelled as independent execution.

`PASS_AUTHORED_SCOPE` remains the supplied specification verdict. `APPROVED_AUTHORED_SCOPE` closes only this Q1 independent quality re-review.

Protected `CLAUDE.md` approval remains open/blocked. The actual Task 18 observation cannot close before `2026-11-14T01:21:18.732242+00:00` and still requires real continuity/end evidence and controller review; interrupted uptime cannot close the original window. Final whole-branch review, controller reconciliation, unresolved owner/source-rights decisions and final owner acceptance remain open. No approval here authorizes a manual production write, restart or deployment.
