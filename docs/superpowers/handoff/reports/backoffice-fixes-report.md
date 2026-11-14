# Backoffice v1 - review fixes report

Input: `docs/superpowers/handoff/reports/final-review/backoffice-v1-review.md`. Branch `pipeline-rebuild`.
The work is committed, not pushed and not deployed. f0nix was not touched. No `docker run`, no `docker compose`
and no image build were used.

| Commit | Fixes |
|---|---|
| `6ed1a3a` fix(backoffice): queue covers every event kind needing a human, bounded reads | Important 1, Important 2, Minor 4 |
| `3223f9d` fix(ingest): read-only reports are one snapshot and never trust a raced immutable read | Important 3, Minor 2, Minor 3 |
| `2f4cc43` fix(deploy): harden the backoffice container | Important 4 |
| `176b962` fix(backoffice): bounded item ids, report age, any-period vintages, host allow-list + CSP | Minors 1, 5, 6, 7 |
| `3b4f308` docs(operations): backoffice queue rules, hardening, boot-order bind | Minor 8 and the docs for all of the above |

| Check | Result |
|---|---|
| `pytest tests/ingest -m "not live"` | 1,574 passed, 7 deselected (518 s) |
| `pytest tests --ignore=tests/ingest` | 155 passed |
| `ruff check ingest backoffice tests` | clean |

## Important 1: queue coverage

I took the event kinds from the `add_event` call sites:
- `pipeline.py`: `fetch_failure`, `format_change`, `stale_refusal`, `operational_failure`, `revision`, `new_periods`;
- `verify.py`: `verification_failure`, `verifier_outage`, `refetch`, `verification_escalated`;
- `db.py`: `withdrawal`, `operational_failure` (orphan sweep), `series_deactivated`.

| Item | Severity | Source of truth |
|---|---|---|
| `verification_failed`, `verification_escalated` | high | event (unchanged) |
| `format_change` | high | event; this includes the per-series `no_valid_observations` event written inside a successful run |
| `stale_refusal` | high | event |
| `stuck_pending` | high | `report.sources[].pending_runs[].stale`. It no longer queries the DB, and `STUCK_PENDING_AFTER` is gone (Minor 4) |
| `operational_failure` | medium | event |
| `verifier_outage` | medium | event, only when the same run has no `verification_escalated` event in the window |
| `fetch_failure_streak` | medium | `Db.failed_fetch_streaks(2)`: the trailing consecutive `failed-fetch` runs per dataset key. A `running` run neither breaks nor extends the streak. `failed-fetch` and `fetch_failure` are 1:1 (`finish("failed-fetch", "fetch_failure")`) |
| `scheduler_streak` | medium | `report...datasets[].scheduler.failure_streak >= 2`, from the scheduler views already in the report |
| `revision_burst` | info | a run with 100 or more revisions (unchanged threshold) |
| `new_period_gap` | info | a `new_periods` event whose added periods are not contiguous (`data_lag.period_index`, made public). PT15M is not judged because its ordinal is per day. Info, not medium: a non-contiguous addition can be a legitimate backfill around held data, and the summary says so |
| `quarantine` | info | per (source, reason): rows, series, runs, latest. It is routine hygiene, so it is info |
| stale / lagging / blocked | unchanged | |

There are two thresholds, `STREAK_ALERT = 2` and `REVISION_BURST = 100`.

Not queued: `refetch`, `withdrawal` and `series_deactivated`. Each records an action already taken. The module
docstring and `operations.md` list the rules.

The two streak kinds overlap on purpose. The scheduler streak covers any non-verified scheduler outcome. The
fetch streak covers fetch failures from any origin, the manual CLI included.

## Important 2: bounded `/queue`

New `Db` read methods, all SQL in `ingest/db.py`:
- `event_counts_by_run(since, kind, min_count, limit)` counts with GROUP BY and HAVING;
- `failed_fetch_streaks`;
- `new_period_spans(since, limit)` returns n/first/last per event through `json_array_length` and `json_each`. The
  period lists are never loaded;
- `quarantine_summary(since, limit)`;
- `series_periods`, for Minor 6.

`reads.queue` reads each per-event kind separately, 200 rows per kind. It reads up to 500 `new_periods` spans, 200
burst runs and 200 quarantine aggregates. `QUEUE_EVENT_ROW_BOUND` = 1,900 event-table rows per request, down from
200,000. A read that hits its limit is named on the page (`Queue.truncated`). The old "lower bound" caveat is gone,
because revision counts are now exact.

Tests:
- `tests/backoffice/test_reads_queue.py` wraps the connection to count every row that a statement on `event`
  returns. With 3,000 revisions in one run, 250 events of each per-event kind, 550 `new_periods` and 2,000
  quarantine rows, the read stays at or below the bound, the burst shows exactly 3,000, and the truncated kinds are
  named.
- A regression test checks that 150 revisions in one run give one burst of exactly 150, and that 99 or an
  out-of-window event give none.
- The existing app test with 150 revisions still passes.

`Db.runs_in_state` has no caller left and was deleted.

## Important 3, Minors 2 and 3: `ingest/db.py` read-only flow (also `ingest status`)

- `open_db_readonly` records the main file's (mtime_ns, size) before an immutable open.
- After the read, `read_db_readonly` checks whether a `-wal` now exists or the stamp moved. Either means a writer
  raced the read, so it discards the result and redoes the read once with `mode=ro`. It does the same on
  `DatabaseError`, as before.
- Tests:
  - a writer that starts mid-read and stays open (`-wal` present);
  - a writer that writes and exits mid-read (no `-wal`, main file changed);
  - a quiet immutable read is kept, and is not redone.
