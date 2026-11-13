-- Migration 0011 (Task 20, final-review fixes A-I1, A-I2, A-M1, A-M2).
--
-- 1. Serving follows DATA time (A-I1). Among verified fetched rows of one (series, period)
--    the served vintage is the one with the latest observation.fetched_at (the publisher
--    retrieval time, the ORIGINAL receipt time for recorded replays), ties broken by the
--    higher id. Before, insertion order alone decided, so an older recorded bundle - or two
--    live writers committing in the reverse of their fetch order - could replace newer data.
--    Fetched rows all carry one UTC spelling ('+00:00', written by ingest.pipeline), so the
--    text comparison is chronological. Legacy rows keep the id tie-break unchanged: the
--    importer already inserts them in fetched_at order, and their mixed 'Z'/fractional
--    spellings would not compare correctly as text within one second.
-- 2. Fetched rows of an INACTIVE series are no longer served (A-I2). 'active: false' is the
--    documented remedy for definition/unit defects; it now withdraws already-verified fetched
--    rows too (history stays in `observation`; reactivation serves them again). Legacy rows
--    keep their exact previous eligibility (global switch, or scoped switch + active).
-- 3. New run state 'withdrawn' (A-I2): a reviewed, terminal withdrawal of ONE verified
--    fetched vintage. Reachable only from 'verified', only for non-legacy runs, and only when
--    an event(withdrawal) row for that run already exists - ingest.db.Db.withdraw_run writes
--    the event (with the operator's reason) and the state change in one transaction. The
--    triggers below make any other path (hand-written UPDATE, generic state setters) fail.
-- 4. New run state 'failed-operational' + event kind 'operational_failure' (A-M1, A-M2): a
--    run interrupted by our own environment (exception, SIGTERM, database lock, process
--    killed and closed at the next scheduler start) is recorded honestly, never as a
--    publisher failure (failed-fetch) or a format change (failed-validation).
-- 5. New event kind 'series_deactivated' (A-I2): registry sync records each series that left
--    the registry and was set inactive.
--
-- No existing row changes. dataset_run and event are rebuilt (create-new / copy / drop /
-- rename) because their CHECKs cannot be altered in place, exactly like 0009; `_migrate`
-- runs this with foreign_keys OFF inside one transaction and checks foreign keys before
-- COMMIT. The served view is recreated from 0009 with only the two changes above.
DROP VIEW served_observation;

CREATE TABLE dataset_run_0011(
  id INTEGER PRIMARY KEY,
  source_id INTEGER NOT NULL REFERENCES source(id),
  started_at TEXT NOT NULL,
  finished_at TEXT,
  state TEXT NOT NULL CHECK (state IN ('running','fetched','failed-fetch','failed-validation',
    'pending-verification','verified','failed-verification','blocked-stale',
    'failed-operational','withdrawn')),
  dataset_key TEXT,
  input_origin TEXT NOT NULL DEFAULT 'live'
    CHECK (input_origin IN ('live','recorded','legacy'))
) STRICT;
INSERT INTO dataset_run_0011
  SELECT id, source_id, started_at, finished_at, state, dataset_key, input_origin
  FROM dataset_run;
DROP TABLE dataset_run;
ALTER TABLE dataset_run_0011 RENAME TO dataset_run;
CREATE INDEX dataset_run_key ON dataset_run(dataset_key, id);

CREATE TABLE event_0011(
  id INTEGER PRIMARY KEY,
  ts TEXT NOT NULL,
  dataset_run_id INTEGER REFERENCES dataset_run(id),
  kind TEXT NOT NULL CHECK (kind IN ('fetch_failure','format_change','revision',
    'cross_check_gap','verification_failure','refetch','stale_refusal',
    'operational_failure','withdrawal','series_deactivated')),
  detail_json TEXT
) STRICT;
INSERT INTO event_0011 SELECT id, ts, dataset_run_id, kind, detail_json FROM event;
DROP TABLE event;
ALTER TABLE event_0011 RENAME TO event;

-- Withdrawal guards (see 3.). 'withdrawn' is never inserted directly and never left.
CREATE TRIGGER dataset_run_withdrawn_ins BEFORE INSERT ON dataset_run
WHEN NEW.state = 'withdrawn'
BEGIN
  SELECT RAISE(ABORT, 'a run is withdrawn only through Db.withdraw_run');
END;

CREATE TRIGGER dataset_run_withdrawn_terminal BEFORE UPDATE OF state ON dataset_run
WHEN OLD.state = 'withdrawn' AND NEW.state <> 'withdrawn'
BEGIN
  SELECT RAISE(ABORT, 'withdrawn is terminal');
END;

CREATE TRIGGER dataset_run_withdraw_reviewed BEFORE UPDATE OF state ON dataset_run
WHEN NEW.state = 'withdrawn' AND OLD.state <> 'withdrawn'
  AND (OLD.state <> 'verified' OR OLD.input_origin = 'legacy'
       OR NOT EXISTS (SELECT 1 FROM event e
                      WHERE e.dataset_run_id = NEW.id AND e.kind = 'withdrawal'))
BEGIN
  SELECT RAISE(ABORT, 'withdraw only a verified non-legacy run through Db.withdraw_run');
END;

CREATE VIEW served_observation AS
WITH eligible AS (
  SELECT o.* FROM observation o
  JOIN dataset_run r ON r.id = o.dataset_run_id AND r.state = 'verified'
  JOIN series s ON s.id = o.series_id
  JOIN source p ON p.id = s.source_id AND p.redistribution_ok = 1
  WHERE (o.kind = 'fetched' AND s.active = 1)
     OR (o.kind = 'legacy-unverified'
         AND ((SELECT value FROM setting WHERE key = 'legacy_served') = '1'
              OR (s.active = 1
                  AND (SELECT value FROM setting
                       WHERE key = 'legacy_served_source:' || p.name) = '1')))
)
SELECT e.* FROM eligible e
WHERE NOT EXISTS (
  SELECT 1 FROM eligible n
  WHERE n.series_id = e.series_id AND n.period = e.period
    AND ((e.kind = 'legacy-unverified' AND n.kind = 'fetched')
         OR (n.kind = 'fetched' AND e.kind = 'fetched'
             AND (n.fetched_at > e.fetched_at
                  OR (n.fetched_at = e.fetched_at AND n.id > e.id)))
         OR (n.kind = 'legacy-unverified' AND e.kind = 'legacy-unverified'
             AND n.id > e.id)));
