#!/usr/bin/env python3
"""Idempotent, audited initialization of the reserved CMS homepage.

This script never migrates and never overwrites authored content. On a fresh database it
creates the complete private home draft from the current homepage content. With --publish it
then publishes that draft as a second audited step. An existing draft is refused because it
may hold operator edits; an already published home is reported and left untouched.

Usage:
  PRUMO_DB_PATH=/data/prumo.sqlite3 PRUMO_EDITORIAL_DB=/data-w/prumo.sqlite3 \
    python scripts/init_home_content.py --actor deploy-operator \
      --prepare-note "inicializar a pagina inicial completa"

  Add --publish --publish-note "publicar a pagina inicial inicializada" only when the
  authorized deployment includes the first publication.
"""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backoffice.cms import Cms, CmsConflict, CmsRefused, CmsUnavailable  # noqa: E402


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Create the complete CMS homepage draft, optionally publishing it once.")
    parser.add_argument("--db", default=os.environ.get("PRUMO_DB_PATH", ""),
                        help="read database (default: PRUMO_DB_PATH)")
    parser.add_argument("--editorial-db", default=os.environ.get("PRUMO_EDITORIAL_DB", ""),
                        help="writable database (default: PRUMO_EDITORIAL_DB, then --db)")
    parser.add_argument("--actor", required=True, help="audit actor for both steps")
    parser.add_argument("--prepare-note", default="inicializar a pagina inicial completa",
                        help="audit reason for the draft creation")
    parser.add_argument("--publish", action="store_true",
                        help="publish the newly created draft as a second audited step")
    parser.add_argument("--publish-note", default="",
                        help="audit reason for publication; required with --publish")
    args = parser.parse_args(argv)
    if not args.db:
        parser.error("--db or PRUMO_DB_PATH is required")
    if args.publish and not args.publish_note.strip():
        parser.error("--publish-note is required with --publish")
    return args


def main(argv=None) -> int:
    args = parse_args(argv)
    cms = Cms(Path(args.db), Path(args.editorial_db or args.db))
    try:
        result = cms.initialize_home(
            actor=args.actor, prepare_note=args.prepare_note,
            publish=args.publish, publish_note=args.publish_note)
    except (CmsConflict, CmsRefused, CmsUnavailable) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
