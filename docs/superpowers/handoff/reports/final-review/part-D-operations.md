# Final review, part D: operations, documentation and repo hygiene

Reviewer: Claude (read-only). Branch `pipeline-rebuild` @ `6b938fd`, base `legacy-ui-final` (`a18a58a`).
Live checks on f0nix were read-only: `docker ps`/`logs`/`inspect`, and a read-only `sqlite3 ... mode=ro`
`serialize()` snapshot copied to the local scratchpad. `status` was run only against that local copy.
Nothing on f0nix was restarted, written or changed.

Scope: `ingest/scheduler.py`, `status.py`, `cli.py`, `operations.py`, `docgen.py`, `cadence.py`,
`__main__.py`, migrations 0009/0010, `Dockerfile`/`entrypoint.sh`/`.dockerignore`/`deploy/prumo-ingest.yml`,
live `~/docker/stacks/web/compose/prumo*.yml`, `app/`, `docs/data/*` and the tests that cover them.

## Test suite (real numbers)

- `.venv-ci/bin/python -m pytest tests/ingest -q`, with the default `-m "not live"` from
  `pytest.ini`: **1397 passed, 7 deselected (live), 2 warnings, 0 failed** in 651.92s on
  Python 3.12.3 and pytest 9.2.0. The wall time is inflated because 3 other review sessions
  were running the suite at the same time.
- The remaining top-level tests (`tests/` without `tests/ingest`, covering the Docker contract,
  maintenance app, manual runbook and Task 17 cleanup): **74 passed, 1 warning**.
- Note: there is no `python` on PATH in this checkout's shell, and `requirements.txt` pins
  `pytest<8` while CI uses 9.2.0 (see M7).

## Strengths

- **Scheduler crash safety works, and the live logs show it.** `scheduler_attempt_started`
  (`ingest/db.py:309-322`) commits a pessimistic `running` state with `failure_streak+1` before
  any network call. Only `verified` resets the streak (`db.py:324-334`). `_ready`
  (`scheduler.py:81-89`) anchors the backoff on `last_finished_at`, or on `last_attempt_at` when
  the process died mid-run. A crash loop under `restart: unless-stopped` therefore cannot hammer
  publishers: a killed group waits at least 1h. Live evidence: 17 World Bank groups had
  `failed-fetch` at 01:39-01:47 and retried about 1h later (02:47-02:52). Three of them then had
  `failed-verification` (streak 2) and retried exactly 4h later (06:52), all `verified`. All 18
  rows in `scheduler_state` now have streak 0. `RestartCount=0`.
- **Freshness never comes from synthetic legacy runs.** The scheduler uses only its own
  `scheduler_state` table (migration 0010, which is additive and STRICT). `status` excludes
  `legacy:` keys from attempts and from verification evidence (`status.py:155-176`). Legacy-only
  series report `availability=legacy-unverified` with their original dates and `stale=True`.
- **The log contract is honest.** `tick` emits one JSON record per actual attempt and fabricates
  no success heartbeat. `--once` exits 1 on any non-verified attempt.
- **Polite clients.** There is one lazy throttled client per source, reused across groups and
  passes. Client retries are 0, so they do not multiply `run_with_refetch` attempts
  (`operations.py:44-55`).
- **FRED credential hygiene in the code path is careful.** The key goes only on the wire. A body
  that echoes the key is refused, the key is stripped from final URLs, and exceptions are
  re-raised without the URL (`ingest/sources/fred.py:371-399`). The scheduler `detail` field
  therefore cannot leak it.
- **Docs match the code and the live DB closely.** I checked 16 concrete claims and all are
  accurate (see "Docs claims verified" below). `docs/data/sources.md` is byte-identical to a fresh
  `python -m ingest docs`. `operations.md:101-105` openly documents the `PRUMO_DB`/`PRUMO_DB_PATH`
  inconsistency instead of hiding it.
- **`.dockerignore` denies by default** and lists credential patterns. The image contains only
  `app/ static/ ingest/ registry/`.
