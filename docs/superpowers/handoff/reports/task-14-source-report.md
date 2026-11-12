# Task 14 Part A — FRED source adapter, registry disposition, fixtures (implementer report)

2026-11-12, implementer Part A only (no verifier — Part B is a fresh agent). Base
`pipeline-rebuild` @ 38aad8c. Controller baseline: 929 passed / 5 live deselected / 162.96 s.

## What was built

- `ingest/sources/fred.py` — `FredSource` (`name='fred'`, `expected_format='json'`):
  - Credential: explicit `api_key=` or env `FRED_API_KEY`; clear `ValueError` when missing/blank;
    the legacy `.fred_api_key` file is never read (tested, incl. empty-cwd construction).
  - Wire: `GET api.stlouisfed.org/fred/series` then `/fred/series/observations` per unique
    series, `file_type=json`, `limit=100000`; units=lin / output_type=1 / order_by / sort_order=asc
    are the FRED defaults, asserted in-payload (never requested as transforms). Offset pagination
    followed per declared `count` with no-progress guard. Fetch yields RawResponses incrementally
    (metadata archived before a later observations failure).
  - Secret hygiene: the key is on the wire request only; the yielded RawResponse carries the
    key-stripped final URL and api_key-OMITTED params (documented in the fixture manifest);
    a response body echoing the key is refused BEFORE yield (bytes never archived/mutated);
    network errors are re-raised as `FredRequestError` (exception type + series id only — no
    request URL, no response excerpt). Core HTTP contract unchanged.
  - Parse: identity from archived url/params (an archived `api_key` fails closed as a leak).
    Metadata (mandatory per series) asserts id/frequency=M/NSA and the runtime unit
    (metadata `units` == registry's exact publisher label, fail closed otherwise). Observation
    values are JSON STRINGS (verbatim token; '.' -> `value_raw=None` for the 144 pre-1992 missing
    cells — kept, never truncated; a JSON-number value is an unknown primitive and raises).
    `flag_raw='normal'` declared for the reviewed no-status-surface shape; unknown
    per-observation keys raise. Duplicated dates, non month-first dates, count/offset/limit
    truncation, realtime identity drift, unknown shapes all raise. `last_updated` is
    shape-checked metadata only (never a per-observation released_at).
    `RawRow.response_index` points at the observations response; metadata responses stay archived.
- `tests/ingest/fred_fixtures.py` + `tests/ingest/test_source_fred.py` (34 tests) +
  `tests/ingest/test_registry_fred_units.py` (11 tests).

## TDD

- RED: tests written first; collection failed with `ModuleNotFoundError: No module named
  'ingest.sources.fred'` (34 errors) before any adapter existed.
- GREEN: `ingest/sources/fred.py` implemented; iterated to
  `tests/ingest/test_source_fred.py ... 34 passed` and both new files `45 passed in 45.65s`.
- Full suite after all registry changes: **974 passed, 5 live deselected, 208.77s** (929 + 45
  new). Two pre-existing tests (`test_registry.py::test_core_registry_loads_and_syncs`,
  `test_registry_dgeg_disposition.py::test_core_equals_proposed_and_invariants_hold`) pin
  `core.yaml == core.proposed.yaml`; the identical FRED edits were mirrored there.

## Registry (FRED portions only)

- 12 active IMF globals now carry native_code, exact publisher unit labels from the archived
  metadata, `seasonal_adjustment: NSA`, canonical series URL and explicit `active: true`
  (`registry/unmapped-fred.md` has the full table). The 5 `commodity_*` primaries (iron_ore,
  nickel, soybean, sugar, zinc) got their missing native_code filled from the proven twin mapping;
  no role swap.
- 8 inactivated with original fields preserved (`active: false` added only): 5 coded
  same-source cross-check twins + WPU101 steel (US BLS Index 1982=100, not a USD WORLD price:
  evidence `meta-WPU101.json`) + MHHNGSP natural gas (US Henry Hub USD/MMBTU, not a global
  benchmark: evidence `meta-MHHNGSP.json`). 313-period duplicate `fred.commodity_steel.WORLD`
  documented. Legacy `commodity_cotton` orphan stays `not_in_registry`, never mapped to
  PCOTTINDUSDM.
- Source block: `redistribution_ok: false`, explicit `verifiable: true`, terms-read comment.
  `registry/licences-todo.md` fred row updated with the read terms, the verbatim deferral quote
  ("making the data series available through the FRED API does not constitute such permission"
  — verified against the archived bytes), and IMF permission UNCONFIRMED.
- New-unit discipline: the correction names the units FRESH data will publish. A legacy test
  (`test_legacy_usd_rows_are_rejected_unit_mismatch_not_relabelled`) proves the UNCHANGED
  importer quarantines old bare-'USD' FRED rows as `unit_mismatch` (no relabel) and still
  accepts rows carrying the exact new label. No importer/SQL changes.

## Fixtures / evidence

- `tests/ingest/fixtures/fred/` — 48 publisher originals + MANIFEST.json (sha256/bytes/status/
  fetched_at/key-free url+params per file; each <= 200 KB): `meta-<CODE>.json` (12),
  `obs-<CODE>.json` (12; 561 cells each = 417 values + 144 '.'), `table-<CODE>.html` (12;
  the server-rendered `/data/<CODE>` table, Part B's independent channel),
  `fredgraph-<CODE>.csv` (12; rejection evidence only).
- `docs/superpowers/handoff/evidence/task-14-fred/` — rights/conflict originals:
  `fred-api-terms.html`, `meta-WPU101.json`, `meta-MHHNGSP.json`, their series pages,
  `csv-decimal-mismatches.json` (controller computation, labeled NOT publisher bytes),
  `f0nix-probes.json` (production-egress 200s), MANIFEST.json.
- Offline cross-channel re-verification: for all 12 series, every one of the 417 API JSON-string
  values equals the corresponding HTML-table cell as exact Decimal
  (`test_every_api_value_matches_the_html_table_exactly`), plus >= 5 named pins
  (PINS covers 9 named (series, period) cells). API metadata nonmissing range
  1992-01..2026-09 preserved; the observations endpoint's 1980-01..1991-12 144 '.' cells per
  series all land as `non_numeric` quarantine (never truncated).

## CSV rejection evidence (why fredgraph.csv is NOT the verifier)

Exact-Decimal zero-tolerance comparison of API vs fredgraph.csv tokens
(`csv-decimal-mismatches.json`): nonzero differences on 10 of 12 IMF series (binary-float tails;
e.g. POILBREUSDM 2006-05: API `70.51` vs CSV `70.51000000000001`). Counts per series: PALUMUSDM 0,
POILBREUSDM 53, PCOFFOTMUSDM 231, PCOPPUSDM 39, PMAIZMTUSDM 242, PCOTTINDUSDM 117, PWHEAMTUSDM
277, PIORECRUSDM 82, PNICKUSDM 134, PSOYBUSDM 5, PSUGAISAUSDM 0, PZINCUSDM 193. The genuine
independent channel is the server-rendered data-table HTML (12/12 HTTP 200, exact match).

## Scope notes / boundaries

- No verifier, no `ingest/verifiers/*`, no importer/pipeline/registry-generation changes,
  no handoff/ledger edits, no main/deploy/push, no Task 13 / Task 15 work. Live gate and full
  fresh production-egress acceptance remain with the controller.
- The adapter never touches the real key: tests use a labelled sentinel; `.fred_api_key` was
  never read during implementation.
