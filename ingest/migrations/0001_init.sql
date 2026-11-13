CREATE TABLE source(
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  licence TEXT NOT NULL,
  licence_url TEXT NOT NULL,
  attribution TEXT NOT NULL,
  redistribution_ok INTEGER NOT NULL CHECK (redistribution_ok IN (0,1))
) STRICT;

CREATE TABLE series(
  id TEXT PRIMARY KEY,
  source_id INTEGER NOT NULL REFERENCES source(id),
  indicator_key TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('primary','cross_check')),
  theme TEXT NOT NULL CHECK (theme IN ('economy','demography','energy')),
  geography TEXT NOT NULL,
  frequency TEXT NOT NULL CHECK (frequency IN ('A','S','Q','M','D')),
  unit TEXT NOT NULL CHECK (length(trim(unit)) > 0),
  multiplier REAL,
  seasonal_adjustment TEXT,
  base_year INTEGER,
  native_code TEXT,
  url TEXT,
  active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1))
) STRICT;

CREATE TABLE raw_fetch(
  id INTEGER PRIMARY KEY,
  source_id INTEGER NOT NULL REFERENCES source(id),
  url TEXT NOT NULL,
  params_json TEXT,
  fetched_at TEXT NOT NULL,
  http_status INTEGER,
  sha256 TEXT,
  path TEXT,
  bytes INTEGER,
  ok INTEGER NOT NULL CHECK (ok IN (0,1))
) STRICT;

CREATE TABLE dataset_run(
  id INTEGER PRIMARY KEY,
  source_id INTEGER NOT NULL REFERENCES source(id),
  started_at TEXT NOT NULL,
  finished_at TEXT,
  state TEXT NOT NULL CHECK (state IN ('running','fetched','failed-fetch','failed-validation',
    'pending-verification','verified','failed-verification'))
) STRICT;

CREATE TABLE observation(
  id INTEGER PRIMARY KEY,
  series_id TEXT NOT NULL REFERENCES series(id),
  period TEXT NOT NULL,
  value_text TEXT NOT NULL CHECK (length(value_text) > 0),
  value REAL NOT NULL,
  status_flag TEXT,
  kind TEXT NOT NULL CHECK (kind IN ('fetched','legacy-unverified')),
  dataset_run_id INTEGER NOT NULL REFERENCES dataset_run(id),
  raw_fetch_id INTEGER REFERENCES raw_fetch(id),
  fetched_at TEXT NOT NULL,
  released_at TEXT,
  UNIQUE (series_id, period, raw_fetch_id),
  CHECK (kind = 'legacy-unverified' OR raw_fetch_id IS NOT NULL)
) STRICT;

-- observation carries no frequency, so the period format is enforced against series.frequency.
CREATE TRIGGER observation_period_ins BEFORE INSERT ON observation
WHEN NOT EXISTS (
  SELECT 1 FROM series s WHERE s.id = NEW.series_id AND (
       (s.frequency = 'A' AND NEW.period GLOB '[0-9][0-9][0-9][0-9]')
    OR (s.frequency = 'S' AND NEW.period GLOB '[0-9][0-9][0-9][0-9]-S[12]')
    OR (s.frequency = 'Q' AND NEW.period GLOB '[0-9][0-9][0-9][0-9]-Q[1-4]')
    OR (s.frequency = 'M' AND NEW.period GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]'
        AND substr(NEW.period,6,2) BETWEEN '01' AND '12')
    OR (s.frequency = 'D' AND NEW.period GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'
        AND date(NEW.period) = NEW.period)))
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
        AND date(NEW.period) = NEW.period)))
BEGIN
  SELECT RAISE(ABORT, 'observation.period does not match series.frequency');
END;

CREATE TABLE quarantine(
  id INTEGER PRIMARY KEY,
  dataset_run_id INTEGER NOT NULL REFERENCES dataset_run(id),
  series_id TEXT REFERENCES series(id),
  raw_period TEXT,
  raw_value TEXT,
  reason TEXT NOT NULL,
  created_at TEXT NOT NULL
) STRICT;

CREATE TABLE event(
  id INTEGER PRIMARY KEY,
  ts TEXT NOT NULL,
  dataset_run_id INTEGER REFERENCES dataset_run(id),
  kind TEXT NOT NULL CHECK (kind IN ('fetch_failure','format_change','revision','cross_check_gap',
    'verification_failure','refetch')),
  detail_json TEXT
) STRICT;

CREATE TABLE verification(
  id INTEGER PRIMARY KEY,
  dataset_run_id INTEGER NOT NULL REFERENCES dataset_run(id),
  seed INTEGER NOT NULL,
  sample_size INTEGER NOT NULL,
  passed INTEGER NOT NULL CHECK (passed IN (0,1)),
  created_at TEXT NOT NULL
) STRICT;

CREATE TABLE verification_item(
  id INTEGER PRIMARY KEY,
  verification_id INTEGER NOT NULL REFERENCES verification(id),
  series_id TEXT NOT NULL REFERENCES series(id),
  period TEXT NOT NULL,
  expected_text TEXT,
  observed_text TEXT,
  evidence_url TEXT,
  match INTEGER NOT NULL CHECK (match IN (0,1))
) STRICT;

CREATE TABLE setting(
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
) STRICT;
INSERT INTO setting(key, value) VALUES ('legacy_served', '0');

-- Latest observation per (series, period) among those from verified runs;
-- legacy rows count only when legacy_served='1' and never when a fetched row exists.
CREATE VIEW served_observation AS
WITH eligible AS (
  SELECT o.* FROM observation o
  JOIN dataset_run r ON r.id = o.dataset_run_id AND r.state = 'verified'
  WHERE o.kind = 'fetched'
     OR (SELECT value FROM setting WHERE key = 'legacy_served') = '1'
)
SELECT e.* FROM eligible e
WHERE NOT EXISTS (
  SELECT 1 FROM eligible n
  WHERE n.series_id = e.series_id AND n.period = e.period
    AND ((e.kind = 'legacy-unverified' AND n.kind = 'fetched')
         OR (n.kind = e.kind AND n.id > e.id)));
