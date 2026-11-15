# Vintage dedupe and language-neutral data layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop storing value-identical vintages, flag calculated rates that are not the publisher's rate, and move all reader-facing text out of the data layer into a presentation layer.

**Architecture:** (1) a new `presentation/` package owns reader text per language; the data layer keeps codes only (migration 0016 reshapes `derived_series` and `served_derived`); caveat codes are added on top. (2) Migration 0015 adds an index; a dataset-level identical-content short-circuit generalises pipeline Ruling D inside `run_dataset`'s write transaction.

**Tech Stack:** Python 3.12, SQLite (STRICT, WAL), pydantic, FastAPI + Jinja2 (backoffice), pytest, ruff.

**Spec:** `docs/superpowers/specs/2026-11-15-vintage-dedupe-and-language-neutral-data-design.md`

## Global Constraints

- Migrations 0001–0014 are deployed: never edit. New: `0015_observation_run_index.sql`, `0016_language_neutral_derived.sql`.
- SQL only in `ingest/db.py` and migrations. Numbers are publisher text / Decimal, never float.
- `registry/core.yaml` stays byte-identical to `registry/core.proposed.yaml`.
- No new `event.kind`; no deletion of existing observations; no INE regrouping.
- Do not edit `AGENTS.md` / `CLAUDE.md`. Backoffice stays read-only, non-root.
- Refactor to the principle first, then change behaviour (task order below).
- No GitNexus MCP: grep callers and report the blast radius of every changed symbol in the task report.
- Commit trailers: `Co-Authored-By: Claude <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_013yKteVjdtPthwSSih1oeWB`; use `</dev/null` with `git commit`.
- Test commands: `.venv-ci/bin/python -m pytest <paths> -q`; `.venv-ci/bin/ruff check ingest backoffice presentation tests`. The full suite takes ~11 min: run it only in Task 6.

## Review Focus

- A (series, period) that appears twice in one run (two responses) must compare as a multiset, not a set.
- A previous run in any non-verified state (failed-verification, withdrawn, blocked-stale, pending) must never serve as a base: full processing.
- Identical values but different quarantine rows (or the reverse) must NOT short-circuit.
- A value that reverts (A, then B, then A again) is not "identical to an older run": only the base of the unbroken chain counts, so the third run is stored.
- After `withdraw_run` of the base, the next identical fetch is stored in full (cascade makes the shortcut runs withdrawn).
- Recorded input whose bundle is stale still ends `blocked-stale`, never `verified` by content.
- A missing catalog key (formula, unit, caveat, derived key) raises; it never renders a raw code silently.
- Migration 0016 on a database that already holds the 23 derived series and their observations keeps every derived observation and event.

---

### Task 1: Presentation package (additive)

**Files:**
- Create: `presentation/__init__.py`, `presentation/catalog/__init__.py`, `presentation/catalog/pt.py`, `presentation/catalog/en.py`
- Test: `tests/presentation/test_catalog.py`

**Interfaces:**
- Produces (all raise `KeyError` subclass `MissingText` on a missing code, `ValueError` for unknown language):
  - `describe_formula(lang: str, formula: str, params: dict[str, str], base_series_id: str) -> str`
  - `unit_text(lang: str, code: str) -> str`
  - `caveat_text(lang: str, code: str) -> str`
  - `derived_title(lang: str, key: str) -> str`
  - `calculated_attribution(lang: str, attribution: str) -> str`
  - `LANGUAGES: tuple[str, ...]` = ("pt", "en")
- Consumes nothing from `ingest` at import time.

- [ ] **Step 1: Failing tests.** `test_pt_formula_text_is_verbatim` asserts `describe_formula("pt", "yoy_change_pct", {}, "ine.x") == "Variação homóloga (%), calculada pelo Prumo a partir de ine.x"` and the other four formulas equal today's `_LABELS` texts in `ingest/derive.py` (`rebase_100` takes `params["base_period"]`; missing param raises ValueError). `test_pt_attribution_suffix`: `calculated_attribution("pt", "INE") == "INE — Calculado pelo Prumo"`. `test_en_second_language` renders all five formulas and an attribution in English. `test_missing_key_raises` for each function. `test_catalog_covers_registry`: load `registry/core.yaml`'s `derived:` rows with `yaml.safe_load`; every formula, every `derived_title(lang, key)` for every key and every language exists (units and caveats are checked in Tasks 2 and 3 once the codes exist: here assert the unit/caveat whitelists of the catalog equal `{"pct","pp","balance","index_2015_100"}` and `{"sa_base","stock_base"}`).
- [ ] **Step 2: Run** `.venv-ci/bin/python -m pytest tests/presentation -q` and confirm it fails.
- [ ] **Step 3: Implement** the package. Move the five formula texts verbatim from `ingest/derive.py::_LABELS`, the 23 titles verbatim from the registry `label:` fields into `pt.py` (dict keyed by derived key), unit texts (`pct` "%", `pp` "p.p.", `balance` "saldo", `index_2015_100` "índice 2015=100"), caveat sentences (pt, see Task 3 for the exact wording constraint), and an English catalog for formulas, units, caveats and the 23 titles. Do NOT touch `ingest/` in this task.
- [ ] **Step 4: Run** the tests and `ruff check presentation tests/presentation`; expect pass.
- [ ] **Step 5: Commit** `feat(presentation): reader text catalogs per language (pt, en)`.

