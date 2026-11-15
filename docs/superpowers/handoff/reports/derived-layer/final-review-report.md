# Final whole-branch review — derived layer v1 (project 3)

Range `64e25ea..fcf2490` on `pipeline-rebuild`. Read-only review; no production access, no network.
The full suite was not re-run (taken as given: 1927 passed, ruff clean on this HEAD).

The diff was too large for one pass, so the review was done in four passes by one reviewer:

1. Spec, plan and ledger (`progress.md`), to know what was promised and what was deferred.
2. Code, seam by seam: registry → `ingest/db.py` + migration 0014 → `derive.py` → `derive_verify.py` → scheduler → CLI → status → backoffice.
3. Experiments on scratch copies (all under the session scratchpad, never in the repo):
   - E1 baseline on a production-like copy (369,576 observations, one verified vintage per base series): migrate to 0014, sync, full derive, timings.
   - E2/E7/E9 history growth: 49 changed vintages simulated for the 20 base series, then timings.
   - E3 scheduler and CLI started with one existing derived key redefined in the registry.
   - E4 Decimal vs Fraction fuzz (200,000 token pairs, all five formulas) and period arithmetic over every M/Q/A period of years 2–9998.
   - E6 base-commit code (64e25ea) run against a database already migrated to 0014.
   - E8 alternative formulation of the served view, to locate the cost.
4. Docs, the 23 starter entries (checked against the base data), tests, ledger verdicts.

### Strengths

- **No wrong number found.** I looked for each of the five anti-goals and could not make the layer serve a value from an unverified, withheld, inactive, withdrawn or superseded input. The `served_derived` view (`ingest/migrations/0014_derived_layer.sql:196-222`) requires row `match` + run `verified` + active derived series + every input id currently served as a `fetched` row of the base series. Tests cover each exclusion on a real SQLite database.
- **Fail closed everywhere.** A formula error is a `compute_error` event and a failed run (`ingest/derive.py:198-205`); a mismatch fails the run; a failed run serves nothing. The whole run is one `BEGIN IMMEDIATE` transaction (`ingest/derive.py:242-262`), so a half-written run is never visible.
- **The two implementations are independent and agree.** `derive_verify.py` has its own parser, its own period arithmetic and uses `Fraction`; a static test forbids it importing the Decimal path. E4: 0 disagreements in 200,000 random pairs (signs, `+`, leading zeros, 30-digit integers, thousands separators, rounding ties), no negative zero, no exponent text, and both period implementations agree at every year boundary (`2020-01`→`2019-12`, `2020-Q1`→`2019-Q4`, `2020`→`2019`).
- **No float on the value path.** `derived_observation` stores `value_text` + `scale` only; inputs are read as text; exponent tokens are rejected by both parsers.
- **No interpolation.** Both implementations use the adjacent period label, never "previous available row"; a gap gives no row.
- **History is kept.** Triggers refuse update of value columns and refuse deletes; a revision adds a version and keeps the old one (tested).
- **Scheduler isolation is real.** A derive exception is logged and does not change the base attempt or the `--once` exit code (tested); derive runs only after a `verified` outcome.
- **Migration is additive and safe to roll back the image.** E1: 0011–0014 on the copy took 2.97 s. E6: the old writer opens a 0014 database without error; the old backoffice answers 503 with `/healthz` still 200 (no container flapping).
- **Backoffice.** No SQL outside `ingest/db.py` (boundary test extended to the derived modules), GET/HEAD only, `autoescape=True`, 404 page for an unknown key, the "calculado" badge on every value, inputs linked to the base series page.
- **Docs are candid.** `operations.md` and `HANDOFF.md` say built and reviewed, NOT deployed, and list the known limits. `methodology.md` matches the code.
- **Starter set is sound.** 23 keys over 20 bases; every base has served fetched rows; `%` formulas only on index/EUR/count bases with no zero or negative values; rate series use differences in `p.p.`.

### Issues

#### Critical (Must Fix)

None found.

#### Important (Should Fix)

**I1. A redefined derived key stops the whole worker — `ingest/scheduler.py:297` (also `ingest/cli.py:567`)**

