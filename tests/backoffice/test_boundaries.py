"""Global constraint of the backoffice plan: SQL lives only in ingest/db.py."""
import re
from pathlib import Path

BACKOFFICE = Path(__file__).resolve().parents[2] / "backoffice"
SQL = re.compile(r"\b(import sqlite3|from sqlite3|SELECT\s|INSERT\s+INTO|UPDATE\s+\w+\s+SET|"
                 r"DELETE\s+FROM|\.execute\()", re.IGNORECASE)


def test_backoffice_package_contains_no_sql():
    files = sorted(BACKOFFICE.rglob("*.py"))
    assert files, "backoffice package not found"
    offenders = [f"{f.name}: {m.group(0)}" for f in files
                 for m in SQL.finditer(f.read_text())]
    assert offenders == []