### Task 2: Language-neutral derived data layer

**Files:**
- Create: `ingest/migrations/0016_language_neutral_derived.sql`
- Modify: `ingest/models.py` (`DerivedSpec`), `ingest/registry.py` (`sync_derived`), `ingest/derive.py` (remove `_LABELS`, `formula_label_pt`; keep the formula check at line ~121 against `FORMULAS`), `ingest/db.py` (`upsert_derived_series`, `derived_series_rows`, `served_derived_rows` column list), `registry/core.yaml` and `registry/core.proposed.yaml` (identical edits to the `derived:` block: drop `label:`, unit → code), `backoffice/reads.py`, `backoffice/templates/derived_detail.html`, `backoffice/templates/derived_list.html`, `docs/data/methodology.md` (derived section ~lines 335–345), tests that reference `formula_label_pt`, `label` or "Calculado pelo Prumo" (`tests/backoffice/test_app_derived.py`, `tests/ingest/test_db_derived.py`, `tests/ingest/test_derived_registry.py`, `tests/ingest/test_registry_derived_starter.py`, others found by grep).
- Test: `tests/ingest/test_migration_0016.py`, plus the updated tests above.

**Interfaces:**
- Consumes: Task 1 functions.
- Produces: `DerivedSpec` without `label`; `unit: Literal["pct","pp","balance","index_2015_100"]` (export the tuple as `DERIVED_UNITS`); `served_derived` without `formula_label_pt` and `label`, `unit` = code, `attribution` = publisher attribution only; `derived_series` without `formula_label_pt` and `label`. Backoffice renders text with `lang = "pt"` (one module constant in `backoffice/deps.py`).

- [ ] **Step 1: Failing tests.** `test_migration_0016_keeps_data`: build a DB migrated to 0015, insert a derived series (old unit `'%'`), an observation and an event through the old shape, apply 0016, assert counts of `derived_observation` and `derived_event` unchanged, `unit` mapped (`'%'`→`pct`, `'p.p.'`→`pp`, `'balance'`→`balance`, `'index 2015=100'`→`index_2015_100`), `served_derived` columns contain no `formula_label_pt`/`label` and its `attribution` has no "Calculado". `test_derived_spec_rejects_unknown_unit`. `test_data_layer_has_no_portuguese_prose`: scan the column values of `derived_series` and `served_derived` after a registry sync for the 23 keys and assert no row contains any character outside ASCII (codes and keys only). Update the backoffice tests to expect the same rendered text as before via the presentation layer (title, formula sentence, "Fake publisher — Calculado pelo Prumo").
- [ ] **Step 2: Run** the new tests; confirm failure.
- [ ] **Step 3: Migration 0016.** `DROP VIEW served_derived`; remove the two reader-text columns (`ALTER TABLE derived_series DROP COLUMN ...` if SQLite allows given the foreign keys, otherwise a table rebuild preserving ids); `UPDATE derived_series SET unit = CASE unit ...`; recreate `served_derived` from the 0014 definition minus `formula_label_pt`/`label` and with `p.attribution AS attribution`. Do not touch 0014.
- [ ] **Step 4: Code.** `DerivedSpec` loses `label`, `unit` becomes the code literal; `sync_derived` and the Db functions drop the two fields; remove `_LABELS`/`formula_label_pt` from `ingest/derive.py` (callers found by grep move to `presentation`). Registry YAML: drop `label:` and map units on both files identically (`diff registry/core.yaml registry/core.proposed.yaml` must be empty). Backoffice: `reads.py` stops selecting the removed columns; templates and `reads.py` call `derived_title`, `describe_formula`, `unit_text`, `calculated_attribution`.
- [ ] **Step 3b:** report the blast radius (callers of each removed/changed symbol) in the task report.
- [ ] **Step 5: Run** `tests/ingest -k "derive or derived or registry or migration" tests/backoffice tests/presentation -q` and ruff; expect pass.
- [ ] **Step 6: Commit** `refactor(derived): data layer carries codes only; reader text moves to presentation`.