- What: `sync_derived(db, derived)` in `_locked_main` is not guarded. `Db.upsert_derived_series` (`ingest/db.py:780-783`) raises `ValueError` when an existing key's formula, base or params change. The registry loader accepts such an edit, so CI passes.
- CONFIRMED (E3): I changed `base_period: '2015'` to `'2020'` on `derived.unit_labour_cost_hour.PT.rebase_100`. `scheduler.main(["--once", ...])` raised `ValueError: ... formula/base/params of an existing derived key cannot change; declare a new key` with 0 runner calls. `python -m ingest derive` printed a raw traceback from `db.py:782`.
- Why it matters: the worker runs with `restart: unless-stopped`, so one registry slip puts it in a restart loop and base ingestion stops for all 1,344 series. This breaks the plan's own rule that the derived layer must never affect base refresh.
- Fix: catch the `ValueError` at `scheduler.py:297`, log one `derive` error record, keep refreshing base data (derive keeps the stored definitions). In `_cmd_derive` catch it and exit 2 with the message. Add a test (see Recommendations). Add one sentence to `operations.md` "Known limitations".

**I2. Deploy order omits the `prumo` web container; the documented status check will refuse — `docs/data/operations.md:657-664`, `docs/superpowers/handoff/HANDOFF.md:5`**

- What: one Dockerfile builds all three containers. The deploy order names only `prumo-ingest` and `prumo-backoffice`. The documented status command is `docker exec prumo python -m ingest ... status` (`operations.md:255-256`, also 216, 365, 431), and "After deploy: `ingest status` shows the derived line" does not say which container.
- CONFIRMED (E6): base-commit code against a 0014 database gives `status refused: ... schema is newer than this code (unknown migrations ['0014_derived_layer'])`, exit 2.
- Why it matters: the first post-deploy check in the runbook fails, on the day of a production deploy, and looks like a broken migration.
- Fix: add `bash -lic "dc-web-up prumo"` to the deploy order (after the worker), or change the post-deploy check to `docker exec prumo-ingest`. Same edit in `HANDOFF.md`.

**I3. Read cost of everything derived grows faster than linearly with the number of base vintages — `ingest/migrations/0014_derived_layer.sql:196-222`, `ingest/db.py:917-970`**

- What: the view tests every historical `derived_observation` row, and for each input id asks `served_observation` (0011) whether it is current; that view rescans all vintages of the (series, period). No query pushes the key inside: `served_derived_rows` evaluates the whole view twice (COUNT + page), `derived_status_rows` evaluates it for every status call, `/derived` does so live on every request.
- CONFIRMED mechanism and cost (E1 vs E7/E9, same machine, 20 bases, 23 keys):

  | Measure | 1 vintage | 49 vintages |
  |---|---|---|
  | `derived_observation` rows | 6,665 | 326,585 |
  | `SELECT COUNT(*) FROM served_derived` | 0.10 s | 8.3 s |
  | `derived_status_rows` (status, overview, `/derived`) | 0.13 s | 14.9 s |
  | `build_status` | 2.0 s | 17.6 s |
  | one-key page (`served_derived_rows`) | 0.21 s | 16.7 s |
  | versions of one key (`derived_rows_of_series`) | 0.11 s | 8.4 s |
  | derive for all 20 bases after a new vintage | 0.79 s | 11.2 s (worst single base 1.3 s) |

  E8: materialising the served base ids once only moved 8.4 s to 6.8 s, and listing the served rows of the 20 bases alone took 6.4 s. So most of the cost sits in the pre-existing 0011 view, which this branch puts on the status path.
- SUSPECTED rate: a new vintage is written only when a dataset's payload bytes change (identical payloads short-circuit, `ingest/pipeline.py:83-88`). If payloads are byte-stable, monthly series reach 49 vintages in about 4 years. If they are not, in 7 weeks. INE fixture payloads carry a `DataExtracao` timestamp (`tests/ingest/fixtures/ine/monthly_exports_0001400.json`); 11 of the 20 bases are INE. I could not check production.
- Why it matters: numbers stay right, ingestion keeps running, but `ingest status`, the backoffice overview and the `/derived` pages become unusable. The derive transaction also holds the write lock longer each week.
- Fix, in order of cost:
  1. Before deploy, measure the rate on production (read-only): verified runs that hold rows, per dataset, since 2026-11-13.
  2. In this branch: filter by derived series inside the per-key queries, evaluate once instead of COUNT + page, and give `/derived` the same TTL cache as the overview.
  3. Separate task on the base layer: make "is this observation id currently served" a constant-time lookup.
  Any change to the view's shape is cheapest before deploy, while 0014 may still be edited; after deploy it needs a 0015 that drops and recreates the view (safe: views hold no data).

