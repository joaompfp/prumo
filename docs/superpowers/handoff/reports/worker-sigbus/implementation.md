# Worker SIGBUS: read-only SQLite sidecar hardening

Date: 2026-11-21. One implementation slice, corrected after review. No production host
was contacted, no deploy or restart was performed, and no worker image was built.

This change does not establish or claim the historical cause of the worker's SIGBUS
exits. It removes reader-side paths that can truncate or create WAL sidecars and turns
on Python fault diagnostics for any future native fault.

## Change

### ingest/db.py

- Canonical path: `open_db_readonly` and `read_db_readonly` call
  `Path(path).expanduser().resolve()` once. Every `-wal` test, `-shm` test, file stamp,
  refusal and sqlite URI uses that canonical path. A symlink can no longer make the
  reader check `link.db-wal` while SQLite opens the target, which previously produced a
  stale immutable read while a writer was live.
- Every open, immutable or not, now uses `mode=ro&readonly_shm=1`. The flag no longer
  depends on whether `-shm` exists at check time, so a sidecar created between the check
  and the open cannot reach a writable shared-memory handle.
- A non-immutable open with no `-shm` is refused before connecting, even in a writable
  directory and even when a `-wal` exists. SQLite would create sidecars and recover the
  shared memory in that case, which the reader must never do. There is no fallback to
  `immutable=1`: a `-wal` without its `-shm` is left for the writer to recover. An
  explicit `immutable=False` on a quiet database is refused for the same reason; no
  reader creates sidecars.
- `read_db_readonly` is bounded to two attempts. It re-evaluates `immutable` on each new
  open and validates both `-wal` existence and the main file `(mtime_ns, size)` stamp
  after every immutable read, whether the read returned or raised
  `sqlite3.DatabaseError`. An immutable read error is retried only when that writer
  evidence exists; otherwise the original error propagates. If both attempts race,
  `ReadOnlyOpenError` reports that the database changed during the read and that nothing
  was returned. A non-immutable read is one transaction and is never retried.
- `open_db_readonly` retries an immutable schema error with a non-immutable open only
  when the same writer evidence appeared; without it, the original refusal is raised.
- No reader-side recovery exists now: a missing or unusable `-shm` fails closed.

The SQLite file effect this guards is: with plain `mode=ro` and a writable data
directory, SQLite opens `-shm` read/write. When the shared-memory lock looks free (no
live writer, a stale WAL index left by a dead process), it truncates the file to its 3
byte header before recovering it. A process that already mapped that shm then faults
with SIGBUS on its next access. `readonly_shm=1` makes the reader open the sidecar
read-only, so it cannot truncate or rewrite it.

### deploy/prumo-ingest.yml (unchanged from the first pass)

- Added `PYTHONFAULTHANDLER: "1"` to the worker environment. A native fault has no
  Python traceback; this prints the Python stack to stderr on the next one. No scheduler,
  parser, migration, registry or data behavior changes.

### tests/test_docker_contract.py (unchanged from the first pass)

- The worker environment contract includes `PYTHONFAULTHANDLER: "1"`.
- `test_worker_keeps_python_faulthandler_on_for_native_crashes` guards that setting.

### tests/ingest/test_readonly_shm.py

- `test_stale_wal_and_shm_are_read_without_touching_sidecars`: copies a database with
  committed WAL rows and its `-wal`/`-shm` while the writer is open, then closes the
  writer. The copy has valid sidecars and no process holding their locks. A read through
  `read_db_readonly` must return the committed rows and leave the database, `-wal` and
  `-shm` byte-identical (size, `mtime_ns` and sha256). This is the deterministic
  regression for the truncation path; it never relies on a fatal signal.
- `test_quiet_database_read_uses_immutable_and_creates_no_sidecars`: a quiet database is
  read through an immutable handle and no `-wal`/`-shm` appears.
- `test_separate_reader_sees_latest_commit_in_one_snapshot_and_cannot_write`: a real
  writer process holds the SQLite locks while a separate reader process opens
  `open_db_readonly`. The reader sees the latest committed WAL row, keeps its first count
  while the writer commits another row mid-transaction, sees the new row in a later
  handle, and its INSERT is refused.
- `test_open_db_readonly_accepts_a_quiet_database_with_the_readonly_shm_flag`: the
  immutable path accepts the flag.