### Task 3: Calculated-rate caveats

**Files:**
- Create (only if Task 2 is already committed): `ingest/migrations/0017_derived_caveats.sql` with `ALTER TABLE derived_series ADD COLUMN caveats_json TEXT NOT NULL DEFAULT '[]'`, then drop and recreate `served_derived` exposing `caveats`. 0016 and 0017 are not deployed, so folding the column into 0016 is allowed; record the choice in the report.
- Modify: `ingest/models.py` (`DerivedSpec.caveats: list[Literal["sa_base","stock_base"]] = []`, `DERIVED_CAVEATS`), `ingest/registry.py`, `ingest/db.py`, registry YAML (both files), `presentation/catalog/{pt,en}.py` (final wording), `backoffice/templates/derived_detail.html`, `backoffice/reads.py`.
- Test: `tests/ingest/test_derived_caveats.py`, `tests/backoffice/test_app_derived.py`.

**Interfaces:**
- Produces: `served_derived.caveats` (JSON array text of codes); `derived_series_rows` includes `caveats` (list).
- Consumes: `caveat_text(lang, code)`.

- [ ] **Step 1: Failing tests.** Assert the exact key→caveat mapping from the spec: six keys carry `["sa_base"]` (the five IPI `yoy_change_pct` keys TOT/B/C/D/E and `derived.ipi_seasonal_cae_TOT.PT.period_change_pct`) and three carry `["stock_base"]` (credit_housing, credit_consumer, deposits_households yoy); all other derived keys carry `[]`. Unknown caveat code rejected by `DerivedSpec`. Backoffice detail page for a caveated series shows `caveat_text("pt","sa_base")` next to the calculated cue; for an uncaveated series shows no caveat block. Wording test: the pt and en sentences contain "Prumo" and the words for "not the publisher's official rate" (pt: "não é a taxa oficial do editor") and do not contain any claim about the publisher's method ("o INE calcula", "o Banco de Portugal calcula").
- [ ] **Step 2: Run** and confirm failure. **Step 3: Implement** (migration, model, sync, Db, YAML edits on both files, catalogs, template). **Step 4: Run** `tests/ingest -k derived tests/backoffice tests/presentation -q` + ruff. **Step 5: Commit** `feat(derived): caveat codes for rates that differ from the publisher's headline`.

### Task 4: Index and per-run content reads

**Files:**
- Create: `ingest/migrations/0015_observation_run_index.sql` (`CREATE INDEX observation_run ON observation(dataset_run_id, series_id);`). Numbering note: if Task 2 already created 0016, renumber so the index migration sorts before the reshaping one is NOT required; migrations apply in filename order: keep 0015 index, 0016 reshaping, 0017 only if needed.
- Modify: `ingest/db.py` (new `content_base_run`, `run_content`; `RunContent` dataclass), docstring of `_run_has_observations` unchanged.
- Test: `tests/ingest/test_db_content.py`, `tests/ingest/test_migration_0015.py`.

**Interfaces:**
- Produces: `Db.content_base_run(key: str, before_run_id: int) -> int | None`; `Db.run_content(run_id: int) -> RunContent` where `RunContent` is a frozen dataclass of two tuples: `observations: tuple[tuple[int, str, str, str | None, str | None], ...]` = `(series_id, period, value_text, status_flag, released_at)` sorted, `quarantine: tuple[tuple[int, str, str, str], ...]` = `(series_id, raw_period, raw_value, reason)` sorted. Two runs compare equal iff both tuples are equal (multiset semantics through sorting).

- [ ] **Step 1: Failing tests.** Chain cases for `content_base_run`: (a) previous verified run with observations is the base; (b) skips verified runs with no observations and returns the earlier writer; (c) returns None when the first run met with observations is not verified (parametrise over failed-verification, withdrawn, blocked-stale, pending-verification, failed-fetch); (d) returns None when the previous run is non-verified even if an older verified writer exists; (e) None for the first run of a key; (f) a verified run with no observations and no quarantine and no earlier writer gives None. `run_content`: duplicate (series, period) rows from two responses both kept; ordering independent of insertion order; `released_at` included. Migration test: after 0015 `EXPLAIN QUERY PLAN SELECT 1 FROM observation WHERE dataset_run_id = ?` uses `observation_run`.
- [ ] **Step 2: Run**; confirm failure. **Step 3: Implement.** **Step 4: Run** `tests/ingest/test_db_content.py tests/ingest/test_migration_0015.py tests/ingest -k "migration or db_" -q` + ruff. **Step 5: Commit** `feat(db): observation_run index and per-run content reads`.

