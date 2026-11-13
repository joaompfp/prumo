# Task 19 quality fix round 1: bounded Q1 correction

## Result

Implemented Q1 only. The standalone manual-import fence in `docs/data/operations.md` now runs inside a subshell with its own `set -euo pipefail`. Failed stop, stopped-state inspection, directory preparation, destination refusal or copy prevents the independent import. A successful stop must be followed by a successful `docker inspect` whose running-state output is exactly `false`. The inspection assignment is separate from the comparison so an inspection command failure also stops execution.

A failed import exits nonzero immediately, before diagnostic status can mask it. Adjacent prose directs the operator to collect diagnostics separately and review before restart. The subshell keeps the operator's parent shell open and does not change its shell options. No restart was added. Existing owner authorization, observation consent, single-writer restriction, review-before-resume and renewed observation requirements remain intact. `manual-refresh.md` already links this authoritative procedure and was not changed.

## Permanent offline tests and actual RED/GREEN

Added `tests/test_manual_runbook.py`. Tests extract the actual first Bash fence under the manual-update section and execute it verbatim using `/bin/bash --noprofile --norc`, with errexit initially disabled. All external commands in the fence (`basename`, `test`, `bash`, `docker`) are in-memory shell functions. PATH contains no executable directory; a DEBUG command allowlist rejects unexpected commands, including absolute external commands. No real command from the fence accesses Docker, services, files, sources or a network. The harness uses pytest `tmp_path` as its isolated working directory and asserts that the fence creates no files there.

Coverage includes failed worker stop, failed inspect, worker still running, failed directory creation, existing destination refusal, failed copy, failed import with an otherwise successful status stub, successful World Bank and E-REDES ordering and preserved arguments, invalid source without exiting the parent, and exact-fence Bash syntax. The failed-import test requires exit 23 and no subsequent status; the success paths exercise the status stub's zero exit. Unexpected commands, including any restart, fail the harness.

Before editing operations.md, harness preparation exposed and corrected a DEBUG allowlist omission for Bash `case` and an argument-indexing mistake. Those preliminary harness failures are not claimed as defect evidence. The subsequent valid RED run against the unchanged fence used:

    PYTHONDONTWRITEBYTECODE=1 .venv-ci/bin/python -m pytest tests/test_manual_runbook.py -q -p no:cacheprovider --basetemp="$TMPDIR/task19-q1-red-final"

Actual result: 10 failed, 1 passed. Failed stop, directory preparation, refusal, copy and import all continued through import/status and returned zero. Readback cases demonstrated the missing stopped-state check. Invalid source exited the parent. The syntax check passed.

After the bounded documentation correction, the focused new tests plus the existing runbook contract passed. A final rerun after the test import-spacing lint correction used:

    PYTHONDONTWRITEBYTECODE=1 .venv-ci/bin/python -m pytest tests/test_manual_runbook.py tests/test_docker_contract.py::test_operator_runbook_links_authoritative_manual_refresh_and_has_valid_shell -q -p no:cacheprovider --basetemp="$TMPDIR/task19-q1-green-final"

Actual result: 12 passed in 0.20s. The existing contract checks Bash syntax for every operations fence; the new test separately checks the exact manual fence. Focused `ruff check --no-cache tests/test_manual_runbook.py` passed. `git diff --check -- docs/data/operations.md` passed.

The default Python lacked pytest; an existing project `.venv-ci` interpreter was used without installing dependencies or accessing the network.

## Scope and preservation

Authored files are limited to the manual block and necessary adjacent prose in `docs/data/operations.md`, new `tests/test_manual_runbook.py`, and this report. No existing application function, class or method was edited; no pipeline locking/import/dependency change was made.

A SHA-256 baseline of existing tracked and untracked regular files was taken before edits. Immediately before writing this report, comparison found only `docs/data/operations.md` changed and only `tests/test_manual_runbook.py` newly added as a regular file. All other baseline file hashes were unchanged, including protected AGENTS/CLAUDE, application/registry/requirements, generated catalogue, audit capsule/helpers, shared handoff/plan state and existing reports/evidence. An initial new-path assertion included unchanged Git directory entries excluded from the regular-file baseline; repeating with consistent regular-file filtering passed. No unrelated files were corrected or reverted.

No production access, network operation, source/service write, delegation, full-suite run, commit, push, merge or deployment occurred. The previous controller 1,460-pass receipt was not rerun or relabelled. Existing specification approval, protected CLAUDE approval block, real 24-hour observation, final controller review and owner gates are not closed by this slice. Independent quality acceptance remains with the reviewer/controller.
