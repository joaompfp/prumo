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
--    - derived_event: zero denominators, missing rebase base periods, mismatches, and
--      compute errors (a formula that raised; its run is finished 'failed').
-- 2. Guards (triggers and CHECKs). A derived value reaches served_derived only through its
--    run's verification, and derived history is never rewritten or removed:
--    - a run is inserted only as 'computing', never over an existing id (REPLACE deletes
--      without firing UPDATE/DELETE triggers, the 0013 M-2 lesson); terminal run states never
--      change except verified -> withdrawn; 'withdrawn' only from 'verified'; 'verified' only
--      when every row of the run is 'match' (Task 5 sets each verdict BEFORE finishing);
--    - a row is inserted only as 'pending', only into a 'computing' run, never over an
--      existing id; its value/provenance columns never change; its state changes once, from
--      'pending', and only while its run is 'computing';
--    - input_obs_ids_json is a non-empty JSON array of DISTINCT integer ids of existing
--      observations (a rebase at its own base period stores one id, not [t, t]);
--      scope_json is a JSON array;
--    - no DELETE on any derived table and no REPLACE of a derived_series row. 0011-0013 do not
--      guard deletes of observation/dataset_run either, but nothing there deletes them; here
--      the guard is cheap and makes "history is kept" a property of the schema.
-- 3. View served_derived: among rows with state 'match' in a 'verified' run of an ACTIVE
--    derived series whose EVERY input id is currently in served_observation as a 'fetched'
--    row OF THE DERIVED SERIES' BASE SERIES (so: verified base run, licence ok, base series
--    active, latest data-time vintage; legacy rows and other series never qualify, and the
--    licence/attribution shown are the inputs' own), the highest id per
--    (derived_series_id, period). A revised or withdrawn input therefore unserves the derived
--    row at once, and withdrawing a base run brings back the derived row built on the vintage
--    that is served again.
--    The input check is a correlated per-id lookup on purpose: SQLite pushes `so.id = ?` into
--    served_observation instead of evaluating the whole served view per query. Measured on a
--    synthetic 270k-observation / 12k-derived-row database: one key's page 0.44 s (2.4 s with
--    an uncorrelated `IN (SELECT id FROM served_observation)`); the remaining cost is the
--    latest-version window over every eligible row.
--    `inputs` element order is NOT guaranteed by SQLite before 3.44 (no aggregate ORDER BY);
--    `input_ids` is the stored array in formula order, and Db.served_derived_rows returns
--    `inputs` in that order. Every row carries is_calculated = 1 and the base source's
--    licence, with attribution '<source attribution> — Calculado pelo Prumo'.
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
  scope_json TEXT NOT NULL
    CHECK (CASE WHEN json_valid(scope_json) THEN json_type(scope_json) = 'array' ELSE 0 END),
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
  input_obs_ids_json TEXT NOT NULL
    CHECK (CASE WHEN json_valid(input_obs_ids_json)
           THEN json_type(input_obs_ids_json) = 'array'
                AND json_array_length(input_obs_ids_json) > 0 ELSE 0 END),
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
  kind TEXT NOT NULL CHECK (kind IN ('zero_denominator','missing_base_period','mismatch',
                                'compute_error')),
  detail_json TEXT
) STRICT;

CREATE TRIGGER derived_series_definition_immutable
BEFORE UPDATE OF formula, base_series_id, params_json ON derived_series
WHEN NEW.formula IS NOT OLD.formula OR NEW.base_series_id IS NOT OLD.base_series_id
  OR NEW.params_json IS NOT OLD.params_json
BEGIN
  SELECT RAISE(ABORT, 'a derived key''s definition is immutable; declare a new key');
END;

CREATE TRIGGER derived_series_no_replace BEFORE INSERT ON derived_series
WHEN EXISTS (SELECT 1 FROM derived_series d WHERE d.key = NEW.key OR d.id = NEW.id)
BEGIN
  SELECT RAISE(ABORT, 'a derived series is updated in place, never replaced');
END;

CREATE TRIGGER derived_run_withdrawn_ins BEFORE INSERT ON derived_run
WHEN NEW.state <> 'computing'
  OR EXISTS (SELECT 1 FROM derived_run d WHERE d.id = NEW.id)
BEGIN
  SELECT RAISE(ABORT, 'a derived run is inserted computing, and never replaced');
END;

CREATE TRIGGER derived_run_terminal BEFORE UPDATE OF state ON derived_run
WHEN NEW.state IS NOT OLD.state
  AND ((OLD.state IN ('verified','failed','withdrawn')
        AND NOT (OLD.state = 'verified' AND NEW.state = 'withdrawn'))
       OR (NEW.state = 'withdrawn' AND OLD.state <> 'verified'))
BEGIN
  SELECT RAISE(ABORT, 'derived run state is terminal (only verified -> withdrawn)');
