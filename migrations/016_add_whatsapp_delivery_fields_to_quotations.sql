-- Add WhatsApp delivery fields and allow CONFIRMED status for quotations.
-- Idempotent migration.

ALTER TABLE quotations
  ADD COLUMN IF NOT EXISTS whatsapp_sent_at timestamptz NULL;

ALTER TABLE quotations
  ADD COLUMN IF NOT EXISTS whatsapp_send_error varchar(255) NULL;

CREATE INDEX IF NOT EXISTS quotations_whatsapp_sent_at_idx
  ON quotations(whatsapp_sent_at);

DO $$
DECLARE
  constraint_name text;
BEGIN
  FOR constraint_name IN
    SELECT conname
    FROM pg_constraint
    WHERE conrelid = 'quotations'::regclass
      AND contype = 'c'
      AND pg_get_constraintdef(oid) ILIKE '%status%'
  LOOP
    EXECUTE format('ALTER TABLE quotations DROP CONSTRAINT %I', constraint_name);
  END LOOP;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conrelid = 'quotations'::regclass
      AND conname = 'quotations_status_check'
  ) THEN
    ALTER TABLE quotations
      ADD CONSTRAINT quotations_status_check
      CHECK (status IN ('NEW', 'IN_PROGRESS', 'OFFERED', 'CONFIRMED', 'CLOSED'));
  END IF;
END $$;
