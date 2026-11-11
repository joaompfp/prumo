-- Ruling R: every field the comparison used is stored on the item, so an auditor can replay it
-- without the registry: the expected side (decimal, unit, flag as compared), the key the
-- verifier said the result was for, and the sha256 of the evidence bytes kept in the raw store
-- (under source "verify-<source>").
ALTER TABLE verification_item ADD COLUMN expected_decimal TEXT CHECK (expected_decimal IN ('.', ','));
ALTER TABLE verification_item ADD COLUMN expected_unit TEXT;
ALTER TABLE verification_item ADD COLUMN expected_flag TEXT;
ALTER TABLE verification_item ADD COLUMN observed_series_id TEXT;
ALTER TABLE verification_item ADD COLUMN observed_period TEXT;
ALTER TABLE verification_item ADD COLUMN evidence_sha256 TEXT;
