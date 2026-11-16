# Vintage dedupe, calculated-rate caveats and a language-independent data layer - design

Date: 2026-11-15. Status: planner's calls, no question round (owner opted out: "Avança"). Follows the
derived-layer v1 deploy (main 80c4c10).

## Intent

Three owner decisions of 2026-11-15, taken after the derived layer went live:

1. **Deduplicate value-identical vintages** in the base pipeline and keep the read path efficient. INE
   returns different bytes on every fetch, so it stores a complete identical vintage per day (12,034 rows).
2. **Say explicitly** when a calculated rate differs from the publisher's headline rate (YoY on seasonally
   adjusted IPI, on credit and deposit stocks).
3. **Reader-facing text leaves the data layer.** The data layer exposes language-independent codes; a
   presentation layer turns them into text, so the product can be internationalised later.

## Goals / non-goals

Goals: stop storing vintages whose values are unchanged; one place that owns reader text; the data layer
and every export of it carry no natural-language prose; a calculated rate that is not the publisher's
rate says so.

Non-goals (anti-goals): no edit of migrations 0001–0014; no deletion of existing history (about 40k of
497k observation rows are duplicate vintages: compaction is a later, owner-approved step); no regrouping of
INE into per-indicator datasets (deferred option, decide from measured vintages per month); no new event
kind; no public UI (project 4); no change to how verification samples or how withdrawals work.

## Decision 1 - identical-content short-circuit

**Measured (production copy 2026-11-15, 70 non-legacy runs):** identical content repeats for bportugal,
fred, oecd (one duplicate run each) and INE (runs 68 and 77 fully identical to run 14, including
`released_at`, plus 9 identical quarantine rows each). Quarantine rows repeat in identical runs too, so
rejections are part of the identity. eredes is already incremental; eurostat is not affected.

**Rule.** The existing byte-identical short-circuit (pipeline Ruling D) is generalised from identical
bytes to identical parsed content. A run is *content-identical* when it would write exactly the same
observation rows `(series_id, period, value_text, status_flag, released_at)` and exactly the same
quarantine rows `(series_id, raw_period, raw_value, reason)` as its **base run**, compared as sorted
multisets (a (series, period) can appear twice from two responses).

**Base run.** Walk back from the immediately previous run of the same `dataset_key`, skipping `verified`
runs that hold no observations (earlier short-circuits). The first run that holds observations is the base
and must be `verified`. Any non-verified run met on the way (failed-fetch, failed-verification, blocked,
pending, withdrawn) means no base and the run is fully processed. A run with no observations of its own
and no quarantine rows is also not a base (nothing to compare to).

**Placement.** In `run_dataset`, inside the existing write transaction, after `_guard_recorded_not_stale`
for recorded input (a stale recorded bundle stays `blocked-stale`) and before `_write`: if identical,
`_leave_running(db, run_id, "verified", ts())` and return `DatasetRunResult("verified", run_id, 0, 0,
detail=...)`. Same contract as the byte short-circuit: no observations, no quarantine, no events, no
verification of its own. So `status._shortcut_confirmations`, `Db.withdraw_run` (cascade), the
scheduler, `run_with_refetch` (returns any non-`pending-verification` result as is) and derive need no
semantic change. Derived runs skip unchanged inputs through `derived_known_inputs`, so the derived layer
simply stops writing ~6.6k rows a day.

**Consequences, to document.** No independent re-verification on unchanged days (same accepted precedent
as Ruling D). When any INE value changes, a complete INE vintage is still stored, because INE is one
dataset. Existing duplicates stay. Wording that says "identical-payload" in the CLI, runbook and
methodology becomes "identical bytes or identical values".

**Efficiency.** Migration 0015 adds `CREATE INDEX observation_run ON observation(dataset_run_id,
series_id)`. Measured on the production copy (158.7 MB, 497k rows): `observations_of_run(77)` 0.19 → 0.02 s,
`verified_run_receipts` 0.08 → 0.00 s, `series_of_runs` 0.15 → 0.06 s; build 6.6 s, DB +18 MB; the
other read-path queries are unchanged and all stay under about 2 s (`served_observation` COUNT 1.96 s is
not on a request path), so no view is rewritten. The index serves the base-content read, the chain walk,
verification sampling and the withdraw checks (`_run_has_observations` no longer scans the table).