- Minor 2: `_read_snapshot` wraps every read in `BEGIN`…`COMMIT`, with ROLLBACK on error. The test commits a writer
  event between two SELECTs of one read, and both SELECTs see the same count. `ingest status` and `lag` use the same
  helper.
- Minor 3: only "no such table" says "not a Prumo database". Any other error reads "cannot open the database
  read-only (sqlite3.OperationalError: ...)". When a `-wal` exists without its `-shm`, a hint is added.
  `PRAGMA query_only` now sits inside the guarded block. Tested with the review's crash case (a `-wal` with no
  `-shm` in a 0555 directory) and with a non-SQLite file.

## Important 4: `deploy/prumo-backoffice.yml`

- **Network:** its own `prumo_backoffice` network (`driver: bridge`, explicit `name`) instead of `t2_proxy`. It is
  deliberately not `internal: true`, because Docker sets up no port publishing for a container attached only to
  internal networks. A plain user-defined bridge publishes `100.118.19.6:8089:8080` like the default bridge does.
  I verified this from the compose and Docker semantics, not by running compose (house rule).
- **No DNS mount:** the `resolv.conf` mount is dropped.
  - `grep` finds no network client in `backoffice/`. A contract test pins this; `urllib.parse` is allowed,
    `urllib.request` is not.
  - The replay path is `replay_check` → `verifier.reread`, which is pure. No verifier constructor touches the
    network or the environment.
- **Filesystem and capabilities:** `read_only: true`, `tmpfs: [/tmp]`, `cap_drop: [ALL]`, and `no-new-privileges`
  as before.
  - `entrypoint.sh`'s `mkdir -p /data` is a no-op on the existing mount point.
  - Python skips writing `.pyc` files on a read-only filesystem, and Jinja has no disk cache.
- **User: kept root, and why.** `RawStore.save` writes evidence through `tempfile.mkstemp`, which creates files with
  mode **0600**, owned by root because the worker runs as root. Under uid 1000 the DB would be readable (sqlite
  files 0644 with the default umask), but every replay would fail with a PermissionError.
  - Root with `cap_drop: [ALL]` has no DAC override. It reads only files root owns, through a `:ro` mount, on a
    read-only rootfs.
  - `test_backoffice_runs_as_root_because_raw_evidence_is_owner_only` pins the reason, so changing RawStore to
    0644 will prompt a revisit.
  - The path to `user: "1000:1000"`: `chmod -R a+rX` the raw store and make RawStore write 0644. It is documented,
    not done.
- **Contract tests:** `tests/test_docker_contract.py` covers each point: own network and no `internal`, the port
  bind, the exact volumes without `resolv.conf`, `read_only` and `tmpfs`, `cap_drop` with no `cap_add` or
  `privileged`, no `user`, and no network imports.
- **Still open:** before deploy, check `exposedByDefault=false` on f0nix's Traefik. It is listed in `operations.md`.

## Minors

1. `item_id: int = Path(ge=1, le=2**63-1)` (`SQLITE_MAX_INT`). `/verification/item/99999999999999999999`,
   `2**63` and `0` now return 422. `2**63-1` returns 404.
5. `/`, `/queue` and `/series/<id>` show "status report generated <ts> (N s ago; reused for up to 30 s)" through
   the shared partial `_report_age.html`. `/queue` also keeps its own derived-at time.
6. The series page has a "Stored periods" table. It is built from `Db.series_periods`: every distinct period in
   `observation`, in any run state (withdrawn, failed, pending and legacy included, and licence-withheld sources),
   newest first, capped at 200, with the total shown. Each row has its row count, "served"/"not served", and a
   link to `?period=…#vintages`. A GET period box covers anything beyond the cap. The vintage table still labels
   each run state.
7. `TrustedHostMiddleware` reads `PRUMO_BACKOFFICE_ALLOWED_HOSTS` (comma-separated). The default is
   `100.118.19.6, localhost, 127.0.0.1`; the healthcheck uses `127.0.0.1`. An unlisted Host gets 400. Every
   response carries a Content-Security-Policy, the 400 included. This is the policy requested plus
   `frame-ancestors 'none'`, which the review suggested for clickjacking:
   `default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'`
   I also added `X-Content-Type-Options: nosniff`. The GET forms still work, because `form-action` does not fall
   back to `default-src`. Test clients now use `base_url="http://localhost"`.
8. No code change. `operations.md` explains that a failed Tailscale-IP bind at boot is not retried: Docker
   documents that a restart policy only applies after a successful start. It gives the `docker inspect` check,
   `dc-web-up` to recover, and the host-level systemd ordering fix.

## Notes and deviations

- The CLAUDE.md GitNexus impact and detect-changes steps were not run, because those MCP tools are not available in
  this session. Changed existing symbols:
  - `derive_queue` (signature: keyword aggregates; stuck runs now come from the report) and `reads.queue`, both
    backoffice-only;
  - `Queue.truncated`, now a tuple of names;
  - `read_db_readonly` and `open_db_readonly`. The callers are the backoffice, `ingest/cli.py` status/lag and tests.
    Behaviour is a superset: an extra redo and a transaction;
  - `Db.immutable_stamp` (new attribute);
  - `data_lag._index` renamed to `period_index` (only caller: `data_lag`);
  - `create_app(allowed_hosts=...)` and `SeriesDetail` (new fields).
- No migration was added. The event table has no index, and the new aggregates scan it like `build_status`'s
  `event_totals` already does.
- Not verified here: a live image run with `read_only` and `cap_drop` (it needs a container run), and the f0nix
  file modes. The post-deploy checks in `operations.md` cover both: `ls` of the data dir mid-run, `/healthz`, and
  `Host: evil.example` returning 400.
- AGENTS.md and CLAUDE.md were left untouched; their pre-existing local changes stay unstaged. The review file
  `final-review/backoffice-v1-review.md` was left untracked as I found it.
