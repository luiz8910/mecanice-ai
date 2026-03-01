-- Quotations (cotações) table for the Seller Portal inbox.
-- Each row represents a quote request assigned to a seller (vendor).
-- Idempotent migration.

CREATE TABLE IF NOT EXISTS quotations (
  id bigserial PRIMARY KEY,
  code text NOT NULL UNIQUE,
  seller_id bigint NOT NULL REFERENCES vendors(id) ON DELETE RESTRICT,
  workshop_id bigint NOT NULL REFERENCES workshops(id) ON DELETE RESTRICT,
  part_number text NOT NULL,
  part_description text NOT NULL,
  vehicle_info text NULL,
  status text NOT NULL DEFAULT 'NEW'
    CHECK (status IN ('NEW', 'IN_PROGRESS', 'OFFERED', 'CLOSED')),
  is_urgent boolean NOT NULL DEFAULT false,
  offer_submitted boolean NOT NULL DEFAULT false,
  notes text NULL,
  soft_delete boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS quotations_seller_id_idx ON quotations(seller_id);
CREATE INDEX IF NOT EXISTS quotations_workshop_id_idx ON quotations(workshop_id);
CREATE INDEX IF NOT EXISTS quotations_status_idx ON quotations(status);
CREATE INDEX IF NOT EXISTS quotations_code_idx ON quotations(code);
CREATE INDEX IF NOT EXISTS quotations_soft_delete_idx ON quotations(soft_delete);
CREATE INDEX IF NOT EXISTS quotations_created_at_idx ON quotations(created_at DESC);

-- Composite index for the seller inbox query (seller + status + not deleted).
CREATE INDEX IF NOT EXISTS quotations_seller_status_idx
  ON quotations(seller_id, status)
  WHERE soft_delete = false;
