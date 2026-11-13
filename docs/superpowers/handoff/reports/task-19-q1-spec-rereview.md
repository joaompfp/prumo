# Task 19 Q1 independent specification re-review

Verdict: PASS_AUTHORED_SCOPE

## Scope and finding

The standalone manual-import correction satisfies Q1 in the reviewed authored scope. No specification change is requested.

Reviewed `task-19-quality-review.md` Q1 and `task-19-quality-fix-1.md`, the bounded correction brief, the actual first Bash fence under `docs/data/operations.md`'s manual-update section, and `tests/test_manual_runbook.py`. Consulted the linking/manual-date paragraphs in `docs/data/manual-refresh.md` and the existing focused runbook contract. The live worktree was on `pipeline-rebuild` with the pre-existing dirty authored package; review used its actual current files, not an assumption that HEAD contained the correction.

Generator, methodology and previously accepted F1/F2 scope were not reopened. This is a specification re-review of Q1, not final whole-branch quality approval or production acceptance.

## Verified correction

- `docs/data/operations.md:306-337` is independently executable as a standalone subshell. Its own `set -euo pipefail` precedes validation and operator commands; it does not rely on the bootstrap fence or prior shell options.
- The stop at line 327 must succeed before readback. The assignment at line 328 independently preserves a failed `docker inspect` exit status; a successful command must then yield `false` after Bash command-substitution newline removal. Failed inspection, running state, empty output and malformed output all stop before destination preparation.
- Directory creation, destination nonexistence check and copy are separate strict-mode prerequisites at lines 330-332. Each injected failure prevented import; directory/refusal failures prevented copy as well. The refusal remains `test ! -e` on the exact bundle destination.
- Import failure at line 333 exits the subshell nonzero before diagnostic status at line 334. A successful status cannot conceal that failed import. Status failure after a successful import also remains nonzero.
- The exact fence preserves the normal clean parent shell: it remains alive after success, invalid arguments and every injected operational failure. Independent probes checked unchanged parent shell flags, `SHELLOPTS` and sentinel values for variables/array names assigned inside the fence.
- No start/restart command is present in this fence or appeared in any captured call trace. The separate resume fence remains subject to approval, result/date review and the silent SOPS prerequisite in adjacent prose.

The guarantee exercised here is the documented standalone invocation in a normal clean Bash parent with errexit initially disabled. It does not claim new concurrency locking or safety for a fence rewritten into an errexit-suppressing conditional context. The documented requirement that no other CLI writer be active remains necessary.

## Actual focused test execution

Ran only the new safe-stub tests and the existing selected runbook contract:

```text
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv-ci/bin/python -m pytest tests/test_manual_runbook.py tests/test_docker_contract.py::test_operator_runbook_links_authoritative_manual_refresh_and_has_valid_shell -q -p no:cacheprovider --basetemp="$TMPDIR/task19-q1-spec-rereview-pytest"
```

Actual result: 12 passed in 0.27s, exit 0; Python 3.12.3, pytest 9.2.0. This includes the exact manual-fence syntax test and the existing syntax-only check of operations Bash fences; the other fences were not operationally executed.

Inspected the new harness before execution. It extracts the actual documented fence, starts `/bin/bash --noprofile --norc` with errexit off, replaces the external commands with in-memory functions, removes executable directories from PATH, applies a DEBUG command allowlist and asserts no files are created in its isolated working directory. Its failed import requires exit 23 with no status call. Existing-destination, preparation, copy, stop and readback failures are covered. Its success cases check World Bank/E-REDES options and reject unexpected Docker/start commands.

## Additional independent safe-stub execution

Executed a separate in-memory Python/Bash harness, without importing or modifying the authored test harness. It extracted the same actual fence and ran it verbatim, not inside an `if`, `&&`, `||` or other errexit-suppressing wrapper. Each Bash process used `/bin/bash --noprofile --norc`, initially disabled errexit/nounset/pipefail and an empty-executable PATH. All fence external commands (`test`, `basename`, `bash`, `docker`) were shell functions. There was no real Docker, alias, filesystem-write or network execution from the fence. The isolated scratch working directory remained empty.

