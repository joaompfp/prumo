-- Serving licence gate (Ruling AD, spec §11.4): a row is served only when its SERIES'
-- publisher allows redistribution (source.redistribution_ok = 1). Verification is technical;
-- it does not authorize serving, so a verified run of a denied source serves nothing.
-- The gate is in the VIEW, not the tables: revoking or reapproving redistribution_ok takes
-- effect immediately for every existing row, fetched and legacy alike (legacy_served='1'
-- included), and no observation/history is ever deleted. Every other serving rule is
-- unchanged: verified runs only, latest vintage wins, legacy never hides a fetched row.
DROP VIEW served_observation;
CREATE VIEW served_observation AS
WITH eligible AS (
  SELECT o.* FROM observation o
  JOIN dataset_run r ON r.id = o.dataset_run_id AND r.state = 'verified'
  JOIN series s ON s.id = o.series_id
  JOIN source p ON p.id = s.source_id AND p.redistribution_ok = 1
  WHERE o.kind = 'fetched'
     OR (SELECT value FROM setting WHERE key = 'legacy_served') = '1'
)
SELECT e.* FROM eligible e
WHERE NOT EXISTS (
  SELECT 1 FROM eligible n
  WHERE n.series_id = e.series_id AND n.period = e.period
    AND ((e.kind = 'legacy-unverified' AND n.kind = 'fetched')
         OR (n.kind = e.kind AND n.id > e.id)));
