-- Per-run observation reads. Serves the base-content read (`Db.run_content`), the chain walk
-- (`Db.content_base_run`), verification sampling (`observations_of_run`, receipts) and the
-- withdraw checks (`_run_has_observations`), none of which had an index on dataset_run_id and
-- so scanned `observation`. Measured numbers (production copy, 497k rows): see
-- docs/superpowers/specs/2026-11-15-vintage-dedupe-and-language-neutral-data-design.md,
-- Decision 1 (observations_of_run 0.19 -> 0.02 s; build 6.6 s, +18 MB).
CREATE INDEX observation_run ON observation(dataset_run_id, series_id);