- **No Claude/Anthropic code remains in runtime code.** `app/`, `ingest/`, `deploy/`,
  `Dockerfile` and `requirements.txt` are clean (`tests/test_maintenance.py::test_no_claude_references`).
  The remaining hits are in historical docs and the legacy `static/` (see Minor).

## Issues

### Critical

**C1. A real FRED API key is committed to a PUBLIC GitHub repository and is still tracked on this branch.**
- **Where:** `/.fred_api_key` (repo root), tracked since `47d8655` (2026-03-16). It is present on
  `origin/main` and `origin/pipeline-rebuild`. `gh repo view joaompfp/prumo` reports `"visibility":"PUBLIC"`.
- **What:** The content is 32 lowercase hex characters, which is exactly the FRED key format. I
  did not print it or test it. The file is not in `.gitignore`. `progress-ledger.md:137` records
  that the team noticed it ("FRED legacy .fred_api_key presence discovered") but it was never
  removed or rotated. The new code deliberately never reads it (`fred.py:19-22`, `:360-369`).
- **Why it matters:** This is a leaked credential on a platform whose one promise is trust. It
  may be the same key that `operations.md:95` calls "the worker's only source secret". Anyone can
  use it against FRED's terms under the owner's identity, which could get the key revoked and
  silently turn the FRED source into `blocked`.
- **Fix:**
  1. Rotate the key at FRED now and update `secrets/web.enc.env` through SOPS. Rotate even if it
     differs from the production key.
  2. `git rm --cached .fred_api_key` and add `.fred_api_key` (and `*.key`, `.*_api_key`) to `.gitignore`.
  3. Optionally purge it from history with `git filter-repo` and force-push. Rotation is the real
     fix, because public history has already been cloned or scraped.
  4. Add a tracked-file secret scan, for example a test that fails if `git ls-files` matches
     `(^|/)\.[\w-]*(api_key|token|secret)`.

This is pre-existing rather than introduced by the branch. It still blocks merge as-is because
the branch re-ships it and the review scope explicitly includes committed secrets.

### Important

**I1. `status` does not show staleness in text mode, and short-circuit runs will produce false "stale" flags.**
- **Where:** `ingest/status.py:270-291` (`render_text`) and `status.py:255-259`.
- **What:**
  - The default `python -m ingest status` text output prints a staleness legend but no per-source
    or per-series stale/never-fetched counts at all. Only `--json` carries `stale`/`stale_reason`.
    The owner chose the CLI status report as the only monitoring channel, so an operator reading
    the text form cannot see staleness.
  - Staleness is computed from the max `observation.fetched_at` of verified rows. The accepted
    identical-payload short-circuit (`pipeline.py:149-150`) ends a run `verified` without writing
    observations. A monthly or daily (`M`/`D` = 1d) series whose publisher bytes have not changed
    will therefore flip to `stale=True` 24h after its last changed fetch, even though the
    scheduler re-checked it minutes ago.
  - This errs toward "stale", never "fresh", so it is not a trust breach. But it trains operators
    to ignore the flag.
  - This is not yet visible live: all 1,345 active series are `stale=False` at 20:35 UTC. It will
    show up once Banco de Portugal/INE/Eurostat re-fetch identical bytes after about 01:2x UTC on
    11-14.
- **Fix:**
  1. Add to each source line in `render_text` the counts `stale N / never_fetched N / never_verified N`,
     and list stale series ids, capped at about 10.
  2. Either base staleness on the latest verified run's `finished_at` for the dataset (a re-check
     that confirmed identical bytes is a real refresh), keeping `real_data_fetched_at` separately
     as the data's age, or document clearly that `stale` means "retained bytes older than policy"
     and add a separate `last_confirmed_current` field.

**I2. `status` is labelled read-only but it migrates, and it creates a database when the path is wrong.**
- **Where:** `ingest/cli.py:138` (help text "(read-only)") and `cli.py:351-357` →
  `open_db` (`ingest/db.py:382-391`), which sets `journal_mode=WAL` and runs `_migrate`.