### tests/ingest/test_readonly_consistency.py

New and updated regressions for the corrected contract:

- A `-wal` without `-shm` in a writable directory is refused by `open_db_readonly` and
  `read_db_readonly`, and the directory tree is unchanged afterwards.
- An explicit `immutable=False` read of a quiet database creates no sidecars; refusal is
  accepted.
- A symlink to a database with a live writer returns the committed WAL rows and opens
  non-immutable, proving the `-wal` was found through the canonical target.
- A symlink read detects a writer that starts and exits during the first immutable read:
  `seen == [True, True]`, the fresh immutable redo returns the committed row and the
  target directory is unchanged.
- An immutable read error with no writer evidence propagates without a retry. An
  immutable read error with `-wal` evidence is retried and succeeds.
- Two writer races in a row raise `ReadOnlyOpenError` with the changed-during-read
  message.
- An immutable schema error with no evidence is not retried; with a live writer it is
  retried once with a non-immutable open.
- The writer-started and writer-started-and-exited immutable redo tests now assert the
  fresh immutable evaluation where no writer remains, and that the redo writes nothing.

### tests/ingest/test_task24_verification_status.py

- The M6 test that demanded a plain retry after an immutable read error without writer
  evidence was replaced. The test now asserts the original `sqlite3.DatabaseError`
  propagates and the read function runs once.

## Baseline before the fix

The new and updated regressions were run against the unfixed `ingest/db.py` first:

```text
$ .venv-ci/bin/python -m pytest tests/ingest/test_readonly_shm.py \
    tests/ingest/test_readonly_consistency.py \
    tests/ingest/test_task24_verification_status.py -q
9 failed, 22 passed
```

Failures recorded:

```text
test_immutable_read_error_without_writer_evidence_is_not_retried
test_writer_that_writes_and_exits_during_an_immutable_read_forces_a_redo
test_two_writer_races_fail_closed_with_a_changed_during_read_error
test_wal_without_shm_is_refused_without_writing_even_in_a_writable_directory
test_explicit_plain_read_of_a_quiet_database_creates_no_sidecars
test_symlink_with_a_live_writer_reads_the_committed_wal_rows
test_symlink_detects_a_writer_that_starts_and_exits_during_the_read
test_immutable_schema_error_without_writer_evidence_is_not_retried
test_read_only_report_does_not_retry_an_immutable_error_without_writer_evidence
```

The failures included `[True, False]` where the corrected contract requires
`[True, True]`, a stale count of 0 through a symlink with a live writer, a missing-shm
open that succeeded and created sidecars, and retries after an immutable error without
any writer evidence.

## Verification after the fix

```text
$ .venv-ci/bin/python -m pytest tests/ingest/test_readonly_shm.py \
    tests/ingest/test_readonly_consistency.py tests/ingest/test_status_readonly.py \
    tests/ingest/test_task24_verification_status.py tests/test_docker_contract.py -q
69 passed

$ .venv-ci/bin/python -m ruff check ingest/db.py \
    tests/ingest/test_readonly_shm.py tests/ingest/test_readonly_consistency.py \
    tests/ingest/test_status_readonly.py tests/ingest/test_task24_verification_status.py \
    tests/test_docker_contract.py
All checks passed!
```

The stale WAL plus shm copy still returns its committed rows with all three files
byte-identical before and after.

## Remaining caveat

The audit reproduced the shm truncation and SIGBUS with a deliberately dropped writer
lock; the event that dropped the real worker's lock is still not proven. This slice makes
every reader unable to truncate or rewrite an existing `-shm`, refuses to create one,
and fails closed if a writer races the read twice. It does not prove or claim that the
historical production crashes came from this path, and it has not been deployed.

A writer that dies leaving `-wal` without `-shm` leaves read-only reports failing closed
with the diagnostic naming the missing sidecar until a writer recovers it. That is the
intended behavior: a report never recovers or creates the sidecar.

## Files

- `ingest/db.py`
- `deploy/prumo-ingest.yml`
- `tests/test_docker_contract.py`
- `tests/ingest/test_readonly_shm.py`
- `tests/ingest/test_readonly_consistency.py`
- `tests/ingest/test_task24_verification_status.py`
- `docs/superpowers/handoff/reports/worker-sigbus/implementation.md` (this report)
