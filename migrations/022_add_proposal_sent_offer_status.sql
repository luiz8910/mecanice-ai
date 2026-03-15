ALTER TABLE IF EXISTS seller_offers
  DROP CONSTRAINT IF EXISTS seller_offers_status_check;

UPDATE seller_offers
SET status = CASE status
  WHEN 'draft' THEN 'DRAFT'
  WHEN 'submitted' THEN 'SUBMITTED_OPTIONS'
  WHEN 'cancelled' THEN 'CANCELLED'
  ELSE status
END;

ALTER TABLE IF EXISTS seller_offers
  ALTER COLUMN status SET DEFAULT 'DRAFT';

ALTER TABLE IF EXISTS seller_offers
  ADD CONSTRAINT seller_offers_status_check
  CHECK (status IN ('DRAFT', 'SUBMITTED_OPTIONS', 'FINALIZED_QUOTE', 'proposal_sent', 'CANCELLED'));