- **What:**
  - I ran `python -m ingest --db <typo> status`. It silently created a 96 KB empty DB, exited 0
    and printed every source as "latest attempt -, last verified never".
  - The operator runbook runs `status` from the web container (`operations.md:229-236`). On f0nix
    the web (`prumo:latest`) and worker (`prumo-ingest:latest`) images are built and rebuilt
    independently (`dc-web-up prumo` rebuilds only the web image). A newer web image would apply
    a new migration to the live system of record underneath an older running worker, simply by
    running "read-only" status.
  - The env-var mismatch adds to this. The CLI reads `PRUMO_DB` (`cli.py:74-75`) while the image
    and scheduler use `PRUMO_DB_PATH` (`scheduler.py:211`, `Dockerfile:10`). It is only safe today
    because both defaults happen to be `/data/prumo.sqlite3`.
- **Fix:**
  1. Give `Db` an `open_db_readonly(path)` that uses `file:...?mode=ro` with `uri=True`. It should
     refuse a missing file (exit 2) and refuse a schema version different from the code's latest
     migration (exit 2, "run migrations with the writer first"). Use it for `status`.
  2. Make the CLI read `PRUMO_DB_PATH`, keeping `PRUMO_DB` as a deprecated fallback, and drop the
     workaround paragraph in `operations.md:101-105`.

### Minor

**M1. `blocked dgeg` log spam: one identical record every pass.** (`ingest/scheduler.py:140-144`;
locked in by `tests/ingest/test_scheduler.py:309-331`, "reported_each_tick")
- **Evidence:** live, 75 of the 120 worker log lines in the last 24h are this identical DGEG
  record. That is 96 a day, about 33 KB a day. It is far from the 10 MB×3 json-file cap, but it
  drowns the real attempt lines that the 24h acceptance review must read
  (`operations.md:414-416`).
- **Why it matters:** it also acts as an unofficial heartbeat, which the docs say does not exist.
- **Proposed fix:** report blocked sources once per process start instead of per pass:
  1. Move the loop at `scheduler.py:140-144` into a `_report_blocked(blocked, now, log)` helper.
  2. Call it from `main()` right after `sync_registry`, for both `--once` and `serve`.
  3. Have `tick()` emit only `attempt` records.
  4. Change the test to assert one `blocked` record per `main()` invocation and zero from a second `tick`.

  If per-pass visibility is still wanted, a state-change rule works too: emit when the blocked set
  differs from the previous pass, kept in a closure in `serve`. Do not write it to the DB `event`
  table; `status` already shows DGEG as `BLOCKED (not_verifiable, licence_withheld)` from the
  registry.

**M2. `pending_stale_after_hours` is reported as 0 instead of 24** (`ingest/status.py:120`).
`timedelta(hours=24).seconds` is 0 because the value is stored as days=1. The live JSON
`staleness_policy` shows `'pending_stale_after_hours': 0`, which misstates the policy in the typed
report. **Fix:** `int(PENDING_STALE_AFTER.total_seconds() // 3600)`, plus a one-line assertion in
`test_status.py`.

**M3. Event totals are lifetime counts with no window** (`status.py:183-186`, rendered at `:282`).
World Bank shows `{'fetch_failure': 17, 'verification_failure': 9, ...}` permanently, so an
operator cannot tell a past incident from a current one. **Fix:** also report counts since the
latest verified attempt, or for the last 24h.

**M4. `status` has no scheduler view.** Neither `status.py` nor `cli.py` reads `scheduler_state`,
so `failure_streak`, `running` in-flight markers (for example a killed attempt) and next-eligible
time are invisible. The operations review has to infer retry state from logs
(`operations.md:415`, "persisted retry state"). **Fix:** add a `scheduler` block per dataset with
`last_attempt_state`, `failure_streak` and `next_eligible_at`, computed with the same `_ready`
logic, moved into `cadence.py` or a shared helper.

