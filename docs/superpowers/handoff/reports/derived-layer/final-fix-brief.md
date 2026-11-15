# Final-review fix brief — derived layer v1

Worktree: /home/joao/projects/prumo-pipeline (branch `pipeline-rebuild`, HEAD fcf2490). The final whole-branch
review found no wrong number but three Important issues and some minors. The full report (with the reviewer's
experiments and numbers) is `.superpowers/sdd/2026-11-14-derived-layer-v1/final-review-report.md` — read sections
"Issues" and "Recommendations" first. The reviewer's experiment scripts and scratch DBs may still be under
`/tmp/claude-1000/-home-joao/0cf85576-cadd-4c92-a5b2-4aac697971e6/scratchpad/final-review/` — reuse them for the
I3 measurements if present (never copy them into the repo).

Fix exactly the items below. Test-first for every behaviour change. Rulings are the controller's and are binding.

## I1 — a redefined derived key must not stop the worker
- `ingest/scheduler.py` (the `sync_derived(db, derived)` call in `_locked_main`, ~line 297): a `ValueError` from
  `sync_derived` (existing key whose formula/base/params changed) must be caught: write ONE `derive` error log
  record (same logging mechanism the derive hook already uses), keep going with base refresh; derive continues to
  use the definitions already stored in the DB. Scheduler state and exit code are unaffected.
- `ingest/cli.py::_cmd_derive` (~line 567): catch the same `ValueError`: print the message on one line to stderr,
  exit 2, no traceback.
- Tests: (1) `scheduler.main(["--once", ...])` against a DB that already holds a derived key whose registry
  definition changed: base refresh still runs (runner called), exit code as without the slip, one derive error
  record logged; (2) CLI `derive` exits 2 with a one-line message.
- `docs/data/operations.md` "Known limitations": one sentence.

## I2 — deploy order must include the `prumo` web container
One image builds all three containers; the runbook runs `ingest status` in `prumo`. Old code against a 0014 DB
refuses ("schema is newer than this code", exit 2). In `docs/data/operations.md` (Derived layer → deploy order,
~lines 657-664) and `docs/superpowers/handoff/HANDOFF.md` (derived paragraph): the order is
`bash -lic "dc-web-up prumo-ingest"` (migrates 0014) → `bash -lic "dc-web-up prumo"` → `bash -lic "dc-web-up prumo-backoffice"`;
say which container each post-deploy check runs in. Never raw `docker compose`/`docker run` in docs.

## I3 — derived read cost must not grow with base history (ruling: edit 0014 in place; it is NOT deployed)
Measured on production: INE and Eurostat base series gain a full new vintage nearly every day (3 in 3 days), so the
reviewer's 49-vintage scenario is ~7 weeks away. Fix on the derived side:
1. `served_derived` view (`ingest/migrations/0014_derived_layer.sql`): choose the candidate row FIRST — the newest
   (`MAX(id)`) row per (derived_series_id, period) among rows with `state='match'` of a `verified` run of an active
   derived series — and only THEN require every input id of that one row to be a currently served
   `kind='fetched'` observation of the base series. (Today it checks the inputs of every historical row, then
   takes rn=1.) This is strictly fail-closed: it can only serve a subset of what the current view serves.
   Write it so SQLite can use index `derived_observation_key (derived_series_id, period, id)` and so a predicate
   on `derived_key` reaches the scan (a window function over the whole table blocks that; prefer a correlated
   `NOT EXISTS newer candidate` / `id = (SELECT MAX(id) ...)` form). All existing view columns and their meaning
   stay exactly as they are. Keep the malformed-JSON protections the table CHECKs give.
2. Consequence to handle in `ingest/derive.py`/`Db.derived_known_inputs`: the "known inputs" skip must compare
   against that same newest candidate row per period only (not any historical row). Then, when a base vintage is
   withdrawn and serving falls back to an older vintage, the next derive writes a new row version on the older
   inputs (history keeps all three rows) and it is served. Tests: revision → new version served, old kept;
   withdrawal of the newest base vintage → nothing served for affected periods until derive runs, then served
   from the older inputs with a new row; identical re-run writes 0 rows; a failed/mismatch newer run does not
   hide an older still-valid row (candidates are only match rows of verified runs).
3. `ingest/db.py`: per-key reads (`served_derived_rows`, `derived_rows_of_series`) filter by the derived series
   inside the query (no whole-view evaluation), and `served_derived_rows` must not evaluate the view twice
   (COUNT + page) more expensively than needed; `derived_status_rows` evaluates served counts once.
4. Backoffice `/derived` list: same TTL cache as the overview (30 s status cache) instead of a live evaluation
   per request.
