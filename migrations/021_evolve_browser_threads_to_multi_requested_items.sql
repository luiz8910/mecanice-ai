-- Evolve browser-first quotation threads to support:
-- - vehicle data at thread level
-- - multiple requested items per thread
-- - seller responses grouped by requested item
-- - final totals only for finalized quotes

ALTER TABLE IF EXISTS quote_threads
  ADD COLUMN IF NOT EXISTS vehicle_plate text NULL;

ALTER TABLE IF EXISTS quote_threads
  ADD COLUMN IF NOT EXISTS vehicle_brand text NULL;

ALTER TABLE IF EXISTS quote_threads
  ADD COLUMN IF NOT EXISTS vehicle_model text NULL;

ALTER TABLE IF EXISTS quote_threads
  ADD COLUMN IF NOT EXISTS vehicle_year text NULL;

ALTER TABLE IF EXISTS quote_threads
  ADD COLUMN IF NOT EXISTS vehicle_engine text NULL;

ALTER TABLE IF EXISTS quote_threads
  ADD COLUMN IF NOT EXISTS vehicle_version text NULL;

ALTER TABLE IF EXISTS quote_threads
  ADD COLUMN IF NOT EXISTS vehicle_notes text NULL;

UPDATE quote_threads t
SET
  vehicle_plate = COALESCE(t.vehicle_plate, pr.vehicle_plate),
  vehicle_brand = COALESCE(t.vehicle_brand, pr.vehicle_brand),
  vehicle_model = COALESCE(t.vehicle_model, pr.vehicle_model),
  vehicle_year = COALESCE(t.vehicle_year, pr.vehicle_year),
  vehicle_engine = COALESCE(t.vehicle_engine, pr.vehicle_engine),
  vehicle_version = COALESCE(t.vehicle_version, pr.vehicle_version),
  vehicle_notes = COALESCE(t.vehicle_notes, pr.vehicle_notes)
FROM part_requests pr
WHERE pr.thread_id = t.id;

CREATE TABLE IF NOT EXISTS requested_items (
  id bigserial PRIMARY KEY,
  request_id bigint NOT NULL REFERENCES part_requests(id) ON DELETE CASCADE,
  description text NOT NULL,
  part_number text NULL,
  quantity integer NOT NULL DEFAULT 1 CHECK (quantity > 0),
  notes text NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS requested_items_request_id_idx
  ON requested_items(request_id);

INSERT INTO requested_items (
  request_id,
  description,
  part_number,
  quantity,
  notes,
  created_at
)
SELECT
  pr.id,
  pr.original_description,
  pr.part_number,
  GREATEST(COALESCE(pr.requested_items_count, 1), 1),
  NULL,
  pr.created_at
FROM part_requests pr
WHERE NOT EXISTS (
  SELECT 1
  FROM requested_items ri
  WHERE ri.request_id = pr.id
);

UPDATE part_requests pr
SET requested_items_count = counts.requested_items_count
FROM (
  SELECT request_id, count(*)::integer AS requested_items_count
  FROM requested_items
  GROUP BY request_id
) counts
WHERE counts.request_id = pr.id;

ALTER TABLE IF EXISTS suggested_parts
  ADD COLUMN IF NOT EXISTS requested_item_id bigint NULL REFERENCES requested_items(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS suggested_parts_requested_item_id_idx
  ON suggested_parts(requested_item_id);

UPDATE suggested_parts sp
SET requested_item_id = ri.id
FROM requested_items ri
WHERE sp.request_id = ri.request_id
  AND sp.requested_item_id IS NULL
  AND ri.id = (
    SELECT ri2.id
    FROM requested_items ri2
    WHERE ri2.request_id = sp.request_id
    ORDER BY ri2.id ASC
    LIMIT 1
  );

ALTER TABLE IF EXISTS seller_offers
  ADD COLUMN IF NOT EXISTS finalized_at timestamptz NULL;

ALTER TABLE IF EXISTS seller_offers
  DROP CONSTRAINT IF EXISTS seller_offers_status_check;

UPDATE seller_offers
SET status = CASE status
  WHEN 'draft' THEN 'DRAFT'
  WHEN 'submitted' THEN 'SUBMITTED_OPTIONS'
  WHEN 'cancelled' THEN 'CANCELLED'
  ELSE status
END;

UPDATE seller_offers
SET total_amount = NULL
WHERE status = 'SUBMITTED_OPTIONS';

ALTER TABLE seller_offers
  ADD CONSTRAINT seller_offers_status_check
  CHECK (status IN ('DRAFT', 'SUBMITTED_OPTIONS', 'FINALIZED_QUOTE', 'CANCELLED'));

ALTER TABLE IF EXISTS seller_offer_items
  ADD COLUMN IF NOT EXISTS requested_item_id bigint NULL REFERENCES requested_items(id) ON DELETE CASCADE;

ALTER TABLE IF EXISTS seller_offer_items
  ADD COLUMN IF NOT EXISTS metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE IF EXISTS seller_offer_items
  ADD COLUMN IF NOT EXISTS is_final_choice boolean NOT NULL DEFAULT false;

ALTER TABLE IF EXISTS seller_offer_items
  ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS seller_offer_items_requested_item_id_idx
  ON seller_offer_items(requested_item_id);

UPDATE seller_offer_items soi
SET requested_item_id = ri.id
FROM seller_offers so
JOIN part_requests pr ON pr.thread_id = so.thread_id
JOIN requested_items ri ON ri.request_id = pr.id
WHERE soi.offer_id = so.id
  AND soi.requested_item_id IS NULL
  AND ri.id = (
    SELECT ri2.id
    FROM requested_items ri2
    WHERE ri2.request_id = pr.id
    ORDER BY ri2.id ASC
    LIMIT 1
  );

UPDATE thread_messages
SET body = CONCAT(
  'Resposta enviada com ',
  COALESCE(metadata_json ->> 'items_count', '0'),
  ' opção(ões).'
)
WHERE type = 'offer_notice'
  AND body = 'Offer submitted';