New `Db` functions (SQL stays in `ingest/db.py`): `content_base_run(key, before_run_id) -> int | None` and
`run_content(run_id) -> RunContent` (sorted observation tuples including `released_at`, sorted
quarantine tuples).

## Decision 2 - calculated-vs-headline caveat

A derived series can carry **caveat codes**, a closed whitelist: `sa_base` (calculated on a seasonally
adjusted series) and `stock_base` (calculated on outstanding amounts / stocks). Declared per derived series
in the registry (`caveats: [..]`), stored in `derived_series.caveats_json`, exposed as `caveats` in
`served_derived`. Applied to: `derived.ipi_seasonal_cae_{TOT,B,C,D,E}.PT.yoy_change_pct`,
`derived.ipi_seasonal_cae_TOT.PT.period_change_pct` (`sa_base`); `derived.credit_housing.PT.yoy_change_pct`,
`derived.credit_consumer.PT.yoy_change_pct`, `derived.deposits_households.PT.yoy_change_pct`
(`stock_base`). The presentation layer renders a sentence saying this is Prumo's calculation on the
seasonally adjusted series / on outstanding amounts and is not the publisher's official rate; the wording
asserts nothing about the publisher's own methodology. The backoffice shows it next to the visual
"calculated" cue.

## Decision 3 - reader text in a presentation layer

*Data layer* (ingest/, SQLite, registry): codes only.
- `derived_series`: drop `formula_label_pt` and `label` (reader text); `unit` holds a unit **code**
  (`pct`, `pp`, `balance`, `index_2015_100`; closed whitelist in the model); add `caveats_json`.
- `served_derived` (dropped and recreated, as 0011 requires): no `formula_label_pt`, no `label`;
  `attribution` is the publisher's attribution only (`is_calculated` stays the data-layer fact); `unit`
  is the code; adds `caveats`.
- Registry `derived:` rows lose `label`; `unit` becomes a code. `registry/core.yaml` stays byte-identical
  to `registry/core.proposed.yaml` (regenerated by `propose_registry`).
- `ingest/derive.py`: `_LABELS` and `formula_label_pt` leave `ingest/`; the formula whitelist stays
  (`FORMULAS`).

*Presentation layer* (new top-level package `presentation/`, no import of `ingest.db`):
`describe_formula(lang, formula, params, base_series_id)`, `unit_text(lang, code)`,
`caveat_text(lang, code)`, `derived_title(lang, key)`, `calculated_attribution(lang, attribution)`;
catalogs per language (`presentation/catalog/pt.py`, plus a minimal `en.py` that proves a second
language works). A missing key raises (fail fast); a test checks that every formula, unit code, caveat
code and active derived key of the registry has an entry in every catalog. The Portuguese texts and the
23 derived titles are moved verbatim from today's `_LABELS` and registry labels. The backoffice calls
this module (language fixed to `pt` for now, one constant).

Calculated values keep only the visual cue (`is_calculated`); "- Calculado pelo Prumo" is produced by the
presentation layer.

## Constraints in force

Deployed migrations 0001–0014 are never edited: new schema work is migration 0015 (index) and 0016
(derived reshaping). Numbers are publisher text / Decimal, never float. SQL only in `ingest/db.py` and
migrations. Nothing invented or interpolated. Backoffice stays read-only and non-root. Protected
`AGENTS.md` / `CLAUDE.md` are not edited. Refactor to the principle first, then change behaviour (so the
language-neutral refactor comes before the caveats, and the index before the short-circuit).

## Left to the builder

Exact names of private helpers; whether 0016 uses `ALTER TABLE ... DROP COLUMN` or a table rebuild
(`derived_series` is referenced by `derived_observation` and by the view: drop the view first, mind the
foreign keys); where the language constant lives in the backoffice.

## Owner options deferred

Compaction of existing duplicate vintages; splitting INE per indicator (would also let annual indicators
fetch every 30 days); a public language switch (project 4).
