-- Migration 0014 (derived layer v1, project 3, Task 2).
--
-- 1. Four new STRICT tables; no existing table, view or row changes.
--    - derived_series: the registry `derived:` list (synced by ingest.registry.sync_derived;
--      a key absent from the registry is set inactive, never deleted). A key's definition
--      (formula, base_series_id, params_json) is immutable: rows computed under it must never
--      be relabelled by a later edit, so a new definition needs a new key.
--    - derived_run: one derive invocation; scope_json = JSON list of the derived keys it
--      evaluated. States mirror dataset_run: computing -> verified | failed; verified ->
--      withdrawn. 'withdrawn' has no writer in v1 (withdrawing the BASE run already unserves
--      its derived rows through the view below); the state and its guards exist so a later
--      reviewed withdrawal command needs no table rebuild.
--    - derived_observation: one computed value (text, never float) with its scale and the
--      exact input observation ids (JSON list, formula order: [t, t-1] or [t, base]). The
--      value and provenance are immutable; state moves once, from 'pending' to the
--      independent recomputation's verdict ('match' / 'mismatch').
--    - derived_event: zero denominators, missing rebase base periods, mismatches.
-- 2. Guards (triggers): no INSERT of a withdrawn run and no INSERT OR REPLACE over a terminal
--    run (REPLACE deletes without firing UPDATE triggers, the 0013 M-2 lesson); terminal run
--    states never change except verified -> withdrawn; 'withdrawn' only from 'verified';
--    derived_observation provenance columns never change and are never REPLACEd; its state
--    changes only from 'pending'.
-- 3. View served_derived: among rows with state 'match' in a 'verified' run of an ACTIVE
--    derived series, with a non-empty input list whose EVERY input id is currently in served_observation as a 'fetched'
--    row (so: verified base run, licence ok, base series active, latest data-time vintage;
--    legacy rows never qualify), the highest id per (derived_series_id, period). A revised
--    or withdrawn input therefore unserves the derived row at once, and withdrawing a base
--    run brings back the derived row built on the vintage that is served again.
--    The input check is a correlated per-id lookup on purpose: SQLite pushes `so.id = ?`
--    into served_observation, so a page of one key costs milliseconds instead of evaluating
--    the whole served view (about 1 s per query at production size).
--    Every row carries is_calculated = 1 and the base source's licence, with attribution
--    '<source attribution> — Calculado pelo Prumo'.
--
-- A later migration that rebuilds series/source/observation/dataset_run (create-new / copy /
-- drop / rename) must DROP and recreate served_derived as well as served_observation.
CREATE TABLE derived_series(
  id INTEGER PRIMARY KEY,
  key TEXT NOT NULL UNIQUE,
  formula TEXT NOT NULL CHECK (formula IN ('period_change','period_change_pct','yoy_change',
    'yoy_change_pct','rebase_100')),
  base_series_id TEXT NOT NULL REFERENCES series(id),
  params_json TEXT NOT NULL DEFAULT '{}',
  label TEXT NOT NULL,
  formula_label_pt TEXT NOT NULL,
  unit TEXT NOT NULL,
  active INTEGER NOT NULL CHECK (active IN (0,1))
) STRICT;

CREATE TABLE derived_run(
  id INTEGER PRIMARY KEY,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  state TEXT NOT NULL CHECK (state IN ('computing','verified','failed','withdrawn')),
  trigger TEXT NOT NULL CHECK (trigger IN ('cli','scheduler')),
  scope_json TEXT NOT NULL,
  n_written INTEGER,
  n_checked INTEGER,
  n_mismatch INTEGER
) STRICT;

CREATE TABLE derived_observation(
  id INTEGER PRIMARY KEY,
  derived_series_id INTEGER NOT NULL REFERENCES derived_series(id),
  period TEXT NOT NULL,
  value_text TEXT NOT NULL CHECK (length(value_text) > 0),
  scale INTEGER NOT NULL CHECK (scale >= 0),
  input_obs_ids_json TEXT NOT NULL,
  computed_at TEXT NOT NULL,
  run_id INTEGER NOT NULL REFERENCES derived_run(id),
  state TEXT NOT NULL DEFAULT 'pending' CHECK (state IN ('pending','match','mismatch'))
) STRICT;
CREATE INDEX derived_observation_key ON derived_observation(derived_series_id, period, id);
CREATE INDEX derived_observation_run ON derived_observation(run_id, id);

