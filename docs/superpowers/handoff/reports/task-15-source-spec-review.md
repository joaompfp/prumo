# Task 15 Part A - independent spec review (source + registry only)

Date: 2026-11-12. Reviewer: independent spec-review subagent (kimi-k3), second pass after the
implementer. Scope frozen to commits 2fb6e28..212cd17 on pipeline-rebuild,
/home/joao/projects/prumo-pipeline. Reviewed artifacts ONLY: ingest/sources/oecd.py,
tests/ingest/fixtures/oecd/ + MANIFEST.json, tests/ingest/oecd_fixtures.py,
tests/ingest/test_source_oecd.py, tests/ingest/test_registry_oecd_units.py, and the OECD hunks
of registry/core.yaml, registry/core.proposed.yaml, registry/licences-todo.md,
registry/mappings-oecd.md. Authoritative inputs: task-15-brief.md and the base-data-pipeline
design spec. The CSV verifier is Task 15 Part B, built concurrently in other files: its absence
is the declared next part, NOT a finding. No code, registry, tests, handoff, ledger or vault
edited; probes live under /home/joao/.hermes/cache/scratch/oecd_partA_probes.py.

## Verdict

PASS for the scoped Part A deliverable. No Critical findings; every mandatory axis of the brief
was probed with concrete fixture mutations and holds on the six shipped series. One Important
(latent, unreachable on the shipped registry) and two Minor hardening gaps are logged below; all
have one-line fixes that can ride the Part B/fix round. This is NOT a certification of Task 15
as a whole: the verifier (Part B), registered run_with_refetch live acceptance and the owner
licence clearance remain open gates.

## Verified (with evidence)

- Tests: ran the targeted scope myself - 43 source + 8 registry/evidence-pairing tests, 51
  passed in 6.3 s (.venv-ci/bin/python -m pytest, both files). ruff: All checks passed on all
  four new/edited python files. Registry mirror invariant: cmp core.yaml core.proposed.yaml
  equal. Did not rerun the 230 s full suite (dispatch bound); the self-reported 1077 = 1026
  baseline + 51 is consistent with the observed scope.
- Fixture genuineness: all six JSON fixtures are BYTE-IDENTICAL to the controller-rehashed
  discovery bodies (manifest items cli/bts-employment/bts-order_books/bts-production/
  bts-selling_prices/unemp "-json", sha256 c23c51a8, 554f0306, fdec7c7d, 08f40b05, 8ec8e04d,
  d5378b76...). Raw publisher bytes, sha256 pinned, final URL + HTTP 200 per MANIFEST.json
  entry; each <= 24 KB. Raw fixtures, not invented.
- Full decoding: all 77 observations across the six archives decode exactly as the named
  publisher pins (PINS table read from the recorded bytes; e.g. CLI 2026-04 = "99.83678", 5 dp
  despite DECIMALS=2; trailing-zero tokens "-6.0"/"12.0"/"6.0" preserved verbatim).
- Number tokens / JSON primitives: json.loads(parse_int=parse_float=_Num tagging)
  (oecd.py:145-147); a quoted numeric raises the type-flip error (probe-backed test
  test_quoted_numeric_value_raises); NaN/Infinity constants rejected via parse_constant;
  duplicate JSON keys rejected globally via object_pairs_hook; RawRow receives plain str
  only. No float/coercion anywhere in the module.
- Period indices / sparse maps: observation indices must be canonical ASCII decimal ("00" and
  fullwidth alias mutations both raise; out-of-range raises); the UNSORTED TIME_PERIOD values
  array is mapped by index (every fixture descends - a zip-sorter would fail the pins);
  duplicate period ids raise; metadata indices (keyPosition, structure, attribute, annotation)
  must be genuine JSON numbers, quoted aliases raise.
- Dimension identity: full pinned-code identity enforced per position - the payload series key
  resolves each dimension value and must equal the requested key segment (oecd.py:435-446);
  PRT->FRA and BCICP->LI drift mutations both raise. The semantic CLI trap (MEASURE=BCICP, not
  the dataflow-default LI) is pinned and documented (registry comment, mappings note,
  test_cli_is_bcicp...).
- Multiplier: UNIT_MULT pinned at TABLE level (values must be exactly {"0"}) AND resolved
  series level (must equal "0"). Probe P7: adding an UNREFERENCED UNIT_MULT=6 table value
  fails closed. DECIMALS asserted a digit string and never used.
- Status: OBS_STATUS table pinned to reviewed codes only - probe P6: adding an unreferenced
  code "B" to the table fails closed even though no observation references it; row-level
  mapping A->normal and any other resolved code raises. Only "A" exists in evidence
  (77/77 obs, controller-confirmed); the unenumerable codelist (discovery item 13, 404) makes
  fail-closed intentional - a documented limitation, not a missing P/E feature.
- Full six coverage / response_index: integration test runs run_dataset over all six series:
  77 observations, 0 quarantined, 6 raw_fetch rows, per-row provenance links 1..6; every RawRow
  carries response_index=i (tested per series).
- Archived identity / windows: offline parse re-derives identity from archived url+params;
  params keys subset of {startPeriod,endPeriod} as canonical YYYY-MM; URL query must be a
  strict projection of params - unknown, duplicated and contradicting keys all raise;
  declared window enforced as CONTAINMENT on decoded periods (out-of-window mutations raise);
  parse never binds to the instance window (correct per brief). Default fetch is full history
  (no params); explicit ctor window validated; malformed/inverted literals raise at
  construction; Unicode window literal rejected.