The independent harness captured every stub invocation in one ordered stderr stream with NUL-separated arguments. Python compared exact argument tuples, avoiding the authored harness's reliance on flattened `$*` for some command recognition. All 23 cases passed:

| Probe | Actual result |
|---|---|
| World Bank with indicator; World Bank without indicator; E-REDES | Exit 0; exact manifest/basename/stop/readback/mkdir/refusal/copy/import/status order |
| Manifest failure | Exit 31; no basename, stop or later operation |
| Stop failure | Exit 32; no readback, destination operation or import |
| Inspection failure | Exit 33; no destination operation or import |
| Directory creation failure | Exit 34; no refusal, copy or import |
| Existing-destination refusal | Exit 35; no copy or import |
| Copy failure | Exit 36; no import or status |
| Import failure | Exit 37; no status, despite a status stub that otherwise returns 0 |
| Status failure after successful import | Exit 38; failure remains visible |
| Readback empty, `true`, `False`, `false extra`, or repeated `false` lines | Exit 1 in each case; no destination preparation or import |
| Inspection emits `false` but exits nonzero | Exit 33; no destination preparation or import |
| Missing host, missing source, or relative host | Exit 1; no external stub call |
| Unsupported source | Exit 2; no stop or later operation |
| E-REDES missing original start or end bound | Exit 1; no stop or later operation |

Every case additionally asserted parent survival, unchanged shell flags/options and unchanged parent sentinel variables/array.

Exact success tuples retained the space-bearing bundle directory as a single argument for both copy and `--bundle`. Stop was exactly `bash -lic 'dc-web stop prumo-ingest'`, followed by `docker inspect prumo-ingest --format '{{.State.Running}}'`. Import and status both retained `docker exec prumo python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw`, with global options before the subcommand. World Bank retained `run worldbank --bundle <target>` and only appended `--indicator SP.POP.TOTL` when set. E-REDES retained `run eredes --bundle <target> --from 2026-11-10 --to 2026-11-11`, without the World Bank indicator. No unexpected call or automatic restart appeared.

## Preserved operational and timestamp semantics

`operations.md:288-304` still delegates capture/validation to the authoritative manual refresh, requires the owner to authorize interruption during the existing observation, prohibits concurrent CLI writers and requires original inclusive E-REDES bounds rather than today's dates or substituted receipt timestamps. Import diagnostics remain a separate action after failure, with review before any restart.

`operations.md:339-352` still requires recording a stop, starting a new observation window after resumption and refusing to close the original window using interrupted uptime. It preserves `input_origin=recorded`, import-attempt `started_at`, original-capture `real_data_fetched_at`, unchanged-byte shortcut limitations and visible stale/partial/invalid refusal. `manual-refresh.md:98-109,111-137` retains the same authoritative production sequence and distinction between original retrieval and import/verification time. No pipeline timestamp behavior was changed or reimplemented by this correction.

## Boundaries and remaining gates

Only this report was authored. No implementation, tests, runbook, shared handoff state, evidence, protected instruction file or production service was edited. Before/after SHA-256 comparisons were unchanged for the inspected operations/manual documents, both test files, Q1 quality review/fix reports and protected `AGENTS.md`/`CLAUDE.md`; this is a bounded input-integrity check, not a claim of auditing every concurrent controller file.

No real Docker, SSH, SOPS, source, network or production command, whole-suite run, delegation, commit, push, merge or deployment occurred. The controller's separate final full-suite run was neither duplicated nor assumed successful here. The author's historical RED result is attributed evidence only; this reviewer independently ran the current GREEN tests and additional probes above.

Protected `CLAUDE.md` approval remains open/blocked. The real Task 18 observation cannot close before `2026-11-14T01:21:18.732242+00:00` and still requires actual continuity/end evidence and controller review. Final whole-branch review, controller reconciliation, unresolved source-rights decisions and final owner acceptance remain open. PASS_AUTHORED_SCOPE closes only this bounded Q1 specification re-review.
