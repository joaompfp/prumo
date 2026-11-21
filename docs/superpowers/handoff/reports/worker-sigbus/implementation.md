# Worker SIGBUS: read-only SQLite sidecar hardening

Date: 2026-11-21. One implementation slice. No production host was contacted, no
deploy or restart was performed, and no worker image was built.

This change does not establish or claim the historical cause of the worker's
SIGBUS exits. It removes a reader-side way to truncate the WAL shared memory and
turns on Python fault diagnostics for any future native fault.

## Change

### ingest/db.py

- Added `_shm(p)`, the `-shm` path helper next to `_wal(p)`, and used it in
  `_open_refusal` and `open_db_readonly`.
- `open_db_readonly` now adds `readonly_shm=1` to every open that has an existing
  `-shm` sidecar, and to every immutable open:

  ```python
  readonly_shm = immutable or _shm(p).exists()
  uri = (p.resolve().as_uri() + "?mode=ro"
         + ("&readonly_shm=1" if readonly_shm else "")
         + ("&immutable=1" if immutable else ""))
  ```

  A read-only database handle is not a read-only shared-memory handle. With plain
  `mode=ro` and a writable data directory, SQLite opens `-shm` read/write. When
  the shared-memory lock looks free, it truncates the file to its 3 byte header
  before recovering it. A process that already mapped that shm then faults with
  SIGBUS on its next access. `readonly_shm=1` makes the reader open the sidecar
  read-only, so it cannot truncate or rewrite it.

- One deliberate omission: a plain (non-immutable) open when no `-shm` exists.
  A missing file cannot hold another process's mapping, and the existing
  documented plain retry in `read_db_readonly` must be able to create the sidecar
  after a writer exits. With the flag present, that retry fails closed and leaves
  a zero-length `-wal` behind, which would keep subsequent read-only reports
  failing. This keeps the M6 retry behavior and its tests unchanged.
- `read_db_readonly`: only a control-flow cleanup (early return instead of a
  `trusted` flag). It performs the same one snapshot, the same writer-appeared
  check and the same single plain retry. No semantic change.

### deploy/prumo-ingest.yml

- Added `PYTHONFAULTHANDLER: "1"` to the worker environment. A native fault has
  no Python traceback; this prints the Python stack to stderr on the next one.
  No scheduler, parser, migration, registry or data behavior changes.

### tests/test_docker_contract.py

- The worker environment contract now includes `PYTHONFAULTHANDLER: "1"`.
- Added `test_worker_keeps_python_faulthandler_on_for_native_crashes`, a direct
  guard for that setting.

### tests/ingest/test_readonly_shm.py (new)

- `test_stale_wal_and_shm_are_read_without_touching_sidecars`: copies a database
  with committed WAL rows and its `-wal`/`-shm` while the writer is open, then
  closes the writer. The copy has valid sidecars and no process holding their
  locks. A read through `read_db_readonly` must return the committed rows and
  leave the database, `-wal` and `-shm` byte-identical (size, `mtime_ns` and
  sha256). This is the deterministic regression for the truncation path; it
  never relies on a fatal signal.
- `test_quiet_database_read_uses_immutable_and_creates_no_sidecars`: a quiet
  database is read through an immutable handle and no `-wal`/`-shm` appears.
- `test_separate_reader_sees_latest_commit_in_one_snapshot_and_cannot_write`:
  a real writer process holds the SQLite locks while a separate reader process
  opens `open_db_readonly`. The reader sees the latest committed WAL row, keeps
  its first count while the writer commits another row mid-transaction, sees the
  new row in a later handle, and its INSERT is refused.
- `test_open_db_readonly_accepts_a_quiet_database_with_the_readonly_shm_flag`:
  the immutable path accepts the flag.

## Baseline before the fix

The regression was run against the unfixed `ingest/db.py` first:

```text
$ .venv-ci/bin/python -m pytest tests/ingest/test_readonly_shm.py -q
tests/ingest/test_readonly_shm.py F...
FAILED tests/ingest/test_readonly_shm.py::test_stale_wal_and_shm_are_read_without_touching_sidecars
AssertionError: differing item:
{'p.db-shm': (32768, <mtime>, '<new hash>')} !=
{'p.db-shm': (32768, <mtime>, '<old hash>')}
1 failed, 3 passed
```

Only `p.db-shm` differed; the read itself returned the committed rows. That is
the forbidden side effect: a read-only report rewrote the shared-memory index.

## Verification after the fix

```text
$ .venv-ci/bin/python -m pytest tests/ingest/test_readonly_shm.py -q
4 passed

$ .venv-ci/bin/python -m pytest \
    tests/ingest/test_readonly_consistency.py \
    tests/ingest/test_readonly_shm.py \
    tests/ingest/test_task24_verification_status.py \
    tests/ingest/test_status.py tests/ingest/test_status_readonly.py \
    tests/ingest/test_status_derived.py tests/ingest/test_data_lag.py \
    tests/ingest/test_db_backoffice_reads.py tests/test_docker_contract.py -q
128 passed

$ .venv-ci/bin/python -m ruff check ingest/db.py \
    tests/ingest/test_readonly_shm.py tests/test_docker_contract.py
All checks passed
```

The new test file was also run three times in a row, 4 passed each time.

## Remaining caveat

The audit reproduced the shm truncation and SIGBUS with a deliberately dropped
writer lock; the event that dropped the real worker's lock is still not proven.
This slice makes every reader that sees an existing `-shm` unable to truncate or
rewrite it, and it fails closed if the sidecar cannot be read safely. It does not
prove or claim that the historical production crashes came from this path, and it
has not been deployed.

A writer that dies leaving `-wal` without `-shm` still leaves read-only reports
failing closed with the existing diagnostic hint until a writer recovers the
sidecar. That behavior is unchanged.

## Files

- `ingest/db.py`
- `deploy/prumo-ingest.yml`
- `tests/test_docker_contract.py`
- `tests/ingest/test_readonly_shm.py` (new)
- `docs/superpowers/handoff/reports/worker-sigbus/implementation.md` (this report)
