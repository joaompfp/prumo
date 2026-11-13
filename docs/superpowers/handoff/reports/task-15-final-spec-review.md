# Task 15 OECD - final independent spec review (whole CODE scope)

Date: 2026-11-12. Reviewer: independent final spec-review subagent (kimi-k3), read-only.
Repo /home/joao/projects/prumo-pipeline, branch pipeline-rebuild, code frozen at e34c60f on
base 2fb6e28 (7b31909 source fix 1, e34c60f verifier fix 1). Authoritative inputs:
task-15-brief.md, the 2026-11-10 design spec, prior reviews task-15-source-spec-review.md
(F1 Important, F2/F3 Minor) and task-15-verifier-spec-review.md (I1 Important, M1-M5), fix
reports task-15-source-fix-1.md and task-15-verifier-fix-1.md. Scope: ingest/sources/oecd.py,
ingest/verifiers/oecd.py, tests/ingest/{oecd_fixtures.py, oecd_verifier_fixtures.py,
live_bounds.py, test_source_oecd.py, test_verifier_oecd.py}, fixtures + both MANIFEST.json,
the OECD hunks of registry/*, discovery evidence. No implementer active; no code edited
anywhere; the only authored file is this report. Probes:
/home/joao/.hermes/cache/scratch/oecd_task15_final_probes.py (ephemeral, zero HTTP, fixtures
and fake sessions only).

## Verdict

PASS for the whole Task 15 CODE specification at e34c60f. Zero Critical, zero Important, zero
blocking Minor findings. Both review-blocking items (F1, I1), both Minor hardening items
(F2, F3), the controller's verifier dimension-identity finding and M3 are closed, each
re-probed independently by this review (40 probes, all PASS, listed below). The LIVE
acceptance gate is NOT covered by this verdict: it remains pending, controller-run
(`-m live -s`, f0nix acceptance), and this PASS neither executes nor infers it.

## Executed verification (real runs, this review)

- Targeted suites: `pytest test_source_oecd.py test_verifier_oecd.py test_independence.py
  test_registry.py test_registry_oecd_units.py -q` -> 140 passed, 1 deselected (the live
  test) in 26.42 s. `ruff check` on all 7 OECD-authored Python files -> All checks passed.
  Full 230 s suite intentionally not rerun (parent runs it).
- Independent probes (my script, from scratch, no network):
  - F1/F2: 10-pin and 8-pin native_codes raise at parse_native_code; fetch over a 10-pin spec
    raises with ZERO http calls; an archived 10-pin URL fails closed offline; `_payload` with
    10- or 8-pin keys against the real 9-dimension body raises ValueError naming the pin/dim
    mismatch (never IndexError). oecd.py:140-144 grammar + 472-477 semantic site both hold.
  - F3: byte-anchored mutations of the genuine payloads all fail closed on the reviewed
    per-dataflow id sequence (oecd.py:339-347): MEASURE->MEASUREE in BOTH the STES CLI and the
    LFS unemployment payloads, duplicated id (METHODOLOGY->MEASURE), order drift (REF_AREA<->
    FREQ id swap), unreviewed dataflow URN. All six untouched payloads still decode to 77 rows.
  - Controller finding: verifier CSV header NAME identity (verifiers/oecd.py:141-163,
    _DIM_IDS:89-96, duplicated on purpose, no collector import): MEASURE->MEASUREE fails
    closed on ALL THREE flows (CLI, EMP, UNE), REF_AREA->FOREIGN_AREA fails, duplicated pair
    name fails, unreviewed dataflow carries no sequence and fails.
  - I1 live bounds (test-local, production contracts untouched): redirect hops count as
    physical attempts (3 hops script -> attempts==3; attempt 4 refused pre-wire), per-attempt
    socket timeout capped to 12.0 s and then to the remaining budget (2.00 s observed),
    deadline-spent attempt refused before any socket, retries=3 and positional retries
    constructively refused, hard_deadline(0.3) aborted a 30 s blocking sleep in 0.30 s with
    SIGALRM handler AND foreign timer restored exactly, rolling_start_month exact at the M3
    trap (2027-02 -> 2025-12) plus Jan/Mar/Dec boundary cases.
  - OBS_STATUS: an in-body A->P ('Provisional') mutation fails closed in the verifier; the
    source pins the reviewed table at definition level AND row level (oecd.py:425-429,
    683-686). Discovery item 13: full codelist probe answered 404 (manifest note: only 'A' in
    all 77 evidence observations), so fail-closed-on-unknown is intentional and documented,
    not a missing P/E/R/B mapping.
  - Provenance: all 12 fixtures sha256 == their MANIFEST.json pins == the discovery bodies
    (items 1-12), all status 200, all <= 200 KB. Genuine publisher bytes, no invented archive.
- Registration and independence: register_verifier static-allowlist test passes,
  assert_verifier_independent subprocess guard passes (collectors/ingest.flags/ingest.sources
  blocked), no allowlist change was needed; registration happens with the source importable in
  the same process. All inside the 140.
- Registry scope: `git diff 2fb6e28..HEAD -- registry/` touches ONLY core.yaml,
  core.proposed.yaml, licences-todo.md and the new mappings-oecd.md; the core.yaml deletions
  are just the old OECD dataset-stub native_codes and the stale licence lines; all six ids,
  indicator_keys, roles, units and geography preserved (oecd.unemp_m.PT stays cross_check of
  unemployment_rate.PT.M, INE primary); every OECD row now carries the complete 9-pin
  native_code, canonical url, multiplier 0, no invented base year; cli correctly carries no
  seasonal_adjustment (AA amplitude); core.yaml == core.proposed.yaml (cmp); source block has
  redistribution_ok: false and verifiable: true. licences-todo.md holds the canonical terms
  URL, the §3 grant wording, the per-dataset third-party-rights caveat and the
  CC-BY-is-written-content-only correction. No fallback, no quarantine policy change
  (test_clean_run_verifies_and_stays_unserved: 0 quarantined; null values -> non_numeric
  quarantine stays engine policy).
- Units/flags derive from published evidence, never echoed: verifier maps publisher
  UNIT_MEASURE code+label to prose and asserts it AGAINST spec.unit (drift raises, test);
  OBS_STATUS 'A' label 'Normal value' pinned; ADJUSTMENT/FREQ asserted against the registry;
  test_registry_oecd_units.py re-reads (code, label) from the archived bytes.
- Commit scope of the two fix commits verified (git show --stat): 7b31909 = source + source
  tests + its report; e34c60f = verifier + verifier tests + live_bounds + its report.
  Truthful, no handoff/ledger edits by implementers (HANDOFF.md modification is the
  controller's own uncommitted state).

## Findings

None blocking. No Critical, Important or Minor gaps remain open in the reviewed CODE scope.

Non-blocking notes already accepted with grounds in the prior reviews (restated, not
re-opened): M1 quoted CSV numeric framing accepted by csv.reader (exact-Decimal comparison
cannot be bypassed); M2 STRUCTURE_ID version digits unpinned per the brief's wording
(agency+dataflow pinned, drift caught by value/unit comparison). Both stand as design notes
for the ledger.

## Limits of this review

Live acceptance via run_with_refetch against sdmx.oecd.org was NOT executed (dispatch: no
HTTP; controller f0nix gate). The live test is code-reviewed and its bounds now execute
in-phase (BoundedRequestsHttp + hard_deadline(150.0), max_attempts=1/retries=0, 18 physical
attempts, non-stale expectations re-derived from the run's own archived bytes, all six
series, verified state, served == 0), but PASSING it is a separate pending controller action
and is NOT claimed here. The controller's source-phase preflight (full six-history HTTP 200
parse, all OBS_STATUS=A) is referenced in task-15-source-fix-1.md and is consistent with the
in-repo evidence state, but the run itself is the controller's record and was not re-executed.
The 9-pin grammar and both dimension-id tables are reviewed constants of the three current
flows; admitting another flow fails closed by default until new genuine evidence and review -
documented limitation, intended posture. OBS_STATUS full codelist remains unenumerable
publisher-side (item 13, HTTP 404).
