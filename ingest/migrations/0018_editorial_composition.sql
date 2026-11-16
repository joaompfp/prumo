-- Migration 0018 (editorial pages plan, Task 1; spec 2026-11-16-editorial-pages-design §4).
--
-- A public page may show a composition chosen in the backoffice: ordered references to
-- existing series, plus an optional derived key per slot. Nothing here stores reader text
-- or a value; a composed card is read at request time exactly like a catalogue card.
--
-- Additive only: no existing table is rebuilt, no column changes, and the pipeline's
-- `event` table is untouched (its `kind` CHECK is closed and SQLite cannot widen a CHECK
-- without rebuilding the table, which is why the editorial audit has its own table).
--
-- `position` is contiguous 0..n-1 and capped at 11: twelve is the home card grid, so a
-- composition that cannot be laid out is unrepresentable rather than refused at render.
--
-- `derived_key` carries NO foreign key on purpose: `derived_series` is a projection that
-- must stay free to deactivate a key, and a hard reference would block that for an
-- editorial convenience. It is validated in code at write and at read.
-- `series_id` DOES carry a foreign key: the pipeline never deletes a series, it deactivates it.

CREATE TABLE editorial_page(
  slug                TEXT PRIMARY KEY,
  version             INTEGER NOT NULL DEFAULT 0,
  draft_saved_at      TEXT,
  published_version   INTEGER,
  published_at        TEXT
) STRICT;

CREATE TABLE editorial_slot(
  slug        TEXT NOT NULL REFERENCES editorial_page(slug) ON DELETE CASCADE,
  state       TEXT NOT NULL CHECK (state IN ('draft','published')),
  position    INTEGER NOT NULL CHECK (position BETWEEN 0 AND 11),
  series_id   TEXT NOT NULL REFERENCES series(id),
  derived_key TEXT,
  PRIMARY KEY (slug, state, series_id),
  UNIQUE (slug, state, position)
) STRICT;

CREATE TABLE editorial_event(
  id          INTEGER PRIMARY KEY,
  ts          TEXT NOT NULL,
  slug        TEXT NOT NULL,
  action      TEXT NOT NULL CHECK (action IN
                ('slot_added','slot_moved','slot_removed','draft_discarded',
                 'published','reset_to_code')),
  version     INTEGER NOT NULL,
  note        TEXT NOT NULL,
  detail_json TEXT
) STRICT;

CREATE INDEX editorial_slot_state ON editorial_slot(state, slug, position);
