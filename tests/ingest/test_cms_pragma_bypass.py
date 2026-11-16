"""B1 regression: the restricted writer cannot rewrite integrity settings.

Before this guard the restricted authorizer allowed any PRAGMA except an assignment to
`recursive_triggers`, so the backoffice handle could turn off the FKs
(`foreign_keys=OFF`), the CHECKs (`ignore_check_constraints=ON`), the append-only trigger
firing (`recursive_triggers=OFF`), or rewrite the schema text (`writable_schema=ON`,
`trusted_schema=OFF`). The handle must keep bare reads and read-only metadata functions,
and refuse every pragma assignment however it is spelled.
"""

import sqlite3

import pytest

from ingest import cms
from ingest.db import open_db, open_db_for_write

# The pragma value an attacker would want, per pragma.
ATTACK_VALUE = {
    "foreign_keys": "OFF",
    "ignore_check_constraints": "ON",
    "recursive_triggers": "OFF",
    "writable_schema": "ON",
    "trusted_schema": "OFF",
}

INTEGRITY_READS = tuple(ATTACK_VALUE)


def _spellings(name, value):
    """The same assignment as the parser sees it, spelled every supported way."""
    return (
        f"PRAGMA {name}={value}",
        f"PRAGMA {name.upper()}={value}",
        f'PRAGMA "{name}"={value}',
        f"PRAGMA main.{name}={value}",
        f'PRAGMA main."{name.upper()}"={value}',
        f"PRAGMA {name}({value})",
        f"PRAGMA main.{name}({value})",
    )


CASES = [(statement, name)
         for name in INTEGRITY_READS
         for statement in _spellings(name, ATTACK_VALUE[name])]


@pytest.fixture
def restricted(tmp_path):
    path = tmp_path / "prumo.db"
    open_db(path).close()
    db = open_db_for_write(path)
    try:
        yield db
    finally:
        db.close()


def _integrity(conn):
    return {p: conn.execute(f"PRAGMA {p}").fetchone()[0] for p in INTEGRITY_READS}


def _cms_snapshot(conn):
    return {
        "cms_document": conn.execute(
            "SELECT * FROM cms_document ORDER BY kind, slug").fetchall(),
        "cms_revision": conn.execute(
            "SELECT * FROM cms_revision ORDER BY id").fetchall(),
        "cms_event": conn.execute(
            "SELECT * FROM cms_event ORDER BY id").fetchall(),
    }


def _page(title):
    return cms.canonical_for("page", {
        "title": title,
        "introduction": "",
        "section": "economy",
        "blocks": [],
    })


@pytest.mark.parametrize("statement,pragma", CASES,
                         ids=[s for s, _ in CASES])
def test_every_spelling_of_an_integrity_pragma_is_refused(restricted, statement, pragma):
    before = _integrity(restricted.conn)
    with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
        restricted.conn.execute(statement)
    assert _integrity(restricted.conn) == before
    # And the refused value specifically did not leak through.
    assert restricted.conn.execute(f"PRAGMA {pragma}").fetchone()[0] == before[pragma]


def test_integrity_violations_stay_refused_after_the_pragma_attempts(restricted):
    conn = restricted.conn
    restricted.cms_create("page", "inicio", _page("Inicio"), actor="owner", note="criar")
    restricted.cms_create("page", "outra", _page("Outra"), actor="owner", note="criar")
    other_revision = conn.execute(
        "SELECT draft_revision_id FROM cms_document WHERE kind = 'page' AND slug = 'outra'"
    ).fetchone()[0]

    for statement, _ in CASES:
        with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
            conn.execute(statement)
    assert _integrity(conn) == {p: conn.execute(f"PRAGMA {p}").fetchone()[0]
                                for p in INTEGRITY_READS}
    assert conn.execute("PRAGMA foreign_keys").fetchone() == (1,)
    assert conn.execute("PRAGMA recursive_triggers").fetchone() == (1,)

    before = _cms_snapshot(conn)
    stamp = "2026-11-16T00:00:00+00:00"
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        conn.execute(
            "INSERT INTO cms_document(kind, slug, version, created_at, updated_at) "
            "VALUES ('boguskind', 'x', 1, ?, ?)", (stamp, stamp))
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        conn.execute(
            "INSERT INTO cms_revision(kind, slug, body_json, created_at, actor) "
            "VALUES ('page', 'fantasma', '{}', ?, 'intruder')", (stamp,))
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        conn.execute(
            "UPDATE cms_document SET draft_revision_id = ? "
            "WHERE kind = 'page' AND slug = 'inicio'", (other_revision,))
    assert _cms_snapshot(conn) == before

    # The handle still does its actual job after all the refusals.
    saved = restricted.cms_save("page", "inicio", 1, _page("Segunda"), actor="owner",
                                note="guardar")
    assert saved["version"] == 2


@pytest.mark.parametrize("statement", [
    "INSERT INTO schema_migration(version) VALUES ('9999_intruder')",
    "CREATE TABLE evil(x)",
    "DROP TABLE cms_document",
    "CREATE TRIGGER evil AFTER INSERT ON cms_event BEGIN SELECT 1; END",
], ids=["source-insert", "create-table", "drop-table", "create-trigger"])
def test_writes_outside_the_authored_tables_stay_refused(restricted, statement):
    with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
        restricted.conn.execute(statement)


def test_reads_and_metadata_functions_still_work(restricted):
    conn = restricted.conn
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert conn.execute("PRAGMA foreign_keys").fetchone() == (1,)
    assert conn.execute("PRAGMA recursive_triggers").fetchone() == (1,)
    columns = {r[1] for r in conn.execute("PRAGMA table_info(cms_document)")}
    assert "draft_revision_id" in columns
    assert conn.execute("PRAGMA index_list(cms_document)").fetchall() != []
    assert conn.execute("PRAGMA database_list").fetchall()
