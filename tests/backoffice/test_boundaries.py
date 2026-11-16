"""Global constraint of the backoffice and derived-layer plans: SQL lives only in ingest/db.py."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKOFFICE = ROOT / "backoffice"
DERIVED = (ROOT / "ingest" / "derive.py", ROOT / "ingest" / "derive_verify.py")
SQL = re.compile(r"\b(import sqlite3|from sqlite3|SELECT\s|INSERT\s+INTO|UPDATE\s+\w+\s+SET|"
                 r"DELETE\s+FROM|\.execute\()", re.IGNORECASE)


def _offenders(files):
    return [f"{f.name}: {m.group(0)}" for f in files for m in SQL.finditer(f.read_text())]


def test_backoffice_package_contains_no_sql():
    files = sorted(BACKOFFICE.rglob("*.py"))
    assert files, "backoffice package not found"
    assert _offenders(files) == []


def test_derived_layer_modules_contain_no_sql():
    assert all(f.is_file() for f in DERIVED), DERIVED
    assert _offenders(DERIVED) == []


def test_public_app_read_layer_contains_no_sql():
    """The public app reads through `Db.public_*`; a query written in a route is a defect.
    `import sqlite3` is allowed there (app/main.py catches OperationalError at the boundary),
    statements and `.execute(` are not."""
    files = sorted((ROOT / "app").rglob("*.py"))
    assert files, "app package not found"
    statements = re.compile(r"\b(SELECT\s|INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|"
                            r"\.executescript\(|\.execute\()", re.IGNORECASE)
    assert [f"{f.name}: {m.group(0)}" for f in files for m in statements.finditer(f.read_text())] == []


def test_sql_pattern_catches_the_usual_forms(tmp_path):
    f = tmp_path / "x.py"
    for src in ("db.conn.execute('x')", "q = 'SELECT id FROM t'", "import sqlite3",
                "'INSERT INTO t VALUES (1)'", "'UPDATE derived_run SET state = 1'"):
        f.write_text(src)
        assert _offenders([f]), src