5. `ingest/status.py::derived_state` (review M3): a derived series whose base has served data but which has 0
   served derived values is `stale`, not `current` (the withdrawal case above must show as stale until derive runs).
6. Evidence, in the report: before/after timings at 1 and ~49 vintages for `SELECT COUNT(*) FROM served_derived`,
   `derived_status_rows`, `build_status`, one-key `served_derived_rows`, `derived_rows_of_series` (reuse the
   reviewer's scenario or rebuild it in the scratchpad). Target: per-key reads well under 1 s and
   `derived_status_rows` within ~1 s of the base-only status cost at 49 vintages. If a target is not reachable
   because the cost sits in the pre-existing base view `served_observation` (migration 0011, deployed — do NOT
   change it or any migration ≤ 0013), say so with numbers; do not paper over it.
7. A regression test that bounds cost structurally rather than by a tight wall clock: e.g. `EXPLAIN QUERY PLAN`
   of the per-key query shows no full scan of `derived_observation`/`observation`, plus a scenario with ~30
   vintages of a small base where the per-key read stays under a generous bound.
8. Docs: `docs/data/operations.md` and `docs/data/methodology.md` must describe the new rule (newest verified
   version per period, served only while all its inputs are the currently served observations; after a base
   withdrawal run `python -m ingest derive`). Review M2: add "then run `derive`" to the withdraw and manual-run
   runbook lines.

## Minors to fix
- M1 `ingest/cli.py::_cmd_derive`: catch `sqlite3.OperationalError` (e.g. database locked) → one line, exit 2. Test.
- M5 `ingest/derive_verify.py` parser: reject a comma that is not a proper thousands group (today `'1,23'` reads
  as 123). It must stay independent (no import of `decimal`, `ingest.derive`, `ingest.models`). Test; the two
  implementations must still agree on every token the Decimal path accepts.
- M9 `docs/superpowers/handoff/HANDOFF.md`: backoffice v1.1's future migration is 0015, not 0014.
- HANDOFF open owner decisions: add (a) YoY on seasonally adjusted IPI and on credit stocks differs from the
  INE/BdP headline rates and the label does not say so; (b) reader-facing text embeds technical series ids and
  mixes languages (`balance`, `index 2015=100`); (c) unit/label of an existing derived key are editable with git
  as the only record; (d) base vintage growth (CORRECTED 2026-11-15 10:45 UTC — use these numbers, not any earlier ones): INE's
  payload bytes change on every fetch, so INE stores a full new vintage per day even when every value is
  identical — measured on production: 3 INE vintages in 3 days, 12,034 rows each, 0 values and 0 flags changed
  between them. Eurostat is NOT affected (its 2026-11-15 re-fetch was byte-identical and stored nothing; its
  earlier vintages carried 150 real revisions). bportugal stored one value-identical second vintage on
  2026-11-14 and none on 2026-11-15. 12 of the 20 derived bases are INE series. Totals: 336,075 fetched rows,
  158 MB DB after 3 days. The item to decide next: value-level dedupe of vintages in the base pipeline.

## Not in scope (ruled: ship as is)
M4 (unit immutability), M6 (zero-row runs), M7/M8 (owner decisions), every ledger item the reviewer marked "ship".

## Constraints
- SQL only in `ingest/db.py` and migrations. Numbers are text/Decimal, never float. Nothing invented.
- `ingest/migrations/0014_derived_layer.sql` may be edited in place (undeployed). No other migration may change.
- Never edit or stage `AGENTS.md` / `CLAUDE.md` (pre-existing dirt in the working tree).
- `registry/core.yaml` and `registry/core.proposed.yaml` must stay byte-identical (do not touch unless needed).
- The project CLAUDE.md asks for GitNexus impact analysis before editing symbols; those MCP tools are not
  available in this environment. Instead, before changing a function's contract, grep its callers and list them
  (the blast radius) in your report.
- Python: `.venv-ci/bin/python`; lint: `.venv-ci/bin/ruff check ingest backoffice tests`; focused tests while
  working; the FULL suite once at the end:
  `.venv-ci/bin/python -m pytest tests/ingest tests/backoffice tests/test_docker_contract.py -q` (~11 min: run it
  in the background and wait for it; test output must be clean).
- No network, no ssh, no docker, no deploy, no push. Scratch files only under
  `/tmp/claude-1000/-home-joao/0cf85576-cadd-4c92-a5b2-4aac697971e6/scratchpad/final-fix/`.
- Commits: small and coherent (e.g. one for I1, one for I3 code+tests, one for docs), `git commit ... </dev/null`,
  each message ending with:
  Co-Authored-By: Claude <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_013yKteVjdtPthwSSih1oeWB
