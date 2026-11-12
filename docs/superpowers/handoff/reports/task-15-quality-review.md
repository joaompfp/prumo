# Task 15 OECD - independent quality review (controller-dispatched, read-only)

Date: 2026-11-12. Reviewer: independent quality-review subagent (kimi-k3), read-only.
Repo /home/joao/projects/prumo-pipeline, branch pipeline-rebuild, range 2fb6e28..e34c60f
(post final spec PASS). Dispatch: probe implementation and live-test assertions, prove or
disprove the controller's candidate findings with tools, zero HTTP, no repo edits except this
report. Inputs: task-15-brief.md, task-15-final-spec-review.md, task-15-source-fix-1.md,
task-15-verifier-fix-1.md, task-15-discovery.md + manifest.json, the full code/tests/registry
diff, and my own probes under /home/joao/.hermes/cache/scratch/oecd_t15_quality_probes.py
(fixtures + sqlite3 semantics only).

## Verdict

REQUEST_CHANGES. Two deterministic defects proven in the OECD live acceptance test (both
fail on the genuine publisher shape, i.e. the live gate as written cannot pass), one
acceptance-evidence overclaim in the same test's docstring, plus two minor report issues.
Production adapter code (ingest/sources/oecd.py, ingest/verifiers/oecd.py) shows no Critical
or Important defect across every probe this review ran; the blocking findings are confined to
tests/ingest/test_verifier_oecd.py and report prose.

## Critical (block acceptance)

C1. Live test asserts SQL min/max against emission-row endpoints.
    tests/ingest/test_verifier_oecd.py:722 `assert (lo, hi) == (rows[0].period_raw,
    rows[-1].period_raw)`. `lo`/`hi` are SQL MIN/MAX aggregates (order-independent);
    `rows[0]`/`rows[-1]` are the first/last rows of the publisher's UNSORTED emission order
    (the adapter's own contract: TIME_PERIOD values array unsorted, mapped via values[i].id;
    the offline source tests deliberately dict-compare at test_source_oecd.py:156 because
    order is non-semantic). Probe over the six GENUINE fixtures (byte-identical to discovery
    items 1,3,5,7,9,11, parsed with the real OecdSource):

      series              rows  first    last     min      max      holds?
      oecd.cli.PT          13   2026-02  2026-01  2025-10  2026-10  NO
      oecd.employment.PT   13   2026-07  2026-02  2025-10  2026-10  NO
      oecd.order_books.PT  13   2025-12  2025-11  2025-10  2026-10  NO
      oecd.production.PT   13   2026-07  2026-04  2025-10  2026-10  NO
      oecd.selling_prices  13   2026-06  2026-05  2025-10  2026-10  NO
      oecd.unemp_m.PT      12   2025-10  2026-08  2025-10  2026-09  NO

    All six genuine payloads fail the assertion; a live response of the recorded shape makes
    the gate fail regardless of adapter correctness. Fix: compare (lo, hi) against
    (min/max over [r.period_raw for r in rows]).

C2. Live test quarantine assertion is inverted in the complete-data case.
    tests/ingest/test_verifier_oecd.py:726-727 `assert sorted(quar) == sorted(
    {"non_numeric": sum(null counter)}.items())`. `quar` is `SELECT reason, COUNT(*) FROM
    quarantine ... GROUP BY reason`: over an empty quarantine set SQL returns `[]`, while the
    expected side is always the one-entry list `[('non_numeric', N)]`. With zero nulls the
    assertion compares `[]` to `[('non_numeric', 0)]` and FAILS; it only passes when at least
    one row is quarantined. Proven with sqlite3 (empty GROUP BY -> []) and the genuine
    evidence: all 77 archived observations are non-null and the brief states the real window
    has no missing cells, so the expected good case is exactly the failing case. Fix: build
    the expected map only from reasons with count > 0 (or assert `{}` == actual when no
    nulls).

## Important (resolve before acceptance)

I1. Live test docstring overclaims what the gate proves.
    tests/ingest/test_verifier_oecd.py:706-708 claims the offline re-parse "asserts DB ==
    publisher archive exactly, incl. row loss between fetch and write". Actual assertions:
    per-series row COUNT vs archived non-null count, an endpoint pair (broken per C1), and
    the 12-item verification sample with per-item envelope replay (lines 730-741). Row loss
    IS caught by the count; a value/flag corruption on an unsampled, non-extreme row is not
    detected by any assertion. This statement will propagate into the controller's acceptance
    record. Fix: reword to the actual coverage, or make it true by pulling
    (series_id, period, value_text) for the run and set-comparing against the offline parse.

## Minor