#### Minor (Nice to Have)

- **M1. `ingest/cli.py:541-581`** — `_cmd_derive` does not catch `sqlite3.OperationalError`. A database locked for more than 30 s gives a traceback and exit 1, the same code as a failed run. SUSPECTED (by reading; lock not exercised). Fix: catch, print one line, exit 2.
- **M2. `ingest/cli.py` (`run`, `verify`, `withdraw`)** — manual base operations do not trigger a derive. Status shows `DERIVED STALE` until the next verified scheduler attempt of that group or a manual `derive`. CONFIRMED by reading; the docs do say "scheduler, or manual". Fix: one line in the withdraw and manual-run runbooks: "then run `derive`".
- **M3. `ingest/status.py:260-270`** — after a base withdrawal back to an older vintage, the state reads `current` (older `fetched_at` < last run) even when no derived rows exist for that older vintage, so 0 values are served. Fail closed, but the label misleads. SUSPECTED (not run). Fix: treat `served_values = 0` with base data present as `stale`.
- **M4. `ingest/db.py:770-790`** — `unit` and `label` of an existing key can change through the registry with no history row; a unit edit (`p.p.` → `%`) relabels every stored value. CONFIRMED by reading. Git is the only record. Fix: make `unit` immutable like formula/base/params, or record a `derived_event`.
- **M5. `ingest/derive_verify.py:20-28`** — the verifier's parser is more lenient than `parse_decimal`: it reads `'1,23'` as 123. CONFIRMED (E4). Harmless today because compute rejects the token first and the run fails; it weakens the "independent check" claim only on paper. Fix: reject a comma that is not a thousands group.
- **M6. `ingest/scheduler.py:147-154`** — a derive runs after every verified attempt, including identical-payload short-circuits, so each group adds one "0 new values" `derived_run` row per day. CONFIRMED (E7: runs 50 and 51 wrote 0 rows and a run row each). The backoffice runs table fills with noise. Fix: skip the run row when nothing is written and nothing is skipped, or filter the table.
- **M7. `registry/core.yaml:20702-20842`** — YoY on seasonally adjusted IPI and on credit stocks will differ from the INE and BdP headline rates, and the label does not say so. CONFIRMED by inspection. A reader comparing with the publisher will think Prumo is wrong. Owner decision before any public UI.
- **M8. `ingest/derive.py:24-33`, `registry/core.yaml`** — reader-facing text embeds a technical id ("a partir de ine.ipi_seasonal_cae_TOT.PT") and mixes languages (`balance`, `index 2015=100` among Portuguese labels). CONFIRMED by inspection. Fix before public UI: use the base series label; pick one language.
- **M9. `docs/superpowers/handoff/HANDOFF.md:9`** — still says backoffice v1.1 will use "migration 0014". That number is now taken. CONFIRMED by reading. Fix: say 0015.

### Deferred minors — verdict per ledger line (ship / fix before merge / upgrade to Important)

| Ledger line | Item | Verdict |
|---|---|---|
| T1 | `derived: false/0/""` loads as `[]` | ship |
| T1 | empty key message lacks name | ship |
| T2 | `scope_json` not enforced against rows by the view | ship (rows are written only for run-scoped keys) |
| T2 | full `tests/ingest` not re-run after the fix | ship (moot: full suite passed on HEAD) |
| T3 | exponent tokens / more than 60 digits abort compute | ship (now a per-series `compute_error`, fails closed; E4 confirmed) |
| T3 | `_split` does not validate sub-period range | ship (the observation trigger already refuses bad periods) |
| T3 | `format_fixed` scale < 0 unvalidated | ship |
| T3 | rebase path has no frequency validation | ship (registry refuses other frequencies) |
| T3 | Fraction grid lacks negative denominators | ship (E4 fuzz covered signs, 0 disagreements) |
| T3 | pct on sign-crossing series not meaningful | ship (documented; starter set has none, checked on data) |
| T4 | `_check_row` maps any `ValueError` to `unparseable_input` | ship |
| T4 | implicit yoy default branch | ship |
| T4 | stored/expected types vary by reason | ship |
| T4 | no `verify_run` tests for yoy / Q / A rollovers | ship (done: `tests/ingest/test_derive_verify.py:324`, `:343`) |
| T4 | duplicate (series, period) rows in one run not detected | ship (the view serves one row per period; orchestration writes one) |
| T5 | one poison base value fails the whole run | ship (documented). Note the effect: after a new base vintage, every key of that group serves nothing until fixed |
| T5 | skip compares ids, not formula code | ship (documented) |
| T6 | `_derive` does not ROLLBACK for an injected deriver | ship |
| T6 | derive log records have a different key set | ship |
| T7 | status module docstring lacks derived section | ship |
| T7 | `derived_run.started_at` UTC unenforced | ship |
| T8 | versions heading lacks total | ship |
| T8 | `/derived` live while overview is cached | **upgrade: part of I3** (15 s per request at 49 vintages) |
| T8 | global runs table | ship (see M6) |
| T8 | no `derived_event` listing | ship now, first follow-up: today a failed run can be diagnosed only by hand SQL |
| T9 | label test does not tie `(%)`/`(p.p.)` suffix to unit | ship (23 entries checked by hand) |
| T9 | no-pct guard keyed on three unit strings | ship |
| T9 | `balance` vs `(saldo)` language mix | ship; owner call before public UI (M8) |

