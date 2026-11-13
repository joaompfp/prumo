-- What an auditor needs to replay each verification_item comparison: the observed number's
-- decimal separator, the unit/flag the independent channel showed (NULL = not exposed), and why
-- the item did not match (NULL on a match). Expected unit/flag come from series/observation.
ALTER TABLE verification_item ADD COLUMN observed_decimal TEXT CHECK (observed_decimal IN ('.', ','));
ALTER TABLE verification_item ADD COLUMN observed_unit TEXT;
ALTER TABLE verification_item ADD COLUMN observed_flag TEXT;
ALTER TABLE verification_item ADD COLUMN note TEXT;
