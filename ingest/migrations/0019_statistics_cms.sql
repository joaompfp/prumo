-- Migration 0019 (statistics CMS, B1): typed documents, immutable revisions and audit.
--
-- Additive only. No existing table, column, index or trigger is changed. Source and
-- observation data are untouched: a CMS body references registry series and chart slugs,
-- never values, units or source metadata.
--
-- `cms_document` is the mutable head: optimistic version, draft pointer, published pointer.
-- `cms_revision` is append-only content. The composite foreign keys make a pointer to a
-- revision of another kind/slug unrepresentable, not merely discouraged. A new document is
-- inserted with NULL pointers, its first revision follows, then the pointer is set in the
-- same transaction: that is why the two tables refer to each other.
--
-- `cms_event` is the append-only actor/reason trail. Every successful lifecycle action writes
-- exactly one event and bumps the document version in the same transaction.
--
-- The append-only and no-delete triggers below depend on `PRAGMA recursive_triggers=ON`:
-- REPLACE deletes the conflicting row before inserting, and SQLite fires DELETE triggers for
-- that internal delete only when recursive triggers are enabled. Both writable openers
-- (ingest.db.open_db and open_db_for_write) set the pragma before any write, and the
-- restricted opener's authorizer refuses turning it off; otherwise `INSERT OR REPLACE` could
-- rewrite a revision body, an audit event or the document head without firing these guards.
-- The setting is connection-local, so it is enforced in code rather than in this migration.
--
-- Rollback requires restoring the pre-0019 database copy (see the plan's migration release
-- contract); dropping these tables would discard authored history.

CREATE TABLE cms_document(
  kind                  TEXT NOT NULL CHECK (kind IN ('page','chart')),
  slug                  TEXT NOT NULL CHECK (length(slug) BETWEEN 1 AND 60),
  version               INTEGER NOT NULL DEFAULT 0 CHECK (version >= 0),
  draft_revision_id     INTEGER,
  published_revision_id INTEGER,
  created_at            TEXT NOT NULL,
  updated_at            TEXT NOT NULL,
  PRIMARY KEY (kind, slug),
  FOREIGN KEY (kind, slug, draft_revision_id)
    REFERENCES cms_revision(kind, slug, id),
  FOREIGN KEY (kind, slug, published_revision_id)
    REFERENCES cms_revision(kind, slug, id)
) STRICT;

CREATE TABLE cms_revision(
  id         INTEGER PRIMARY KEY,
  kind       TEXT NOT NULL CHECK (kind IN ('page','chart')),
  slug       TEXT NOT NULL CHECK (length(slug) BETWEEN 1 AND 60),
  body_json  TEXT NOT NULL CHECK (
               CASE WHEN json_valid(body_json)
                    THEN json_type(body_json) = 'object'
                    ELSE 0 END),
  created_at TEXT NOT NULL,
  actor      TEXT NOT NULL CHECK (length(trim(actor)) > 0),
  UNIQUE (kind, slug, id),
  FOREIGN KEY (kind, slug) REFERENCES cms_document(kind, slug)
) STRICT;

CREATE TABLE cms_event(
  id          INTEGER PRIMARY KEY,
  ts          TEXT NOT NULL,
  kind        TEXT NOT NULL CHECK (kind IN ('page','chart')),
  slug        TEXT NOT NULL CHECK (length(slug) BETWEEN 1 AND 60),
  action      TEXT NOT NULL CHECK (action IN
                ('created','saved','published','unpublished','restored','duplicated')),
  version     INTEGER NOT NULL CHECK (version >= 1),
  revision_id INTEGER NOT NULL,
  actor       TEXT NOT NULL CHECK (length(trim(actor)) > 0),
  note        TEXT NOT NULL CHECK (length(trim(note)) > 0),
  FOREIGN KEY (kind, slug) REFERENCES cms_document(kind, slug),
  FOREIGN KEY (kind, slug, revision_id) REFERENCES cms_revision(kind, slug, id)
) STRICT;

CREATE INDEX cms_event_document ON cms_event(kind, slug, id);

CREATE TRIGGER cms_document_identity_immutable
BEFORE UPDATE OF kind, slug, created_at ON cms_document
BEGIN
  SELECT RAISE(ABORT, 'cms_document kind, slug and created_at are immutable');
END;

CREATE TRIGGER cms_document_no_delete
BEFORE DELETE ON cms_document
BEGIN
  SELECT RAISE(ABORT, 'a CMS document is unpublished, never deleted');
END;

CREATE TRIGGER cms_revision_immutable_update
BEFORE UPDATE ON cms_revision
BEGIN
  SELECT RAISE(ABORT, 'cms_revision rows are append-only');
END;

CREATE TRIGGER cms_revision_immutable_delete
BEFORE DELETE ON cms_revision
BEGIN
  SELECT RAISE(ABORT, 'cms_revision rows are append-only');
END;

CREATE TRIGGER cms_event_immutable_update
BEFORE UPDATE ON cms_event
BEGIN
  SELECT RAISE(ABORT, 'cms_event rows are append-only');
END;

CREATE TRIGGER cms_event_immutable_delete
BEFORE DELETE ON cms_event
BEGIN
  SELECT RAISE(ABORT, 'cms_event rows are append-only');
END;
