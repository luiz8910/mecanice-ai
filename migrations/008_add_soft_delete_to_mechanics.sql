-- Adds soft_delete flag to mechanics for logical deletion.
--
-- Idempotent: safe to re-run.

ALTER TABLE IF EXISTS mechanics
  ADD COLUMN IF NOT EXISTS soft_delete boolean NOT NULL DEFAULT false;
