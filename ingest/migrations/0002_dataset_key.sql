-- Dataset identity: "<source name>:<sha256 of sorted series ids joined by newline>".
-- "Previous run of a dataset" = latest earlier dataset_run with the same dataset_key.
ALTER TABLE dataset_run ADD COLUMN dataset_key TEXT;
CREATE INDEX dataset_run_key ON dataset_run(dataset_key, id);

-- Links each raw payload to the run that fetched it, so a run's payload fingerprint
-- (sha256 over its responses' sorted sha256s) is computed from raw_fetch, not duplicated.
ALTER TABLE raw_fetch ADD COLUMN dataset_run_id INTEGER REFERENCES dataset_run(id);
CREATE INDEX raw_fetch_run ON raw_fetch(dataset_run_id);