END;

CREATE TRIGGER derived_run_verified_complete BEFORE UPDATE OF state ON derived_run
WHEN NEW.state = 'verified' AND OLD.state = 'computing'
  AND EXISTS (SELECT 1 FROM derived_observation d
              WHERE d.run_id = NEW.id AND d.state <> 'match')
BEGIN
  SELECT RAISE(ABORT, 'a derived run is verified only when every row matched');
END;

CREATE TRIGGER derived_observation_ins BEFORE INSERT ON derived_observation
WHEN NEW.state IS NOT 'pending'
  OR NOT EXISTS (SELECT 1 FROM derived_run r WHERE r.id = NEW.run_id AND r.state = 'computing')
  OR EXISTS (SELECT 1 FROM derived_observation d WHERE d.id = NEW.id)
  OR CASE WHEN json_valid(NEW.input_obs_ids_json)
               AND json_type(NEW.input_obs_ids_json) = 'array'
          THEN EXISTS (SELECT 1 FROM json_each(NEW.input_obs_ids_json) j
                       WHERE j.type <> 'integer'
                          OR NOT EXISTS (SELECT 1 FROM observation o WHERE o.id = j.value))
               OR (SELECT COUNT(DISTINCT j.value) FROM json_each(NEW.input_obs_ids_json) j)
                  <> json_array_length(NEW.input_obs_ids_json)
          ELSE 1 END
BEGIN
  SELECT RAISE(ABORT, 'a derived row enters a computing run as pending, with a JSON array of distinct existing integer observation ids, and is never replaced');
END;

CREATE TRIGGER derived_observation_immutable
BEFORE UPDATE OF derived_series_id, period, value_text, scale, input_obs_ids_json, run_id,
  computed_at ON derived_observation
BEGIN
  SELECT RAISE(ABORT, 'a derived observation''s value and provenance are immutable');
END;

CREATE TRIGGER derived_observation_state_once BEFORE UPDATE OF state ON derived_observation
WHEN OLD.state <> 'pending'
  OR NOT EXISTS (SELECT 1 FROM derived_run r WHERE r.id = OLD.run_id AND r.state = 'computing')
BEGIN
  SELECT RAISE(ABORT, 'a derived observation''s state is set once, from pending, while its run is computing');
END;

CREATE TRIGGER derived_series_no_delete BEFORE DELETE ON derived_series
BEGIN
  SELECT RAISE(ABORT, 'derived history is kept: deactivate, never delete');
END;

CREATE TRIGGER derived_run_no_delete BEFORE DELETE ON derived_run
BEGIN
  SELECT RAISE(ABORT, 'derived history is kept: never delete');
END;

CREATE TRIGGER derived_observation_no_delete BEFORE DELETE ON derived_observation
BEGIN
  SELECT RAISE(ABORT, 'derived history is kept: never delete');
END;

CREATE TRIGGER derived_event_no_delete BEFORE DELETE ON derived_event
BEGIN
  SELECT RAISE(ABORT, 'derived history is kept: never delete');
END;

CREATE VIEW served_derived AS
WITH eligible AS (
  SELECT d.*, ROW_NUMBER() OVER (PARTITION BY d.derived_series_id, d.period
                                 ORDER BY d.id DESC) AS rn
  FROM derived_observation d
  JOIN derived_run r ON r.id = d.run_id AND r.state = 'verified'
  JOIN derived_series ds ON ds.id = d.derived_series_id AND ds.active = 1
  WHERE d.state = 'match'
    AND NOT EXISTS (SELECT 1 FROM json_each(d.input_obs_ids_json) j
                    WHERE NOT EXISTS (SELECT 1 FROM served_observation so
                                      WHERE so.id = j.value AND so.kind = 'fetched'
                                        AND so.series_id = ds.base_series_id))
)
SELECT ds.key AS derived_key, e.period, e.value_text, e.scale, ds.unit,
  1 AS is_calculated, ds.formula, ds.formula_label_pt, ds.label, ds.base_series_id,
  (SELECT json_group_array(json_object('series_id', x.series_id, 'period', x.period,
                                       'observation_id', x.id))
   FROM (SELECT o.series_id, o.period, o.id FROM json_each(e.input_obs_ids_json) j
         JOIN observation o ON o.id = j.value ORDER BY j.key) x) AS inputs,
  e.input_obs_ids_json AS input_ids,
  p.licence, p.licence_url, p.attribution || ' — Calculado pelo Prumo' AS attribution,
  e.computed_at, e.run_id AS derived_run_id, e.id AS derived_observation_id
FROM eligible e
JOIN derived_series ds ON ds.id = e.derived_series_id
JOIN series s ON s.id = ds.base_series_id
JOIN source p ON p.id = s.source_id
WHERE e.rn = 1;
