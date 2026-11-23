"""Read-only readers must not write the WAL sidecars of a database.

`mode=ro` alone does not make the `-shm` file read-only: SQLite still opens it for
writing, and when the shared-memory lock looks free (no live writer, a stale WAL
index left by a dead process) it truncates the file to its 3 byte header before
recovering it. A process that already mapped that shm can then die with SIGBUS.
`readonly_shm=1` opens the sidecar read-only, so recovery can never rewrite it;
a stale index that cannot be read safely is refused instead.

The incident audit reproduced that file effect and the resulting signal on the
worker's SQLite version. The historical reason the writer's lock appeared free is
not established here, and these tests claim nothing about it. They assert the
deterministic file effect only, never the fatal signal, so the suite cannot crash
or flake.
"""

import hashlib
import queue
import subprocess
import sys
import threading
from pathlib import Path

from ingest.db import open_db, open_db_readonly, read_db_readonly

T = "2026-11-14T00:00:00+00:00"
REPO = Path(__file__).resolve().parent.parent.parent


def _tree(directory: Path) -> dict[str, tuple[int, int, str]]:
    """Name -> (size, mtime_ns, sha256) of every file in the directory."""
    out = {}
    for f in sorted(directory.iterdir()):
        st = f.stat()
        out[f.name] = (st.st_size, st.st_mtime_ns, hashlib.sha256(f.read_bytes()).hexdigest())
    return out


def _stale_wal_snapshot(source_dir: Path, copy_dir: Path) -> tuple[Path, dict]:
    """A database with committed WAL rows and its sidecars, copied while a writer is open.

    The copy has a valid `-wal`/`-shm` pair but no process holding its locks: the
    lock-free state a dead writer can leave behind. The source writer is idle after its
    last commit, so the copied bytes are a stable snapshot.
    """
    source = source_dir / "p.db"
    source_dir.mkdir()
    writer = open_db(source)
    try:
        writer.add_event(T, "revision", None, {"n": 1})
        writer.add_event(T, "revision", None, {"n": 2})
        assert Path(str(source) + "-wal").is_file()
        assert Path(str(source) + "-shm").stat().st_size >= 32768
        copy_dir.mkdir()
        for suffix in ("", "-wal", "-shm"):
            dest = copy_dir / ("p.db" + suffix)
            dest.write_bytes(Path(str(source) + suffix).read_bytes())
    finally:
        writer.close()
    return copy_dir / "p.db", _tree(copy_dir)


def test_stale_wal_and_shm_are_read_without_touching_sidecars(tmp_path):
    db_path, before = _stale_wal_snapshot(tmp_path / "source", tmp_path / "copy")
    count = read_db_readonly(
        db_path, lambda db: db.conn.execute("SELECT COUNT(*) FROM event").fetchone()[0])
    assert count == 2  # the committed WAL rows are visible
    assert _tree(db_path.parent) == before


def test_quiet_database_read_uses_immutable_and_creates_no_sidecars(tmp_path):
    db_path = tmp_path / "p.db"
    open_db(db_path).close()
    assert not Path(str(db_path) + "-wal").exists()
    seen = []

    def read(db):
        seen.append(db.immutable)
        return db.conn.execute("SELECT COUNT(*) FROM event").fetchone()[0]

    assert read_db_readonly(db_path, read) == 0
    assert seen == [True]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["p.db"]


_WRITER = """
import sys
sys.path.insert(0, sys.argv[2])
from ingest.db import open_db
db = open_db(sys.argv[1])
db.add_event("2026-11-14T00:00:00+00:00", "revision", None, {"n": 1})
print("READY", flush=True)
for line in sys.stdin:
    if line.strip() == "commit":
        db.add_event("2026-11-14T00:00:00+00:00", "revision", None, {"n": 2})
        print("COMMITTED", flush=True)
    elif line.strip() == "quit":
        break
db.close()
"""