CREATE TABLE derived_event(
  id INTEGER PRIMARY KEY,
  ts TEXT NOT NULL,
  run_id INTEGER NOT NULL REFERENCES derived_run(id),
  derived_series_id INTEGER REFERENCES derived_series(id),
  period TEXT,
  kind TEXT NOT NULL CHECK (kind IN ('zero_denominator','missing_base_period','mismatch')),
  detail_json TEXT
) STRICT;

CREATE TRIGGER derived_series_definition_immutable
BEFORE UPDATE OF formula, base_series_id, params_json ON derived_series
WHEN NEW.formula IS NOT OLD.formula OR NEW.base_series_id IS NOT OLD.base_series_id
  OR NEW.params_json IS NOT OLD.params_json
BEGIN
  SELECT RAISE(ABORT, 'a derived key''s definition is immutable; declare a new key');
END;

CREATE TRIGGER derived_run_withdrawn_ins BEFORE INSERT ON derived_run
WHEN NEW.state = 'withdrawn'
  OR EXISTS (SELECT 1 FROM derived_run d WHERE d.id = NEW.id
             AND d.state IN ('verified','failed','withdrawn'))
BEGIN
  SELECT RAISE(ABORT, 'a derived run is never inserted withdrawn, and a finished run is never replaced');
END;

CREATE TRIGGER derived_run_terminal BEFORE UPDATE OF state ON derived_run
WHEN NEW.state IS NOT OLD.state
  AND ((OLD.state IN ('verified','failed','withdrawn')
        AND NOT (OLD.state = 'verified' AND NEW.state = 'withdrawn'))
       OR (NEW.state = 'withdrawn' AND OLD.state <> 'verified'))
BEGIN
  SELECT RAISE(ABORT, 'derived run state is terminal (only verified -> withdrawn)');
END;

CREATE TRIGGER derived_observation_immutable
BEFORE UPDATE OF derived_series_id, period, value_text, scale, input_obs_ids_json, run_id,
  computed_at ON derived_observation
BEGIN
  SELECT RAISE(ABORT, 'a derived observation''s value and provenance are immutable');
END;

CREATE TRIGGER derived_observation_no_replace BEFORE INSERT ON derived_observation
WHEN EXISTS (SELECT 1 FROM derived_observation d WHERE d.id = NEW.id)
BEGIN
  SELECT RAISE(ABORT, 'a derived observation is never replaced');
END;

CREATE TRIGGER derived_observation_state_once BEFORE UPDATE OF state ON derived_observation
WHEN OLD.state <> 'pending'
BEGIN
  SELECT RAISE(ABORT, 'a derived observation''s state is set once, from pending');
END;

CREATE VIEW served_derived AS
WITH eligible AS (
  SELECT d.*, ROW_NUMBER() OVER (PARTITION BY d.derived_series_id, d.period
                                 ORDER BY d.id DESC) AS rn
  FROM derived_observation d
  JOIN derived_run r ON r.id = d.run_id AND r.state = 'verified'
  JOIN derived_series ds ON ds.id = d.derived_series_id AND ds.active = 1
  WHERE d.state = 'match'
    AND json_array_length(d.input_obs_ids_json) > 0
    AND NOT EXISTS (SELECT 1 FROM json_each(d.input_obs_ids_json) j
                    WHERE NOT EXISTS (SELECT 1 FROM served_observation so
                                      WHERE so.id = j.value AND so.kind = 'fetched'))
)
SELECT ds.key AS derived_key, e.period, e.value_text, e.scale, ds.unit,
  1 AS is_calculated, ds.formula, ds.formula_label_pt, ds.label, ds.base_series_id,
  (SELECT json_group_array(json_object('series_id', x.series_id, 'period', x.period,
                                       'observation_id', x.id))
   FROM (SELECT o.series_id, o.period, o.id FROM json_each(e.input_obs_ids_json) j
         JOIN observation o ON o.id = j.value ORDER BY j.key) x) AS inputs,
  p.licence, p.licence_url, p.attribution || ' — Calculado pelo Prumo' AS attribution,
  e.computed_at, e.run_id AS derived_run_id, e.id AS derived_observation_id
FROM eligible e
JOIN derived_series ds ON ds.id = e.derived_series_id
JOIN series s ON s.id = ds.base_series_id
JOIN source p ON p.id = s.source_id
WHERE e.rn = 1;
