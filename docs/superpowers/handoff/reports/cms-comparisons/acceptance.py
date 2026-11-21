"""Reproduce CMS conversion proof on an isolated database; production requires explicit scope."""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

from backoffice.cms import Cms
from backoffice.comparison_import import install


def fingerprint(path: Path) -> dict:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        conn.execute("BEGIN")
        tables = {}
        for (name,) in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            digest = hashlib.sha256()
            count = 0
            for row in conn.execute(f'SELECT * FROM "{name}" ORDER BY rowid'):
                digest.update(json.dumps(row, ensure_ascii=False, default=repr).encode())
                digest.update(b"\n")
                count += 1
            tables[name] = {"rows": count, "sha256": digest.hexdigest()}
        schema = list(conn.execute("SELECT type,name,sql FROM sqlite_master ORDER BY type,name"))
        return {
            "tables": tables,
            "schema": hashlib.sha256(json.dumps(schema).encode()).hexdigest(),
            "integrity": list(conn.execute("PRAGMA quick_check")),
            "foreign_keys": list(conn.execute("PRAGMA foreign_key_check")),
            "home": list(conn.execute("SELECT * FROM cms_document WHERE kind='page' AND slug='inicio'")),
        }
    finally:
        conn.close()


def protected(snapshot: dict) -> dict:
    return {name: digest for name, digest in snapshot["tables"].items()
            if not name.startswith("cms_") and name != "sqlite_sequence"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--publish-content", action="store_true")
    parser.add_argument("--actor", default="operator:jarbas")
    args = parser.parse_args()
    before = fingerprint(args.db)
    result = ()
    repeated = ()
    if args.publish_content:
        cms = Cms(args.db, args.db)
        result = install(cms, actor=args.actor,
                         note="Conversão dos comparativos reais para autoria CMS autorizada pelo João",
                         publish=True)
        repeated = install(cms, actor=args.actor, note="Confirmar importação sem substituir conteúdo",
                           publish=True)
    after = fingerprint(args.db)
    assert before["schema"] == after["schema"]
    assert protected(before) == protected(after)
    assert before["home"] == after["home"]
    assert after["integrity"] == [("ok",)]
    assert not after["foreign_keys"]
    receipt = {"before": before, "after": after, "import": result, "repeat": repeated,
               "protected_unchanged": True, "home_unchanged": True}
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"receipt": str(args.receipt), "import": result, "repeat": repeated,
                      "protected_unchanged": True, "home_unchanged": True}))


if __name__ == "__main__":
    main()
