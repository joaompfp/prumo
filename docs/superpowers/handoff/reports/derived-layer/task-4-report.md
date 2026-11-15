# Task 4 report: `ingest/derive_verify.py`

Status: DONE. Commit `70e8efa feat(derive): independent Fraction recomputation`.

## Files
- `ingest/derive_verify.py` (new)
- `tests/ingest/test_derive_verify.py` (new, 38 tests)

## What was built
- `expected_text(formula, current, reference) -> (text, scale)`: own token parser (strip; drop `,`, space, NBSP, NNBSP; fullmatch `[+-]?[0-9]+(\.[0-9]+)?` else ValueError), `Fraction` arithmetic, half-even via `round(Fraction * 10**scale)`, own fixed-point formatter (no `+`, no `-0`). Abs change scale = max input fractional digits; pct/rebase = 4. `ZeroDivisionError` propagates; unknown formula -> ValueError.
- Own period arithmetic for M/Q/A (`_shift`), reference = previous / year-ago / `params["base_period"]`.
- `VerifyOutcome(n_checked, n_mismatch, mismatches)` and `verify_run(db, run_id, at)`: re-reads inputs by id via `observations_by_ids`; checks in order: id count, existence, `kind='fetched'` and served, base series, periods, parse, zero denominator, value, scale. First defect per row is reported. Sets every row `match`/`mismatch` with one `set_derived_row_states` call and writes one `derived_event(kind='mismatch', detail=<mismatch dict>)` per mismatch.
- Canonical input-id rule (ledger ruling): `[current, reference]`; a `rebase_100` row at its own base period must hold exactly ONE id `[t]`. Both `[t, t]` (DB refuses anyway) and `[t, other]` at the base period are mismatches.
- Imports: `re`, `dataclasses`, `fractions`, `typing`; `ingest.db.Db` only under `TYPE_CHECKING`. No `decimal`, `ingest.derive`, `ingest.models`, no `float(`, no SQL.

## Tests (red first: collection error, module missing)
- Independence: static AST guard on the module's imports (covers `import x`, `from x import y`, `from ingest import derive`), plus a self-test of the guard on each forbidden form; no `float(` in source.
- `expected_text` agrees with `derive.compute` for all 5 formulas over a 19-pair grid incl. Task 3 ties (`100.00005`, `100.00015`), negative-zero (`99.99999`, `5`/`5`), thousands separators, NBSP, negative denominators. Review Focus values pinned verbatim. Zero denominators raise; 11 malformed tokens refused.
- `verify_run`: all-match for period_change / period_change_pct / rebase_100 (then `finish_derived_run(verified)` succeeds); rebase base-period row holds one id; tampered value (`value`, event written, finish verified refused); wrong scale (`scale`); tampered input list (swapped -> `input_wrong_period`, dropped / extra id -> `input_count`, reference two periods back -> `input_wrong_period`); rebase base period with two ids; input revised by a newer vintage -> `input_not_served`; input of a withdrawn run -> `input_not_served`; other-series ids -> `input_wrong_series`; wrong period; zero denominator; unparseable stored token (test drops observation triggers to plant `1e3`); covers every row of the run and not another run's; empty run.

Result: `pytest tests/ingest/test_derive_verify.py tests/ingest/test_derive_formulas.py tests/ingest/test_db_derived.py -q` -> 93 passed. `ruff check ingest backoffice tests` -> clean. `tests/backoffice/test_boundaries.py` also passes.

## Concerns / deviations
1. Added reason `input_count` (not in the brief's list) for an input list of the wrong length (dropped/extra id, or two ids at a rebase base period). Mapping these onto `input_missing`/`input_wrong_period` would have been misleading; it is just a string in the event detail.
2. `stored`/`expected` in a mismatch dict: for `scale` they are the ints (stored scale, expected scale); for `value` the texts; for input/zero/unparseable reasons `stored` is the row's value_text and `expected` is `None`.
3. `verify_run` opens no transaction (Db's `transaction()` is `BEGIN IMMEDIATE`, not nestable); Task 5 should wrap verify + finish in its own transaction if it wants atomicity. Writes are batched at the end of the function.
4. An unsupported frequency or malformed row period raises `ValueError` (fail fast; the registry already refuses non-M/Q/A bases) rather than marking a mismatch.
5. Verifier's token parser is deliberately looser than `ingest.models` (drops any `,`/space without enforcing groups of 3), per the brief. Stored inputs already passed the strict parser at ingest, so this cannot make a bad row match.
6. Plan Global Constraint "extend tests/backoffice/test_boundaries.py" (no SQL in derive/derive_verify) was not done here; it is not in Task 4's file list.