### Rulings — any you disagree with

- L3 (deploy deferred, owner authorization, after 2026-11-15 10:25 UTC): agree.
- L13 (Task 3 carries Task 2 contracts): agree.
- L16 (rebase at base period stores one id `[t]`): agree. The DB contract is the right authority; both implementations apply it.
- L19 (`input_count` reason; one transaction; compute error = failed run): agree. The code matches.
- L24 (0014 edited in place before deploy; never after): agree. Consequence worth stating: any view change for I3 is cheapest before deploy.
- L29 (worker first, then backoffice, short 503 window): **disagree in part — incomplete.** The 503 window and health behaviour are as ruled (E6). But the `prumo` web container carries old `ingest` code and is where the runbook runs `status`; it must be rebuilt in the same deploy (I2).

### Declined to judge

- Cost of the pre-existing `served_observation` view (0011): outside the range; named only as the root of I3.
- Whether production payloads are byte-stable between fetches: needs production or network.
- State of the production database (at 0013, 0014 never applied): relied on the ledger; no access.
- Whether `p.p.` is the right reading for rate series: open owner decision in the spec.
- Which of the 23 series to publish first: editorial, owner's call.
- Statistical appropriateness of YoY on seasonally adjusted data: noted as a labelling minor only.
- Public API or public UI for derived values: not in this range; only the view contract was checked.
- Retention or pruning of derived history: the spec requires history without deletion.
- Derived series on D / S / PT15M bases: refused by the registry by design.
- Float `value` column in the base `observation` table: pre-existing; the derived path reads `value_text` only.
- Base pipeline short-circuit and withdrawal semantics: pre-existing, used as given.
- Backoffice authentication and network exposure: project 2, unchanged.
- Full suite and ruff: not re-run, by instruction.
- `AGENTS.md` / `CLAUDE.md` working-tree dirt: outside the branch.

### Recommendations

1. Fix I1 and I2 before merge; both are small.
2. Most valuable missing test: `scheduler.main(["--once", ...])` against a database that already holds a derived key whose registry definition changed — base refresh must still run and one `derive` error record must be logged. Today it raises.
3. Second most valuable: one end-to-end test with real data — a verified `run_dataset`, then a scheduler tick, then `served_derived` has rows; a changed payload adds versions and keeps the old ones. The current real-derive scheduler test has no served inputs and writes nothing.
4. For I3, measure the vintage rate on production before deploy, and add a test that bounds view cost with about 30 vintages.
5. Tests otherwise exercise real behaviour: real SQLite, real code, `monkeypatch` only to inject faults.
6. Plan/spec issue, not an implementation one: the spec asks for full history and whole-view serving but sets no bound on read cost as history grows.

### Assessment

**Ready to merge?** With fixes

**Ready to deploy on production data?** With fixes

**Reasoning:** No path was found that serves a wrong or unverified number, and the Decimal and Fraction implementations agree on 200,000 fuzzed cases. Three things need attention first: a registry slip can stop the whole worker (I1), the deploy runbook's status check will fail as written (I2), and status and backoffice reads slow sharply as vintages accumulate (I3: measure the rate before deploy, mitigate before or soon after).
