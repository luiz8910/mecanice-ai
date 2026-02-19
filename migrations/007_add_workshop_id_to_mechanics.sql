-- Adds workshop_id to mechanics for existing databases that were created
-- without this column.
--
-- This file is intentionally idempotent because `make migrate-docker` re-runs
-- all scripts and ignores errors.

ALTER TABLE IF EXISTS mechanics
  ADD COLUMN IF NOT EXISTS workshop_id bigint NULL;