### Task 5: Identical-content short-circuit

**Files:**
- Modify: `ingest/pipeline.py` (`run_dataset` and a new private `_same_content_as_base(db, key, run_id, raws, checked) -> bool`; keep `_same_as_previous_verified`), docstring at the top of `run_dataset` (Ruling D now "identical bytes, or identical values").
- Test: `tests/ingest/test_pipeline_content_shortcut.py`

**Interfaces:**
- Consumes: `Db.content_base_run`, `Db.run_content`.
- Produces: `run_dataset` returns `DatasetRunResult("verified", run_id, 0, 0, detail=<text naming the base run>)` for a content-identical run; no observations, quarantine, events or verification are written for it.

- [ ] **Step 1: Failing tests** (use the existing fake sources / pipeline test helpers; reuse patterns from the current Ruling D tests): (a) two live fetches with different bytes but identical parsed values → second run `verified`, zero observation rows of its own, zero quarantine rows, no events; (b) identical values, different `released_at` → stored in full; (c) identical values, different quarantine rows → stored; identical quarantine rows too → short-circuit; (d) one changed value → stored in full as `pending-verification` and later verifiable; (e) A, B, A sequence: third run stored; (f) previous run `failed-verification` → stored; (g) after `withdraw_run` of the base the next identical fetch is stored; (h) recorded input with stale bundle → `blocked-stale`; recorded input identical → `verified` no-op; (i) duplicate (series, period) from two responses compared as a multiset; (j) `status` confirms the series current through a content short-circuit (`_shortcut_confirmations`) and staleness derives from it; (k) the existing byte-identical test file still passes untouched.
- [ ] **Step 2: Run** `tests/ingest/test_pipeline_content_shortcut.py`; confirm failure.
- [ ] **Step 3: Implement** inside the write transaction after `_guard_recorded_not_stale` and before `_write`: build the run's would-be rows from `checked` (observations with their raw tuple values, `released_at`, rejections as quarantine tuples) in the same shape as `RunContent`, compare with `db.run_content(base)`, and if equal call `_leave_running(db, run_id, "verified", ts())` and return. A `None` base never short-circuits.
- [ ] **Step 4: Wording.** "identical-payload" → "identical bytes or identical values" in `ingest/verify.py` (lines ~133, 416, 434), `ingest/cli.py` (19, 477), `ingest/db.py` (411–412, 633–662), `ingest/bundle.py` (498–499), `docs/data/operations.md` (395–396, 422–430, 703: the pending value-dedupe note becomes a statement of what shipped), `docs/data/methodology.md` (154–155, 249–255, 378, 395–402). Add the consequences from the spec (no independent re-verification on unchanged days; INE stores a complete vintage when any value changes; existing duplicates are kept).
- [ ] **Step 5: Run** `.venv-ci/bin/python -m pytest tests/ingest -k "pipeline or verify or status or withdraw or scheduler or bundle" -q` + ruff. **Step 6: Commit** `feat(pipeline): identical-content short-circuit generalises Ruling D`.

### Task 6: Handoff, full suite and production-copy dry run

**Files:**
- Modify: `docs/superpowers/handoff/HANDOFF.md` (STATUS block, decisions 1–3 shipped or pending deploy, migration numbers 0015/0016(/0017), backoffice v1.1 migration renumbered to the next free number), `docs/data/operations.md` (deploy note for 0015/0016).

- [ ] **Step 1:** full run in the background: `.venv-ci/bin/python -m pytest tests/ingest tests/backoffice tests/presentation tests/test_docker_contract.py tests/test_manual_runbook.py -q`; ruff clean. Expect all pass (previous baseline 1897 passed, 7 deselected, plus the new tests).
- [ ] **Step 2:** copy of the production DB (`/tmp/claude-1000/-home-joao/0cf85576-cadd-4c92-a5b2-4aac697971e6/scratchpad/deploy-0014/copy.sqlite3`, already at 0014): run `python -m ingest status` migration to 0015/0016 on a copy, record migration time, DB size, derived rows unchanged (23 series, 6,665 served values) and the timings of `perf.py` before/after.
- [ ] **Step 3:** update HANDOFF and commit `docs(handoff): vintage dedupe, caveats and language-neutral data layer ready to deploy`. Do not deploy: ask Joao first.