M1. Discovery report budget prose does not reconcile with its own manifest.
    task-15-discovery.md section 0 headline: "21 publisher/site requests + 3 web-tool
    fetches"; its own breakdown sums to 18 (12 data API + 1 codelist 404 + 1 f0nix egress +
    3 www curl + "1 f0nix repeat (403)"). Manifest ground truth: 20 items total = 17 archived
    publisher HTTP + 3 web-tool; items 15-17 are all f3nix egress, so the "+ 1 f0nix repeat
    (403)" has no archived item (section 9 attributes the only repeat to the local curl-23
    capture failure on f0nix data probe item 14, which IS archived once). "last 14:20:08Z
    (~224 s)" vs manifest last publisher request 14:20:02Z (217 s); "web-tool ... ~14:26Z"
    vs manifest note "same session window 14:21-14:24Z". Classification: documentation
    bookkeeping inconsistency in the audit trail, NOT a data fallacy and NOT a budget breach
    (every reading is <= 21 requests and <= 224 s against the <= 30 / <= 360 s limits; bodies,
    statuses and sha256 all archived and rehashed clean). Fix the section 0 numbers/labels to
    match manifest.json.

M2. New U+2014 em-dashes in task-authored files despite the plain-hyphen style rule for
    authored files (reported per dispatch; files NOT edited by this review):
    docs/superpowers/handoff/reports/task-15-source-implementation.md (12 added),
    ingest/sources/oecd.py docstring (7), ingest/verifiers/oecd.py docstring (4),
    registry/core.yaml and core.proposed.yaml new comments (4 each), registry/licences-todo.md
    (2), registry/mappings-oecd.md (11), tests/ingest/oecd_fixtures.py (4),
    oecd_verifier_fixtures.py (1), test_registry_oecd_units.py (1), test_source_oecd.py (4),
    test_verifier_oecd.py (4). Baseline core.yaml already carried 8 em-dash lines pre-task, so
    registry comment style predates this task; the authored REPORT and new code docstrings are
    the clear violations. The U+2013 en-dashes inside the four bts publisher JSON fixtures are
    original publisher bytes and must never be normalized - correctly untouched.

## Verified PASS areas (independently re-probed, no reliance on prior reviewers)

- Fail-closed adapter contract: 9-pin grammar with per-flow semantic dimension id pinning;
  genuine-JSON-number tagging (_Num) with plain-str return and quoted-numeric rejection;
  canonical ASCII decimal indices ('00'/Unicode aliases rejected); UNSORTED TIME_PERIOD
  mapped through values[i].id; duplicate JSON keys, sparse duplicate/malformed observations,
  extra series keys, multiplier != 0, unknown OBS_STATUS (definition-table and row level)
  all raise; archived-window containment and URL/params projection identity enforced;
  RawRow.response_index set; non-2xx fail-closed.
- Verifier: header parsed by NAME with reviewed per-flow dimension id sequences (renamed,
  duplicated, repositioned, aliased columns raise; unlisted dataflow has no sequence and
  fails); pinned STRUCTURE_ID/ACTION and request-pinned codes; exact plain-decimal tokens,
  no floats anywhere; UNIT_MEASURE/FREQ/ADJUSTMENT asserted against the registry, never
  echoed; versioned oecd-csv-evidence v1 envelope carries the actual final URL + actual
  status + base64 body and replays offline (tested).
- Registry scope: only OECD hunks of core.yaml/core.proposed.yaml/licences-todo.md plus new
  mappings-oecd.md; all six ids, indicator_keys, roles, units, geography unchanged
  (oecd.unemp_m.PT stays cross_check, INE primary); multiplier 0 documented from evidence;
  cli BCICP identity trap documented; redistribution_ok: false, verifiable: true;
  core.yaml == core.proposed.yaml (cmp). No SQL or core-contract edits anywhere in the
  range (diff file list).
- Live bounds helper: BoundedRequestsHttp counts every physical attempt including redirect
  hops, refuses attempts beyond 18 and attempts starting with <= 1 s wall budget, caps each
  socket timeout to min(client, remaining, 12 s); retries != 0 (keyword or positional)
  refused. hard_deadline aborts a blocked 30 s sleep in 0.3 s via SIGALRM and restores the
  previous handler AND a pre-armed foreign timer exactly (both tested, pre-existing timer
  preserved). rolling_start_month month-index arithmetic exact on the 2027-02 -> 2025-12
  rollover trap. 18 attempts against the expected 12 requests leaves only redirect slack;
  coherent.
- Tests are not just green: 30 named exact publisher pins checked against BOTH channels,
  complete 77-cell content asserted per series (order-free dict comparison), tamper/rename/
  drift mutations fail closed, registration allowlist + subprocess independence guard pass.
  Independently reproduced this review: targeted suites 140 passed, 1 deselected in 26.74 s;
  ruff clean on all 8 authored Python files.
- No auto fallback, no outage-driven inactivation, no precision/tolerance relaxation found
  in the diff or code.

## Limits of this review

No HTTP run (dispatch; controller executes the live gate). Test-only findings C1/C2 were
proven against genuine archived publisher bytes and SQL semantics, not by a live run - they
are deterministic on the recorded shape. The source-spec review's M1/M2 design notes and the
fail-closed OBS_STATUS posture stand as accepted. Live-test line 712 reconstructs collector
RawResponses with a hardcoded status=200 (raw_fetch ok=1 stands in for the stored status);
parse requires 2xx so behaviour is unchanged, but the collector replay does not re-assert the
archived status the way the verifier envelope does - nit, optional.
