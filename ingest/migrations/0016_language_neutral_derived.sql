-- Migration 0016 (vintage-dedupe / language-neutral plan, Task 2; spec Decision 3).
--
-- The derived data layer carries codes only; every reader-facing sentence is rendered by the
-- `presentation` package (per language).
-- 1. derived_series loses its two reader-text columns (`label`, `formula_label_pt`), and
--    `unit` becomes a unit CODE from a closed list (ingest.models.DERIVED_UNITS):
--    '%' -> pct, 'p.p.' -> pp, 'balance' -> balance, 'index 2015=100' -> index_2015_100.
--    Any other stored unit fails the new CHECK and aborts the migration (fail fast: nothing
--    is guessed). The table is rebuilt (create-new / copy / drop / rename, as 0011) so the
--    CHECK can be added; ids are copied, so derived_observation / derived_event keep pointing
--    at the same rows, and neither table is touched. `_migrate` runs this with foreign_keys
--    OFF in one transaction and checks foreign keys before COMMIT. The 0014 guards on the
--    table (definition immutable, no REPLACE, no DELETE) are dropped with it and recreated
--    verbatim.
-- 2. served_derived is dropped and recreated from 0014 with: no `formula_label_pt`, no
--    `label`, `unit` = the code, and `attribution` = the publisher's attribution only
--    (`is_calculated` stays the data-layer fact; "Calculado pelo Prumo" is presentation).
--    Serving rules are unchanged.
DROP VIEW served_derived;

CREATE TABLE derived_series_0016(
  id INTEGER PRIMARY KEY,
  key TEXT NOT NULL UNIQUE,
  formula TEXT NOT NULL CHECK (formula IN ('period_change','period_change_pct','yoy_change',
    'yoy_change_pct','rebase_100')),
  base_series_id TEXT NOT NULL REFERENCES series(id),
  params_json TEXT NOT NULL DEFAULT '{}',
  unit TEXT NOT NULL CHECK (unit IN ('pct','pp','balance','index_2015_100')),
  active INTEGER NOT NULL CHECK (active IN (0,1))
) STRICT;
INSERT INTO derived_series_0016(id, key, formula, base_series_id, params_json, unit, active)
  SELECT id, key, formula, base_series_id, params_json,
         CASE unit WHEN '%' THEN 'pct' WHEN 'p.p.' THEN 'pp' WHEN 'balance' THEN 'balance'
                   WHEN 'index 2015=100' THEN 'index_2015_100' ELSE unit END,
         active
  FROM derived_series;
DROP TABLE derived_series;
ALTER TABLE derived_series_0016 RENAME TO derived_series;

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

CREATE TRIGGER derived_series_no_delete BEFORE DELETE ON derived_series
BEGIN
  SELECT RAISE(ABORT, 'derived history is kept: deactivate, never delete');
END;

CREATE VIEW served_derived AS
SELECT ds.key AS derived_key, d.period, d.value_text, d.scale, ds.unit,
  1 AS is_calculated, ds.formula, ds.base_series_id,
  (SELECT json_group_array(json_object('series_id', x.series_id, 'period', x.period,
                                       'observation_id', x.id))
   FROM (SELECT o.series_id, o.period, o.id FROM json_each(d.input_obs_ids_json) j
         JOIN observation o ON o.id = j.value ORDER BY j.key) x) AS inputs,
  d.input_obs_ids_json AS input_ids,
  p.licence, p.licence_url, p.attribution AS attribution,
  d.computed_at, d.run_id AS derived_run_id, d.id AS derived_observation_id
FROM derived_series ds
JOIN derived_observation d ON d.derived_series_id = ds.id
JOIN series s ON s.id = ds.base_series_id
JOIN source p ON p.id = s.source_id
WHERE ds.active = 1
  -- CASE keeps the order: the candidate test first, the input test only for that one row
  AND CASE WHEN d.id = (SELECT c.id FROM derived_observation c
                        JOIN derived_run r ON r.id = c.run_id AND r.state = 'verified'
                        WHERE c.derived_series_id = d.derived_series_id
                          AND c.period = d.period AND c.state = 'match'
                        ORDER BY c.id DESC LIMIT 1)
      THEN NOT EXISTS (SELECT 1 FROM json_each(d.input_obs_ids_json) j
                       WHERE NOT EXISTS (SELECT 1 FROM served_observation so
                                         WHERE so.id = j.value AND so.kind = 'fetched'
                                           AND so.series_id = ds.base_series_id))
      ELSE 0 END;
