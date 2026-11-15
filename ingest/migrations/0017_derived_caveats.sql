-- Migration 0017 (vintage-dedupe / language-neutral plan, Task 3; spec Decision 2).
--
-- A derived series may carry caveat CODES (ingest.models.DERIVED_CAVEATS: 'sa_base',
-- 'stock_base') saying why Prumo's calculated rate differs from the publisher's headline rate.
-- Codes only; the sentence is rendered by the `presentation` package. The column is a JSON
-- array of codes, default '[]' (every existing row is uncaveated until the registry sync).
-- It is a mutable field (the 0014 immutability trigger fires only on formula, base_series_id,
-- params_json), synced like unit/active. served_derived is dropped and recreated verbatim
-- from 0016 plus the `caveats` column.
DROP VIEW served_derived;

ALTER TABLE derived_series ADD COLUMN caveats_json TEXT NOT NULL DEFAULT '[]';

CREATE VIEW served_derived AS
SELECT ds.key AS derived_key, d.period, d.value_text, d.scale, ds.unit,
  1 AS is_calculated, ds.formula, ds.base_series_id,
  (SELECT json_group_array(json_object('series_id', x.series_id, 'period', x.period,
                                       'observation_id', x.id))
   FROM (SELECT o.series_id, o.period, o.id FROM json_each(d.input_obs_ids_json) j
         JOIN observation o ON o.id = j.value ORDER BY j.key) x) AS inputs,
  d.input_obs_ids_json AS input_ids,
  p.licence, p.licence_url, p.attribution AS attribution,
  d.computed_at, d.run_id AS derived_run_id, d.id AS derived_observation_id,
  ds.caveats_json AS caveats
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
