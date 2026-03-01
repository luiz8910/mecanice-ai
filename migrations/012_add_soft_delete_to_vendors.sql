-- Logical deletion for vendors.
-- Idempotent migration.

ALTER TABLE IF EXISTS vendors
  ADD COLUMN IF NOT EXISTS soft_delete boolean NOT NULL DEFAULT false;

-- Rebuild uniqueness so deleted vendors don't block re-creation.
DROP INDEX IF EXISTS vendors_autopart_email_uniq;
CREATE UNIQUE INDEX IF NOT EXISTS vendors_autopart_email_uniq
  ON vendors(autopart_id, email)
  WHERE email IS NOT NULL AND soft_delete = false;

CREATE INDEX IF NOT EXISTS vendors_soft_delete_idx ON vendors(soft_delete);
