# Task 15 Part A — OECD source implementation report

Date: 2026-11-12. Author: implementer subagent (kimi-k3). Base 2fb6e28, branch
pipeline-rebuild, /home/joao/projects/prumo-pipeline. Scope: Part A ONLY per dispatch —
the collector (`ingest/sources/oecd.py`), original JSON fixtures, source + scoped registry
tests, registry/core.yaml six OECD entries + source licence block, licences-todo.md,
registry/mappings-oecd.md. The verifier (Part B), live acceptance, CLI/scheduler, reviews and
any handoff/ledger/vault edits are explicitly out of scope and untouched.

## Delivered

| path | what |
|---|---|
| ingest/sources/oecd.py | `OecdSource` — SDMX-JSON data 2.0 collector (fetch + parse) |
| tests/ingest/fixtures/oecd/ | 6 genuine publisher bodies + MANIFEST.json (sha256 pins; byte-identical to discovery items 1,3,5,7,9,11; verified against discovery hashes at copy time) |
| tests/ingest/oecd_fixtures.py | fixture accessors + routing FixtureHttp |
| tests/ingest/test_source_oecd.py | 43 source tests |
| tests/ingest/test_registry_oecd_units.py | 8 registry/evidence pairing tests |
| registry/core.yaml, registry/core.proposed.yaml | six full identities + corrected source licence block (proposed mirrored to preserve the equality invariant) |
| registry/licences-todo.md | oecd row rewritten with the 2026-11-12 read |
| registry/mappings-oecd.md | semantic mapping note (BCICP-vs-LI trap, unit derivations, grammar) |

## TDD record

- RED: `ModuleNotFoundError: No module named 'ingest.sources.oecd'` at collection
  (full failing-run output captured at the time).
- Iteration: two real mis-assumptions fixed against evidence, not guessed —
  (a) `dimensionGroupAttributes` keys are arbitrary dimension-subset keys (9- and 10-segment
  keys both occur), (b) series-request responses list hierarchy PARENTS as extra dimension
  values (ACTIVITY carries C + _T); the pinned code is the value the series key's index
  resolves to, so identity = value-at-key-index equality per dimension (exactly what the
  BCICP/LI drift test exercises).
- GREEN: `43 passed tests/ingest/test_source_oecd.py`, `8 passed
  tests/ingest/test_registry_oecd_units.py`.
- Full suite after both commits: **1077 passed, 6 live deselected, 1 warning in 230 s** —
  controller baseline 1026 + 51 new tests, zero regressions; core.yaml==core.proposed.yaml
  invariant tests pass.

## Contract coverage (mandatory deep points)

- Number tokens: genuine JSON number primitives preserved verbatim via `json.loads(
  parse_int=_Num, parse_float=_Num)` tagging; quoted numerics, non-finite constants and
  duplicate JSON keys raise. No float/rounding anywhere; `DECIMALS` asserted but never used
  (CLI publishes 5-dp tokens under DECIMALS=2).
- Indices: series keys and observation indices must be canonical ASCII decimal (`0` vs `00` vs
  Unicode aliases all rejected); observation index → UNSORTED `values[i].id` mapping (every
  fixture exercises a descending TIME_PERIOD array; zip-sorting would fail the pins).
  keyPosition/structure/attribute/annotation indices must be genuine numeric primitives.
- Identity: native_code grammar `<agency>,<dataflow>/<key>`; URL netloc/path, params ⊆
  {startPeriod,endPeriod} canonical YYYY-MM, URL query a strict projection of params; dataflow
  URN (`Dataflow=<agency>:<dataflow>(version)`) and datastructure URN pinned to the request;
  ALL pinned dimension codes asserted against the requested key; action='Information',
  errors==[], single dataSet/structure/series.
- Multiplier/status: UNIT_MULT must resolve 0 ('Units') twice (table + series attributes);
  OBS_STATUS table must contain ONLY reviewed code 'A' (map A→normal) and every observation
  attribute index must resolve in range — unknown codes fail closed even when unreferenced,
  per the unenumerable codelist (discovery item 13). BASE_PER does not exist on the JSON
  channel (CSV-only, empty in evidence).
- Missing values: `null` → value_raw=None → quarantined non_numeric (tested via mutation;
  the real window has none, as briefed).
- Window: default full-history fetch (no params); explicit `start_period`/`end_period`
  ctor-validated canonical YYYY-MM; archived window enforced as a containment constraint on
  decoded periods in offline parse; final URLs byte-match the manifest's archived evidence URLs.
- Every row carries `response_index`; a series archived twice, an unrequested series, or a
  duplicate native_code spec all raise. No pagination: evidence shows one complete body per
  request; multi-dataSet/series payloads fail closed.

Pipeline integration test: `run_dataset` over all six series → 77 observations written,
0 quarantined, 6 raw_fetch rows, per-row provenance links to responses 1..6.

## Registry / licence

- Six entries: complete `native_code` identities, `url` = canonical request address,
  `multiplier: 0`, `seasonal_adjustment: "Calendar and seasonally adjusted"` where ADJUSTMENT=Y
  (cli left unset: AA is amplitude adjustment, not seasonal — documented), no invented base
  year. Units/ids/indicator_keys/roles/geography untouched; unemployment stays cross_check of
  `unemployment_rate.PT.M` (INE primary). No inactivation, no proposal regeneration.
- Source block: canonical terms URL, T&C §3 grant wording with third-party caveat, corrected
  off "believed CC BY 4.0" (written-content-only licence); `redistribution_ok: false`,
  `verifiable: true`. licences-todo.md row carries the full read incl. the 403=bot-wall
  correction.

## Tooling compliance

GitNexus index fresh on 2fb6e28 (alias prumo-pipeline); no existing symbols modified (new
module/classes only, zero pre-existing callers; controller's sync_registry impact ran LOW and
the contract is unchanged); `gitnexus detect-changes -r prumo-pipeline` before commits: LOW,
0 affected processes, 3 tracked files. No network used at implementation time. Lint:
`.venv-ci/bin/ruff check` clean on all new/edited python files.

## Commits

- `05fdd3b` feat(ingest): OECD SDMX-JSON data 2.0 source adapter (Task 15 Part A) — 10 files.
- `8847d84` feat(registry): OECD scoped metadata from Task 15 publisher evidence (Part A) —
  5 files.

## Remaining gaps for Part B (explicit, not hidden)

1. `ingest/verifiers/oecd.py` (csvfilewithlabels channel, `oecd-csv-evidence` envelope),
   its tests/fixtures, registration and independence subprocess guard — NOT started. CSV
   fixtures (discovery items 2,4,6,8,10,12) are controller evidence awaiting Part B.
2. Decimal-exact (not token-exact) comparison policy: CSV trims trailing `.0` (-6.0↔-6 etc.,
   7/77 cells) — verifier must compare by Decimal equivalence, never string equality.
3. Live acceptance (`run_with_refetch`, fresh f0nix archive, full active coverage, served=0
   under redistribution_ok=false) — controller's separate gate.
4. OBS_STATUS full codelist remains unenumerated (publisher 404 on the probed id); fail-closed
   on non-'A' stands until official codelist evidence is supplied and independently reviewed.
5. Per-dataset third-party licence clearance for DF_CLI/DF_BTS/DF_IALFS_UNE_M is the owner's
   outstanding duty before any serving.
