-- Add original_message to quotations, create quotation_items and quotation_events tables.
-- Idempotent migration.

-- 1) Add original_message column to quotations
ALTER TABLE quotations
  ADD COLUMN IF NOT EXISTS original_message text NULL;

-- 2) Quotation items (peças identificadas / itens do orçamento)
CREATE TABLE IF NOT EXISTS quotation_items (
  id bigserial PRIMARY KEY,
  quotation_id bigint NOT NULL REFERENCES quotations(id) ON DELETE CASCADE,
  part_number text NOT NULL,
  description text NOT NULL DEFAULT '',
  brand text NULL,
  compatibility text NULL,
  price numeric(12,2) NULL,
  availability text NULL DEFAULT 'Em estoque',
  delivery_time text NULL,
  confidence_score numeric(5,2) NULL,
  notes text NULL,
  selected boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS quotation_items_quotation_id_idx
  ON quotation_items(quotation_id);

-- 3) Quotation events (histórico / timeline)
CREATE TABLE IF NOT EXISTS quotation_events (
  id bigserial PRIMARY KEY,
  quotation_id bigint NOT NULL REFERENCES quotations(id) ON DELETE CASCADE,
  event_type text NOT NULL DEFAULT 'status_change',
  description text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS quotation_events_quotation_id_idx
  ON quotation_events(quotation_id);
CREATE INDEX IF NOT EXISTS quotation_events_created_at_idx
  ON quotation_events(quotation_id, created_at);