**M5. Dead legacy code and AI remnants are publicly served.**
- `static/` keeps 81 tracked legacy files. They include the Haiku AI panel
  (`static/js/sections/analise.js:513`, `static/css/components/analysis.css:1,70`) and AI i18n
  strings, and they are served by `app.mount("/static", ...)` (`app/main.py:10`). For example,
  `https://cae.joao.date/static/js/sections/analise.js` returns 200. The maintenance page needs
  only `static/images/prumo/favicon.svg`.
- `app/config.py` is about 55 lines of dead legacy config: DuckDB `CAE_DB_PATH`, `site.json`
  loading, `SKILLS_DIR=/home/node/.openclaw/...`, `OUTPUT_LANGUAGES` "for model prompts".
  Only `STATIC_DIR` is used.
- `test_no_claude_references` deliberately skips `static/` and `docs/`, so it does not cover these.
- `ROADMAP.md:15,83,134`, `OPENSOURCE.md`, `docs/operations/PHASE_*` still describe Haiku and
  Anthropic as production.
- **Fix:** delete `static/` except the favicon (the legacy UI is recoverable at the tag), reduce
  `app/config.py` to `STATIC_DIR`, and mark or move the historical docs under an archive heading
  in `DOCS_MAP.md`.

**M6. Container hardening.**
- The worker and the CLI run as root: the live `prumo.sqlite3`, `raw/` and the lock file are
  owned by `root:root`, and there is no `USER` in the `Dockerfile`.
- The maintenance web container mounts the system of record `rw` (`prumo.yml` volumes), only so
  operators can `docker exec prumo python -m ingest ...`.
- **Fix:** add a non-root `USER` matching the host uid, then `chown` appdata once under a
  controlled change. Optionally run operator CLI writes in the worker image with a
  `docker compose run --rm`-style alias instead of the web container, so the web process could
  mount `/data` `:ro`.

**M7. Test dependencies ship in the production image.** `requirements.txt` includes `pytest`,
`pytest-cov` and `httpx`, and the `Dockerfile` installs all of it. Its pin `pytest>=7.4,<8` also
does not match the CI venv actually used (pytest 9.2.0). **Fix:** split into
`requirements-dev.txt` and align the pin.

**M8. `HEAD /` and `HEAD /healthz` return 405 live** (catch-all is `@app.get` only). This is
documented in `README.md`, but external uptime monitors commonly use HEAD. **Fix:**
`@app.api_route(..., methods=["GET","HEAD"])`.

**M9. About 13.7 MB of binary evidence (31 binaries) added to the git history.** Examples:
`docs/superpowers/handoff/reports/evidence/task-13-csv-language/full-recorded-run.tar.gz` (3.7 MB),
`.../task-18/checkpoint-*/worldbank-live-evidence.json.gz` (3.4 MB),
`.../task-17/eredes-live.tar.gz` (2.5 MB), 16 World Bank ZIPs, and a DGEG `.xlsx`. They are
intentional audit evidence, but they are permanent weight in a public repo, and the DGEG
spreadsheet's redistribution rights are explicitly unresolved (`registry/licences-todo.md`).
**Fix:** decide deliberately. Either keep it with a note, or move the evidence to a release
asset or out-of-repo store with hashes kept in git. Check the DGEG xlsx licence before
publishing it publicly.

**M10. Cosmetic issues in status ordering.** `datasets` are sorted by `dataset_key` hash
(`status.py:206-210`), so World Bank indicators print in a random-looking order. Sort by label.
`latest_by_key` compares ISO strings lexically (`status.py:163`); this is fine today because all
non-legacy stamps share the `+00:00` format, but it should parse with `_parse_ts` to be robust.

**M11. Uncommitted working-tree changes.** These were reported only; I did not touch them.
- `AGENTS.md`: the GitNexus symbol counts were bumped.
- `CLAUDE.md`: a second, duplicated 44-line GitNexus block was appended by tooling.

  Neither belongs in this merge. Discard them or commit them separately after removing the
  duplicate.