_READER = """
import sqlite3, sys
sys.path.insert(0, sys.argv[2])
from ingest.db import open_db_readonly
db = open_db_readonly(sys.argv[1])
try:
    print(f"OPENED {db.immutable}", flush=True)
    print(f"COUNT {db.conn.execute('SELECT COUNT(*) FROM event').fetchone()[0]}", flush=True)
    db.conn.execute("BEGIN")
    print(f"BEFORE {db.conn.execute('SELECT COUNT(*) FROM event').fetchone()[0]}", flush=True)
    sys.stdin.readline()
    print(f"AFTER {db.conn.execute('SELECT COUNT(*) FROM event').fetchone()[0]}", flush=True)
    db.conn.execute("COMMIT")
    try:
        db.conn.execute("INSERT INTO event(ts, kind) VALUES (?, 'revision')",
                        ("2026-11-14T00:00:00+00:00",))
    except sqlite3.OperationalError:
        print("WRITE refused", flush=True)
    else:
        print("WRITE allowed", flush=True)
finally:
    db.close()
"""


class _Child:
    """A subprocess whose stdout lines are pumped to a queue (a pipe can be read ahead)."""

    def __init__(self, args):
        self.proc = subprocess.Popen(
            args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True)
        assert (self.proc.stdin is not None and self.proc.stdout is not None
                and self.proc.stderr is not None)
        self.stdin = self.proc.stdin
        self.stderr = self.proc.stderr
        stream = self.proc.stdout
        self.lines: queue.Queue[str | None] = queue.Queue()

        def pump():
            for line in stream:
                self.lines.put(line)
            self.lines.put(None)

        threading.Thread(target=pump, daemon=True).start()

    def line(self, timeout: float = 30.0) -> str:
        try:
            line = self.lines.get(timeout=timeout)
        except queue.Empty:
            raise AssertionError("timed out waiting for the child process") from None
        if line is None:
            raise AssertionError(f"child process exited unexpectedly: {self.stderr.read()}")
        return line.strip()

    def send(self, text: str) -> None:
        self.stdin.write(text)
        self.stdin.flush()

    def stop(self) -> None:
        if self.proc.poll() is not None:
            return
        try:
            self.send("quit\n")
        except (BrokenPipeError, OSError):
            pass
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()


def test_separate_reader_sees_latest_commit_in_one_snapshot_and_cannot_write(tmp_path):
    """Real separate processes: the writer holds the locks, the reader only reads.

    The reader sees the writer's committed WAL row, keeps its first count while the
    writer commits again in the middle of its read transaction, sees the new row in a
    later handle, and its INSERT is refused.
    """
    db_path = tmp_path / "p.db"
    writer = _Child([sys.executable, "-u", "-c", _WRITER, str(db_path), str(REPO)])
    try:
        assert writer.line() == "READY"
        reader = _Child([sys.executable, "-u", "-c", _READER, str(db_path), str(REPO)])
        try:
            assert reader.line() == "OPENED False"  # live -wal: non-immutable handle
            assert reader.line() == "COUNT 1"
            assert reader.line() == "BEFORE 1"
            writer.send("commit\n")
            assert writer.line() == "COMMITTED"
            reader.send("second\n")
            assert reader.line() == "AFTER 1"  # one snapshot, despite the commit
            assert reader.line() == "WRITE refused"
        finally:
            reader.stop()
        assert read_db_readonly(
            db_path, lambda db: db.conn.execute("SELECT COUNT(*) FROM event").fetchone()[0]) == 2
    finally:
        writer.stop()


def test_open_db_readonly_accepts_a_quiet_database_with_the_readonly_shm_flag(tmp_path):
    db_path = tmp_path / "p.db"
    open_db(db_path).close()
    db = open_db_readonly(db_path)
    try:
        assert db.immutable is True
        assert db.conn.execute("SELECT COUNT(*) FROM event").fetchone()[0] == 0
    finally:
        db.close()
