# Task 15 verifier fix 1: executable live bounds + semantic dimension identity

Date: 2026-11-12. Scoped fix on pipeline-rebuild, base 7b31909 (source F1/F2/F3 already
committed there and left untouched). Owner paths only: tests/ingest/test_verifier_oecd.py,
tests/ingest/live_bounds.py (new, test-local), ingest/verifiers/oecd.py,
this report. No registry/handoff/ledger/source edits, no production shared-core edits, no
network run.

## Scope and why

1. I1 (reviews/task-15-verifier-spec-review.md, Important, blocking): the live test bounded
   requests and the 150 s phase only as POST-HOC assertions. Now both are enforced while the
   phase runs: tests/ingest/live_bounds.py adds `BoundedRequestsHttp` (a RequestsHttp
   subclass; retries other than 0 refused) whose `_get_with_retries` override counts every
   PHYSICAL attempt (redirect hops and retry attempts included, since RequestsHttp.get
   re-enters per hop), refuses attempts beyond 18, refuses to start an attempt with <=1 s of
   wall budget left, and caps each attempt's socket timeout to min(client timeout, remaining
   budget, 12 s); plus `hard_deadline`, a signal.setitimer SIGALRM context that can abort a
   blocking socket read on the pytest main thread and restores the previous handler and the
   previously armed timer exactly as found. The live test wraps run_with_refetch in
   hard_deadline(150.0) with max_attempts=1/retries=0 unchanged; the old assertions
   (attempts <= 18, elapsed <= 150.0) are kept as the acceptance signal, no longer as the
   enforcement. `_Counting` deleted (it undercounted hops and enforced nothing).
2. M3: rolling window was off by one year for Jan/Feb runtimes. Replaced by month-index
   arithmetic `rolling_start_month(today)` (year*12 + month - 1, minus 14); parametrized
   tests cover Nov/Dec in-year, Jan/Feb rollover (2027-02 -> 2025-12, the exact trap), and
   the March boundary. Live semantics unchanged: bounded 14-months-back start, no end bound,
   expectations still re-derived from this run's freshly archived bytes, all 6 series,
   served == 0.
3. Controller finding (NEW - missed by the Part B spec review, reported here explicitly):
   `_header` accepted ANY uppercase dimension name with a non-blank label, so renaming
   MEASURE -> MEASUREE or REF_AREA -> FOREIGN_AREA with identical codes, or aliasing
   MEASURE/UNIT_MEASURE name cells, passed the 9 pinned-code slots. The brief requires
   unknown columns and semantic dimension identity to fail closed, mirroring the source-side
   F3 fix. ingest/verifiers/oecd.py now carries its own reviewed per-flow dimension id
   sequence (_DIM_IDS, duplicated on purpose, no collector import): STES flows pin REF_AREA
   FREQ MEASURE UNIT_MEASURE ACTIVITY ADJUSTMENT TRANSFORMATION TIME_HORIZ METHODOLOGY, the
   LFS flow pins REF_AREA MEASURE UNIT_MEASURE TRANSFORMATION ADJUSTMENT SEX AGE ACTIVITY
   FREQ, both in native key order (which equals the reviewed header pair order in items
   2,4,6,8,10,12). A renamed, repositioned, duplicated or aliased dimension name raises
   identity drift; an unlisted dataflow has no reviewed sequence and fails closed. Attribute
   pair order stays free (item 12 layout), unit/status/multiplier maps untouched, no data or
   licence policy change.

## Tests (RED -> GREEN)

RED before the verifier fix, on the new tests (bounded helper green from its own run):
- test_dimension_name_rename_with_identical_codes_fails_closed: DID NOT RAISE (CLI, EMP, UNE)
- test_ref_area_rename_to_foreign_area_fails_closed: DID NOT RAISE
- test_dimension_name_duplicate_and_identity_alias_fail_closed: identity-alias case wrong-
  message (misbinding surfaced as UNIT_MEASURE confusion, not identity failure)
- test_unreviewed_dataflow_carries_no_dimension_id_sequence: wrong failure (STRUCTURE_ID
  drift) instead of an unreviewed-flow identity failure

GREEN after ingest/verifiers/oecd.py fix:
- .venv-ci/bin/python -m pytest tests/ingest/test_verifier_oecd.py -q: 47 passed,
  1 deselected (live, controller-run) in 7.42 s
- Targeted scope: + test_source_oecd.py, test_independence.py (subprocess guard included),
  test_registry.py, test_registry_oecd_units.py: 93 passed in 20.92 s; combined verifier +
  independence rerun: 60 passed, 1 deselected in 13.36 s
- .venv-ci/bin/ruff check on the 3 authored files: clean
- Bounds proofs without real network: attempt counter sees redirect hops (2 hops = 2
  attempts, 3rd refused pre-socket), per-attempt timeout equals the 12 s cap and then the
  remaining-budget cap, deadline-spent attempts refused before touching the wire, a retrying
  client is constructively refused; SIGALRM abort proves a blocked sleep is interrupted
  (~0.3 s alarm vs 30 s sleep) and the global alarm state (handler AND armed foreign timer)
  is verified preserved after both fired and unfired hard_deadline use.
- GitNexus (refreshed on this worktree): impact read_csv_evidence and _header LOW (only the
  verifier's own check flow); detect-changes after the fix: medium risk tag comes from the
  controller's uncommitted HANDOFF.md edit, execution flows affected are only the OECD
  verifier's own Check flows. No symbol outside owned scope touched.

## Live gate state

No fresh network was run (no live execution now). The live test remains controller-run
(`-m live -s`) and is structurally unchanged in what it asserts: fresh archive-derived
expectations for all 6 series, verified state, served == 0 under redistribution_ok=false,
offline evidence replay. Only the enforcement of the budget/deadline and the window
arithmetic changed.

## Remaining risks / notes

- Residual from review I1 stands, narrowed: per-attempt timeout is now min(remaining, 12 s)
  so one hop cannot overrun the deadline, and SIGALRM aborts a blocked read on the main
  thread; a trickle exactly under the socket timeout still counts against the wall budget
  and is refused at the next attempt boundary - bounded by the alarm regardless.
- `_FakeSession` stub assignments to `http._session` are test-internal; Pyright flags them
  but Pyright is not part of this repo's acceptance (pytest + ruff).
- The semantic-identity table assumes header pair order == native key order, which every
  reviewed response (items 2,4,6,8,10,12) already satisfied and the positional pinned-code
  comparison already required. A genuine publisher reorder would now fail closed and need
  review - intended behaviour, stated in the module docstring.
- OBS_STATUS codelist remains unenumerated publisher-side (fail closed on anything but 'A'),
  unchanged from the Part B review limitations.
- Pyright-only diagnostics in the test file predate this change pattern (no pyright gate in
  repo tooling).