## Docs claims verified against code and live DB (all accurate)

1. Raw layout is `<raw-dir>/<source>/<sha256[:2]>/<sha256>` (`rawstore.py:3,23`).
2. Quarantine reasons are `bad_period/non_numeric/unit_mismatch/duplicate_period` (`validate.py:8-11`).
3. Flag precedence is `break > provisional > estimated > revised > normal` (`flags.py:25`).
4. Default sample target is 50 and there are 3 total attempts (`verify.py:252`, `operations.py:237`).
5. World Bank runs one group per indicator, other sources one group (`operations.py:85-101`).
   Live, `scheduler_state` has 18 World Bank keys.
6. Identical-fingerprint runs short-circuit to verified with no new observations (`pipeline.py:149-150,269-273`).
7. Recorded receipts more than 5 minutes in the future are refused (`receipts.py:21`).
8. The served view requires a verified run and `redistribution_ok=1`, and fetched beats legacy
   (0007/0009 view). Live: `fred/oecd/ren/dgeg = 0`.
9. The global legacy switch is off and only World Bank is scoped on. Live:
   `legacy_served=0`, `legacy_served_source:worldbank=1`.
10. Staleness defaults are A/S=30d, Q=7d, M/D/PT15M=1d (`cadence.py`).
11. Capture defaults are `--timeout 30 --max-requests 256 --deadline 300`
    (`cli.py:126-136`, `operations.py:41`). The `--to` bound is inclusive and must be before
    today UTC (`cli.py:185-198`).
12. 17 failed fetches and 9 failed verifications (`operations.md:59`). Live: `fetch_failure=17`,
    `verification_failure=9`, and the matching `dataset_run` states.
13. Checkpoint served rows (`operations.md:48-52`): Banco de Portugal 4,318, E-REDES 64,479
    (max period `2026-11-11T00:00:00+00:00`), Eurostat 45,500, INE 12,034, World Bank 45,915.
    All match the live `served_observation`.
14. World Bank has 949 matching samples over 18 passing runs. Live: `sum(sample_size)=949` over
    18 passed verifications.
15. There are 1,345 active series and none is stale. The live per-source sum is
    10+3+329+12+41+6+14+930 = 1,345, all `stale=False`.
16. The worker has a disabled healthcheck, a 10 MB×3 json-file log cap and no ports
    (`deploy/prumo-ingest.yml`, matches live). Observation start `01:21:18.73` equals the
    container's `StartedAt`.

## Declined to judge

- **Whether the leaked `.fred_api_key` equals the production `FRED_API_KEY`.** I did not decrypt
  SOPS or test the key, by design. Rotate it either way.
- **Long-term DB growth from full-history re-inserts on every non-identical fetch.** For example,
  Eurostat writes 45,500 rows per daily run when the bytes change. This belongs to parts B/C
  (storage/pipeline), and one day of data is too little to extrapolate.
- **`served_observation` query performance (NOT EXISTS self-join, no `(series_id, period)` index).**
  Out of part D scope, and there are no consumers yet behind the maintenance page.
- **The 24h acceptance outcome.** The observation window closes at 2026-11-14T01:21Z, after this review.
- **The correctness of verifier/source parsing.** Covered by parts B/C.

## Assessment

**Ready to merge: With fixes.** The operational core is sound and observably honest live. The
scheduler's pessimistic markers, backoff and legacy exclusion work exactly as designed, crash
loops cannot hammer publishers, and the docs are unusually accurate (16/16 claims checked). Merge
should wait for C1: rotate the publicly committed FRED key and untrack the file. I1 (text status
hides staleness, and short-circuit runs will create false stale flags) and I2 (the "read-only"
status migrates and auto-creates a DB, plus the env-var mismatch) should be fixed soon after, with
the M1 log-spam fix and the M2 one-liner as cheap follow-ups.