- Duplicates / partial responses: same series archived twice raises; unrequested series raises;
  URL-vs-body cross-pairing raises; duplicate native_code specs raise; multi-dataSet and
  multi-series payloads fail closed; empty-observations series fails closed; every non-2xx
  status raises in parse; fetch yields non-2xx untouched for pipeline classification.
- Registry: six entries carry complete native_code identities, canonical url, multiplier 0
  (UNIT_MULT evidence), seasonal_adjustment only where ADJUSTMENT=Y (cli correctly unset - AA
  is amplitude adjustment), base_year None, ids/indicator_keys/roles/units/geography preserved
  (unemp stays cross_check of unemployment_rate.PT.M with INE primary). licences-todo.md row
  rewritten with canonical terms URL, exact §3 grant wording + per-dataset third-party caveat
  and the CC-BY-4.0-is-written-content-only correction; redistribution_ok false, verifiable
  true, source not inactivated. Registry diff touches ONLY the oecd source block, the six oecd
  rows and the oecd licences row - every non-OECD definition byte-preserved (full diff read).
- HTML-error rejection, malformed-JSON rejection: tested and re-probed.

## Non-findings (controller-flagged candidates, resolved with spec grounds)

1. RawRow.unit_raw is always None and spec.unit is never compared inside parse. Grounds:
   validate's contract is "a missing unit means the source did not say, so spec.unit is
   authoritative" (ingest/validate.py docstring); the SDMX-JSON channel carries no row-level
   unit field at all (any UNIT_MEASURE-style series attribute id outside {UNIT_MULT, DECIMALS}
   fails closed, oecd.py:362-363). The unit CODE is nonetheless publisher-compared: UNIT_MEASURE
   is a pinned key dimension, so its code equality is enforced per series (oecd.py:443-446),
   and the registry pairing test re-reads (code, label) from the archived bytes and asserts the
   reviewed prose derivation (test_registry_oecd_units.py:114-116, UNIT_EVIDENCE). Same posture
   as the World Bank precedent (empty unit, fail closed if non-empty). Acceptable; no gap.
2. Missing one of the six responses returns an empty row list for that series with no raise
   (probe P2: unemp_m -> 0 rows, siblings parse normally). Grounds: Ruling M
   (progress-ledger.md:67) - a series with zero valid observations becomes a format_change
   event and the run continues; the run fails-validation only if EVERY series is empty or parse
   raises. The adapter behavior directly engages that ruling; the dataset does NOT silently
   pass as "fine" at pipeline level. Acceptable as designed; flagging only that parse() itself
   has no completeness signal (by design - completeness is the pipeline's ruling, not the
   adapter's).
3. Past quarterly/annual keys out of scope: TIME_PERIOD ids must match canonical YYYY-MM
   (oecd.py:333), so a quarterly payload fails closed rather than mis-parsing. No overbuild.

## Findings

### Important (latent; unreachable on the shipped registry)

F1. Extra-length registry key pins are silently unasserted (oecd.py:430-446). The identity loop
   iterates `enumerate(seg)` where seg = PAYLOAD series-key segments and indexes `key_pins`
   (registry key segments), but never checks len(key_pins) == len(series_dims). Probe P4: a
   spec carrying native_code "...PRT.M.BCICP.IX._Z.AA.IX._Z.H.X" (10 pins) with an archived
   URL/body of the real 9-dimension series PARSES - the 10th pin is never compared to
   anything, so a registry typo could pin an identity the publisher never confirmed (the exact
   fail-open class the BCICP/LI pin exists to kill). Latency: all six shipped native_codes are
   test-pinned to exactly 9 segments (test_source_oecd.py:532, 535) and live fetch of a
   10-segment key would almost certainly 404 (fail closed), so no current data risk. Fix is
   one line: require len(key.split('.')) == len(series_dims) before the loop. Brief letter:
   "ALL pinned dimension codes asserted against the requested key" - violated only for a pin
   count no shipped entry has.

### Minor

F2. Registry key SHORTER than the payload dimension count crashes with a raw IndexError
   (oecd.py:443, key_pins[pos] out of range) instead of a module ValueError (probe P5). Still
   fail closed (nothing parses, exception propagates), but the exception type escapes the
   adapter's error contract; same one-line length check as F1 resolves it.
F3. Series dimension ids are shape-checked only (_str, oecd.py:293) and never pinned to
   expected identities; probe P3: renaming id MEASURE -> MEASUREE in the payload still parses.
   Data binding is unaffected - keyPosition coverage, position uniqueness, TIME_PERIOD id/pos
   and every pinned value code are all enforced, so a relabelled id cannot rebind values - and
   the brief's "unknown extra dimensions must fail" (count/shape) is honored. Residual value of
   pinning ids is defense-in-depth against a future DSD revision silently renaming dimensions
   (the dataflow URN check pins agency+dataflow but only the VERSION PATTERN, not the exact
   version, per brief). Minor hardening, not a mandatory gap.

## Limitations of this review

Part B (CSV verifier, oecd-csv-evidence envelope, registration + independence subprocess
guard), live acceptance via run_with_refetch, per-dataset licence clearance and any CLI work
are open; no statement here covers them. Probes and this report are the only authored files:
/home/joao/.hermes/cache/scratch/oecd_partA_probes.py and this report. No commits, pushes,
deploys or merges performed.
