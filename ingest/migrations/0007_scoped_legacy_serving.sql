-- Migration 0007 (Task 17A): source-scoped eligibility of legacy rows.
--
-- Keeps the existing licence gate (0005) and the fetched-verified-over-legacy precedence
-- untouched. Adds ONE scoped permission, seeded for worldbank only (the owner-approved source
-- for dated-data continuity): a 'legacy-unverified' row becomes eligible when the explicit
-- global `legacy_served` = '1' (backward compatible, exactly as before) OR when a
-- source-specific setting legacy_served_source:<source> = '1' AND the row's series is active
-- AND its source allows redistribution (the existing join). The inactive World Bank PPP
-- unit-conflict series are NOT exposed by the scoped switch; every other source is disabled
-- unless a setting row is added by a later reviewed change. No value/unit conversion, no new
-- configuration abstraction: the existing `setting` table carries the flag.
--
-- World Bank permission justification: owner instruction 2026-11-12 (keep serving BM data with
-- honest original retrieval dates when refresh fails), WDI CC BY 4.0 licence archived in the
-- registry, and legacy rows carry their original fetched_at (2026-02-27..2026-04-06 export).
INSERT INTO setting(key, value) VALUES ('legacy_served_source:worldbank', '1');

DROP VIEW served_observation;
CREATE VIEW served_observation AS
WITH eligible AS (
  SELECT o.* FROM observation o
  JOIN dataset_run r ON r.id = o.dataset_run_id AND r.state = 'verified'
  JOIN series s ON s.id = o.series_id
  JOIN source p ON p.id = s.source_id AND p.redistribution_ok = 1
  WHERE o.kind = 'fetched'
     OR (SELECT value FROM setting WHERE key = 'legacy_served') = '1'
     OR (o.kind = 'legacy-unverified' AND s.active = 1
         AND (SELECT value FROM setting
              WHERE key = 'legacy_served_source:' || p.name) = '1')
)
SELECT e.* FROM eligible e
WHERE NOT EXISTS (
  SELECT 1 FROM eligible n
  WHERE n.series_id = e.series_id AND n.period = e.period
    AND ((e.kind = 'legacy-unverified' AND n.kind = 'fetched')
         OR (n.kind = e.kind AND n.id > e.id)));
