# Prumo worker SIGBUS: investigation and safety release

## Scope and current boundary

The owner requested investigation of the autonomous ingestion-worker restarts and a bug fix if applicable. Product features, source parsers, licences, migrations and authored CMS content are outside this repair. `fe13837` implements the accepted read-path correction; release verification and installation are recorded separately below when completed. No retrospective assertion that the three SIGBUS incidents are fully explained is made.

## Confirmed live incident

The original worker container `3921475705a35df28b81a7d381e4d388918616c681607a116ac9df69ad334e4b`, image `ff50b981e4cdc7923c773fe1f017567340d64e979d6b336553045504806e53a3`, exited with code 135 (SIGBUS) at 2026-11-20 21:39:40 UTC, 2026-11-21 14:49:07 UTC and 2026-11-21 15:04:10 UTC. Docker recorded `manualRestart=false`; restart policy recovered it. These incidents predate the 15:33 reader deployment. The final incident followed 15 minutes of wall time, 2.657 seconds CPU and a 68.7 MB memory peak. `OOMKilled` is false and no corresponding kernel OOM, filesystem or I/O error was found. Current storage is local ext4, not a network filesystem.

The worker uses Python 3.12.16 and SQLite 3.46.1. The only mapped database-related file is its 32 KiB `prumo.sqlite3-shm`; main-database mmap is disabled by SQLite's build default. The DMS (dead-man-switch) shared read lock at byte 128 is currently present and the inode matches the live sidecar. Ordinary readers in separate PID namespaces see that read lock too. Lock loss during the historical incidents has not been captured.

Python fault handling was disabled. The host's Apport crash collector also failed: it looked for `/usr/local/bin/python3.12` in the host filesystem rather than the container. No usable core or native stack exists for these crashes. The repair enables Python's fatal-fault stack output; it does not change host-wide core handling.

## Reproduced reader defect and correction

`mode=ro` protects the main database but does not by itself make SQLite's shared-memory index read-only. On a copied stale WAL (write-ahead log) and shm pair in a writable directory, the original Prumo reader rewrote the shm file. A controlled signal probe also reproduced SIGBUS by deliberately releasing a mapped writer's DMS lock before a second process performed that rewrite. This proves a possible mechanism, not that the live worker lost its lock for that reason.

The accepted implementation adds `readonly_shm=1` unconditionally, resolves symlink targets before inspecting their sidecars, refuses a WAL that lacks its shm rather than recovering it, and bounds immutable-reader retries to evidenced writer races. It re-evaluates and validates every repeated immutable read; no writer means no speculative retry. Regressions prove byte-identical sidecars, fresh committed WAL values, stable read transactions, write refusal, symlinks and repeated races. Independent specification and quality gates passed after correcting an unsafe existence-based first candidate. See [implementation](implementation.md) and [reviews](reviews.md).

The actively reused release probe and online-backup helper, and the current operations snippet, also use `readonly_shm=1`. Dated raw receipts are unchanged. Other old installation scripts are historical evidence, not approved current operator commands; do not replay a historical direct SQLite connection against the live database without this flag. Do not unlink, truncate, restore or raw-copy a live database or its sidecars.

## Production preflight and recovery contract

`collect.py` captures exact container identities, safe shared-memory-read-only database fingerprints, schema, CMS/history, persisted scheduler state, integrity and worker daemon events. It does not output credentials. `receipts/pre-state.json` is the controller's collected 16:54 UTC baseline, not a child self-report. At that time the worker still had exactly three restarts and there were no running dataset runs. Integrity is ok and foreign-key violations are zero.

An exclusive-created, online SQLite recovery copy is held at `f0nix:/home/joao/prumo-operations/worker-sigbus-20261121/prumo-before.sqlite3`, 299,540,480 bytes, SHA-256 `f1e82f8aa47243622d23bfd773cdf79b55fee0a957c68c9b4dbc5282568b4f57`. It was independently opened and integrity checked after creation. It is a recovery artifact, not permission to restore it over newer production data.

Release scope: rebuild the worker, public reader and Admin because they package the shared persistence module. Install the worker's reviewed environment include. No SQL migration, CMS publication, ownership, proxy, authentication or Traefik change is required. Prebuild from a detached exact approved commit while live binds stay untouched. Stop and read back the bind-mounted public reader before advancing its checkout, then replace worker and readers using the established `dc-web` aliases. Preserve unrelated infrastructure edits. Confirm no running source attempt before a controlled worker recreation.

Pin the actual old images before rebuilding. Roll back the same code checkout (`34ed8c0`) and all affected exact image tags if safety or serving checks fail; retain the diagnostic environment where possible. Preserve the database and CMS history: this is schema-compatible and requires no restore. A source-data fingerprint mismatch after restart must be explained from actual scheduler work rather than erased by restoring a snapshot.

## Acceptance and remaining gate

Release acceptance requires exact committed imports and focused regressions, a complete passing offline suite, independent reviews, exact-main hosted CI, live read-back of images/environment, successful status and public/Admin reads, unchanged CMS/schema and explained source-data changes. Observe at least one real scheduler interval after activation. The separate 24-hour operational observation and definitive historical root cause remain open until their evidence exists. Zero restarts immediately after recreation is not proof of stability and is never compared directly with the old container's count of three.

Initial receipt collector correction: a query used `dataset_id` instead of the actual `dataset_key`; SQLite refused that read before any receipt or backup was created. The corrected collector completed and the exact backup was then read back. This was an evidence-tool error, not an application/data failure.
