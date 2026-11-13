-- Migration 0006 (Task 16): native quarter-hour frequency PT15M (E-REDES 15-minute data).
--
-- Extends series.frequency's CHECK with 'PT15M' and replaces the two observation period
-- triggers with versions that also accept the single canonical UTC spelling
-- 'YYYY-MM-DDTHH:MM:SS+00:00' (ASCII digits, an actual Gregorian date, hour 00-23, minute
-- 00/15/30/45, seconds 00). All prior A/S/Q/M/D rules are unchanged. Old migrations are
-- untouched.
--
-- The series CHECK cannot be altered in place, so series is rebuilt (create-new / copy /
-- drop / rename). That is only sound with foreign_keys OFF at statement time: with FK ON,
-- SQLite would (a) fail the DROP on immediate FK references from observation/..., and
-- (b) silently rewrite child REFERENCES clauses during RENAME. `_migrate` (ingest/db.py)
-- therefore applies every migration inside ONE transaction with foreign_keys temporarily
-- OFF and verifies PRAGMA foreign_key_check afterwards. No row is deleted; the view and
-- settings are untouched; the triggers are recreated (their WHEN clause names `series`).
-- The view served_observation (0005, licence gate) references `series`, and SQLite
-- re-prepares views on schema change, so it must be dropped before the rebuild and
-- recreated VERBATIM afterwards - same rows eligible, same gate, same text as
-- 0005_served_licence_gate.sql.
CREATE TABLE series_pt15m(
  id TEXT PRIMARY KEY,
  source_id INTEGER NOT NULL REFERENCES source(id),
  indicator_key TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('primary','cross_check')),
  theme TEXT NOT NULL CHECK (theme IN ('economy','demography','energy')),
  geography TEXT NOT NULL,
  frequency TEXT NOT NULL CHECK (frequency IN ('A','S','Q','M','D','PT15M')),
  unit TEXT NOT NULL CHECK (length(trim(unit)) > 0),
  multiplier REAL,
  seasonal_adjustment TEXT,
  base_year INTEGER,
  native_code TEXT,
  url TEXT,
  active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1))
) STRICT;
INSERT INTO series_pt15m SELECT id, source_id, indicator_key, role, theme, geography,
  frequency, unit, multiplier, seasonal_adjustment, base_year, native_code, url, active
  FROM series;
DROP TRIGGER observation_period_ins;
DROP TRIGGER observation_period_upd;
DROP VIEW served_observation;
DROP TABLE series;
ALTER TABLE series_pt15m RENAME TO series;

-- The PT15M arm: exact 25-char canonical spelling (GLOB has no wildcards); strftime
-- round-trip proves the Gregorian date/time is real and UTC (+00:00) and rejects offsets;
-- the explicit hour/minute/second bounds cover what strftime normalizes (e.g. 24:00).
CREATE TRIGGER observation_period_ins BEFORE INSERT ON observation
WHEN NOT EXISTS (
  SELECT 1 FROM series s WHERE s.id = NEW.series_id AND (
       (s.frequency = 'A' AND NEW.period GLOB '[0-9][0-9][0-9][0-9]')
    OR (s.frequency = 'S' AND NEW.period GLOB '[0-9][0-9][0-9][0-9]-S[12]')
    OR (s.frequency = 'Q' AND NEW.period GLOB '[0-9][0-9][0-9][0-9]-Q[1-4]')
    OR (s.frequency = 'M' AND NEW.period GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]'
        AND substr(NEW.period,6,2) BETWEEN '01' AND '12')
    OR (s.frequency = 'D' AND NEW.period GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
        AND date(NEW.period) = NEW.period)
    OR (s.frequency = 'PT15M'
        AND NEW.period GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]T[0-2][0-9]:[0-9][0-9]:[0-9][0-9]+00:00'
        AND strftime('%Y-%m-%dT%H:%M:%S+00:00', NEW.period) = NEW.period
        AND substr(NEW.period,12,2) BETWEEN '00' AND '23'
        AND substr(NEW.period,15,2) IN ('00','15','30','45')
        AND substr(NEW.period,18,2) = '00')))
BEGIN
  SELECT RAISE(ABORT, 'observation.period does not match series.frequency');
END;

CREATE TRIGGER observation_period_upd BEFORE UPDATE OF series_id, period ON observation
WHEN NOT EXISTS (
  SELECT 1 FROM series s WHERE s.id = NEW.series_id AND (
       (s.frequency = 'A' AND NEW.period GLOB '[0-9][0-9][0-9][0-9]')
    OR (s.frequency = 'S' AND NEW.period GLOB '[0-9][0-9][0-9][0-9]-S[12]')
    OR (s.frequency = 'Q' AND NEW.period GLOB '[0-9][0-9][0-9][0-9]-Q[1-4]')
    OR (s.frequency = 'M' AND NEW.period GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]'
        AND substr(NEW.period,6,2) BETWEEN '01' AND '12')
    OR (s.frequency = 'D' AND NEW.period GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
        AND date(NEW.period) = NEW.period)
    OR (s.frequency = 'PT15M'
        AND NEW.period GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]T[0-2][0-9]:[0-9][0-9]:[0-9][0-9]+00:00'
        AND strftime('%Y-%m-%dT%H:%M:%S+00:00', NEW.period) = NEW.period
        AND substr(NEW.period,12,2) BETWEEN '00' AND '23'
        AND substr(NEW.period,15,2) IN ('00','15','30','45')
        AND substr(NEW.period,18,2) = '00')))
BEGIN
  SELECT RAISE(ABORT, 'observation.period does not match series.frequency');
END;

-- Recreated verbatim from 0005_served_licence_gate.sql (licence gate included).
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
