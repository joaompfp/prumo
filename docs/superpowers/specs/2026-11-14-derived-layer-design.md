# Prumo — Derived layer (project 3) — Design

Date: 2026-11-14 · Status: written by the planner from the owner's instruction "Avança" (owner opted out of the question round; every choice is the planner's call unless marked **[owner]**).

## 1. Intent and why

The base pipeline serves only numbers a publisher published, each independently verified. Readers also want numbers nobody publishes directly: year-on-year change, change since last period, an index rebased to 100. These must carry the same trust: reproducible from verified inputs, never invented, and **visibly marked as calculated** **[owner: "basta mostrar que é calculado através de alguma dica visual"]**.

## 2. Goals

- G1. Compute a small, closed set of derived series from `served_observation` only (verified, licence-gated), deterministically, with exact decimal arithmetic.
- G2. Every derived value records its formula, parameters and the exact input observation ids it used, so anyone can recompute it by hand.
- G3. An independent recomputation check (second implementation, different arithmetic) covers 100% of derived values every run (pure computation, so no sampling needed).
- G4. A `served_derived` view for the future UI, exposing `is_calculated = 1`, a human formula label ("Variação homóloga, calculada pelo Prumo a partir de …"), input provenance and the strictest licence/attribution of the inputs.
- G5. Derived series are declared in the registry (git), not in code; adding one is a YAML change.
- G6. Backoffice shows each derived series with formula, inputs and recomputation status.

## 3. Non-goals and anti-goals

Non-goals (v1): AI commentary; composite "scores"/rankings (judgement, weights); cross-series arithmetic (spreads, ratios between two series); smoothing/seasonal adjustment/forecasts; the UI (project 4).
Anti-goals — failure even if it works: a derived value served from an unverified, withheld, or inactive input; a derived value that silently changes when an input is revised without a trace; interpolated or imputed inputs; a calculated number that is indistinguishable from a published one; float arithmetic.

## 4. Planner's calls

1. **Formulas (closed set, v1):** `period_change` (value_t − value_{t−1}), `period_change_pct`, `yoy_change` (value_t − value_{same period previous year}), `yoy_change_pct`, `rebase_100` (value_t / value_base × 100, base period param). "Previous period" and "same period last year" are defined by the series frequency from the period label (M, Q, A; D/other frequencies refused in v1). A missing input period yields **no** derived value (no interpolation).
2. **Arithmetic:** `decimal.Decimal` with a fixed context; result quantized to a per-formula scale recorded with the row (pct: 4 decimals; absolute change: max(input decimals); index: 4). Rounding ROUND_HALF_EVEN. Zero denominator → no row, plus an event with reason `zero_denominator`. Stored as text like base values (never float).
3. **Storage:** migration 0014: `derived_series(id, key, formula, base_series_id, params_json, label, unit, active)` seeded from registry `derived:`; `derived_observation(id, derived_series_id, period, value_text, scale, input_obs_ids_json, computed_at, run_id, state)`; `derived_run` mirrors `dataset_run` states (`computing`, `verified`, `failed`, `withdrawn`). SQL only in `ingest/db.py`.
4. **Recompute trigger:** after a base run verifies, derived series whose base series changed are recomputed (a CLI `python -m ingest derive [--series KEY]` plus the scheduler calling it after verified runs; the worker is not restarted for this plan's deploy until the owner picks a time). A revision of an input produces a new derived row version; old versions stay (history, like vintages).
5. **Verification:** `ingest/derive_verify.py` recomputes every derived value from the stored input observation ids with `fractions.Fraction`, compares exactly to the stored decimal after the same quantization; any mismatch fails the derived run and nothing from that run is served (same rule as base data). Inputs are re-read by id and must still be eligible in `served_observation` (verified run, licence ok, series active); otherwise the derived row is not served.
6. **Licence/attribution:** a derived row inherits the strictest input terms; served only when every input is redistributable. Attribution text: input attribution + "Calculado pelo Prumo".
7. **Visual cue contract for project 4:** the view exposes `is_calculated`, `formula_label_pt`, `inputs` (series keys + periods). The UI must badge any `is_calculated` value; this plan ships the data contract and the backoffice badge only.
8. **Registry scope for v1:** a starter set only, chosen by the builder from active, redistributable, monthly/quarterly/annual series with a clear citizen reading (e.g. HICP index → YoY %, industrial production index → YoY %, Euribor/prices where meaningful, unemployment as pp change). Aim for a few dozen derived series, not all 1,344; the machinery must scale to all.
9. **Deployment:** same method as backoffice: tests + adversarial review first; **ask the owner before deploy**; the 24 h worker observation (until 2026-11-15 10:25 UTC) means no worker restart before then — migration 0014 ships with the next planned worker deploy.

## 5. Parts (build order)

1. Registry schema for `derived:` + loader validation (formula whitelist, base series exists/active, frequency supports formula).
2. Migration 0014 + db.py read/write functions + `served_derived` view (+ tests incl. withdrawn/inactive/licence cases).
3. `ingest/derive.py` (pure Decimal formulas + run orchestration) and `ingest/derive_verify.py` (Fraction recomputation) + CLI `derive`.
4. Scheduler hook (after verified base run) and `status` integration (derived counts, stale derived).
5. Backoffice: derived series list/detail pages with formula, inputs, recomputation result, "calculado" badge.
6. Starter registry entries + docs (`docs/data/operations.md`, handoff).

## 6. Constraints

All standing rulings hold: numbers as text/Decimal never float, SQL only in db.py, nothing invented, test-first, subagent-driven with adversarial review, no Telegram/push, protected AGENTS.md/CLAUDE.md untouched, never raw docker run/compose.

## 7. Left to the builder

Exact period arithmetic helpers, quantization table, the starter series list, label wording (Portuguese), pagination, performance of recompute (incremental by changed periods is allowed if it stays exactly equal to a full recompute — a test must prove that).

## 8. Open questions for the owner (non-blocking)

Which derived series matter most to publish first? Should "scores"/rankings and AI commentary be project 3b, after the UI exists? Is pp change (not %) the right reading for rate series like unemployment?
