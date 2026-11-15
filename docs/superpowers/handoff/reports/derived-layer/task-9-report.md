# Task 9 report: starter derived series, docs, handoff

Status: DONE (Steps 1-5; Step 6 deploy is the controller's, owner-gated, not before 2026-11-15 10:25 UTC).

## Files
- `tests/ingest/test_registry_derived_starter.py` (new): `test_starter_set_loads`, `test_starter_bases_are_active_redistributable_primary`, `test_keys_follow_base_id_and_formula` (extra), `test_no_pct_formula_on_percent_or_balance_units`, `test_pp_entries_declare_pp_unit` (also: every `*_pct` entry has unit `%`), `test_every_label_is_nonempty_portuguese_text` (label stripped, not the key, does not contain the base id, and contains the Portuguese reading for its formula: "variação homóloga" / "variação face ao período anterior" / "índice").
- `registry/core.yaml` + `registry/core.proposed.yaml`: the same `derived:` block appended after `series:` to both files. `core.proposed.yaml` has to change because `tests/ingest/test_registry_dgeg_disposition.py::test_core_equals_proposed_and_invariants_hold` checks that the two files are byte-identical. Earlier registry edits (Nov 14) kept them identical the same way. `propose_registry` was not run.
- `docs/data/operations.md`: new `## Derived layer` before `## Rollback`.
- `docs/data/methodology.md`: new `## Derived values` before `## Dates, catch-up and recorded input`.
- `docs/superpowers/handoff/HANDOFF.md`: new top `STATUS 2026-11-15` paragraph.

## TDD evidence
- RED: `pytest tests/ingest/test_registry_derived_starter.py -q` -> 1 failed (`assert 20 <= 0`), 5 passed (vacuous on an empty list).
- GREEN: `pytest tests/ingest/test_registry_derived_starter.py tests/ingest/test_registry*.py tests/ingest/test_derived_registry.py tests/ingest/test_docgen.py -q` -> 143 passed (177 s). Docgen output does not change: `generate_sources` does not render `derived:`, and `docs/data/sources.md` still matches.

## Starter set (23 entries, all active), key = `derived.<base id without source prefix>.<formula>`
I checked every base against core.yaml myself: all 20 are active, `role: primary`, have a `redistribution_ok: true` source, frequency M or A, and `decimal: "."`. Nothing was dropped or swapped.

| Base | Freq | Base unit | Formula(s) | Derived unit |
|---|---|---|---|---|
| ine.ipi_seasonal_cae_TOT.PT | M | index_2021=100 | yoy_change_pct, period_change_pct | % |
| ine.ipi_seasonal_cae_B/C/D/E.PT | M | index_2021=100 | yoy_change_pct | % |
| ine.exports_monthly.PT, ine.imports_monthly.PT | M | EUR | yoy_change_pct | % |
| bportugal.credit_housing / credit_consumer / deposits_households .PT | M | MEUR | yoy_change_pct | % |
| eurostat.metals.PT, eurostat.chemicals_pharma.PT | M | I21 | yoy_change_pct | % |
| ine.population / live_births / deaths .PT | A | N.º | yoy_change_pct | % |
| eurostat.gdp_per_capita_eur.PT | A | EUR per capita | yoy_change_pct | % |
| ine.unemployment_monthly.PT, bportugal.pt_10y.PT | M | % | period_change, yoy_change | p.p. |
| eurostat.cci.PT | M | balance | period_change | balance |
| eurostat.unit_labour_cost_hour.PT | A | I10_2010 | rebase_100, base_period "2015" | index 2015=100 |

Labels are Portuguese, written as "<name> — <reading>", e.g. "Taxa de desemprego — variação homóloga (p.p.)".

## Local smoke (synthetic DB only; no live DB, no ssh, no containers)
Script: `/tmp/claude-1000/-home-joao/0cf85576-cadd-4c92-a5b2-4aac697971e6/scratchpad/seed_smoke.py`. It runs `open_db(<scratch>/smoke.sqlite3)` and `sync_registry` with the real core.yaml specs, then uses the repo helper `tests.ingest.derived_helpers.verified_values` to write a verified vintage for three bases:
- `ine.ipi_seasonal_cae_TOT.PT`: 2024-01..2025-12
- `ine.unemployment_monthly.PT`: 2025-01..2026-01
- `eurostat.unit_labour_cost_hour.PT`: 2010..2024

All three use fetched_at 2026-11-14T09:00Z.
- `python -m ingest --db <scratch>/smoke.sqlite3 --raw-dir <scratch>/raw derive` -> `derive run 1: verified; 23 series, 63 new values, 0 skipped, 0 mismatches` (exit 0). Running it again on the first seeding gave `0 new values` (idempotent).
- `... status` -> `derived: 23 active series; 63 served values; stale 0 / never computed 0; last run 1 (verified, 2026-11-15T01:49:17Z); failed runs 7d 0`.
- `served_derived`: 63 rows, sum(is_calculated) = 63.
- Spot checks by hand:
  - IPI 2025-12: yoy 2.6757 % (115.12 / 112.12) and period 0.8851 % (115.12 / 114.11).
  - Unemployment: 2025-12 period 0.1 p.p.; 2026-01 period 0.2 p.p. and yoy 0.3 p.p.
  - ULC rebase: 2015 = 100.0000, 2016 = 101.0471.
- The first seeding used fetched_at 2026-11-15T09:00Z, which is later than wall-clock now. Status then showed `stale 5` with a `DERIVED STALE` list. That was a test artifact: base fetched_at was later than the run start. It was not a defect.

## Docs: what was recorded
- operations.md covers:
  - what is computed and the CLI commands inside `prumo-ingest`, with output lines
  - the scheduler trigger (log-only)
  - how withdrawal and revision propagate through the view
  - the four 0014 event kinds: zero_denominator, missing_base_period, mismatch, compute_error
  - the status v4 line and stale/never-computed rules
  - the `/derived` pages
  - known limitations: one poison base value fails the whole run (`derive --series` in the CLI, no workaround in the scheduler); the skip compares input ids, not code, so a formula fix needs a new key, and formula/base/params are immutable; pct sign / sign-crossing rule; 0014 must never be edited after deploy (tracked by name, not checksum; it was edited in place before deploy)
  - deploy order: worker first, then backoffice, with a short 503 window; the old worker image has no derived code
  - the `chmod -R a+rX /data/raw` note
  - post-deploy checks
- methodology.md: formula/scale table, periods and frequencies, input eligibility, no interpolation, Decimal context and canonical text, the pct sign rule and p.p. reading, independent Fraction recomputation of 100% of values, provenance and immutability, serving rule, licence/attribution, and the visual-cue contract (`is_calculated`, `formula_label_pt`, `inputs`).
- HANDOFF.md: built and reviewed, NOT deployed; owner authorization required, not before 2026-11-15 10:25 UTC; deploy order; open owner decisions (which series first, scores/AI commentary as 3b, p.p. vs %).

## Verification
- ruff: `.venv-ci/bin/ruff check ingest backoffice tests` -> All checks passed.
- Full suite: `.venv-ci/bin/python -m pytest tests -q -m "not live"` -> 1927 passed, 7 deselected, 3 warnings in 673 s (exit 0).

## Concerns
- `eurostat.unit_labour_cost_hour.PT` rebase to 2015: the 2015 base period is expected in Eurostat nama_10_lp_ulc, but I could only check it in the synthetic DB. If 2015 is not served in production, the result is a `missing_base_period` event and no rows, not an error.
- All current derived keys are PT-only. CCI uses `period_change` in unit `balance` (a difference of balances); I did not add `yoy_change` for it.
- Did not use the GitNexus impact/detect_changes MCP tools from CLAUDE.md. They are not available in this session, and no code symbol was edited (only YAML, docs and a new test).
- Commit trailers follow the coordinator's latest instruction (`Co-Authored-By: Claude <noreply@anthropic.com>`), not the brief's "Claude Sonnet 5.5" line.
