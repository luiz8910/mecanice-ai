-- Vendor metrics with timestamped events for reporting.
-- Idempotent migration.

ALTER TABLE IF EXISTS vendors
  ADD COLUMN IF NOT EXISTS served_workshops_count integer NOT NULL DEFAULT 0;

ALTER TABLE IF EXISTS vendors
  ADD COLUMN IF NOT EXISTS quotes_received_count integer NOT NULL DEFAULT 0;

ALTER TABLE IF EXISTS vendors
  ADD COLUMN IF NOT EXISTS sales_converted_count integer NOT NULL DEFAULT 0;

ALTER TABLE IF EXISTS vendors
  ADD COLUMN IF NOT EXISTS metrics_updated_at timestamptz NOT NULL DEFAULT now();

CREATE TABLE IF NOT EXISTS vendor_metric_events (
  id bigserial PRIMARY KEY,
  vendor_id bigint NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
  autopart_id bigint NOT NULL REFERENCES autoparts(id) ON DELETE RESTRICT,
  workshop_id bigint NULL REFERENCES workshops(id) ON DELETE SET NULL,
  conversation_id text NULL REFERENCES quote_conversations(conversation_id) ON DELETE SET NULL,
  request_id text NULL,
  event_type text NOT NULL CHECK (
    event_type IN (
      'WORKSHOP_ASSIGNED',
      'QUOTE_RECEIVED',
      'SALE_CONVERTED'
    )
  ),
  event_ts timestamptz NOT NULL DEFAULT now(),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS vendor_metric_events_vendor_ts_idx
  ON vendor_metric_events(vendor_id, event_ts DESC);

CREATE INDEX IF NOT EXISTS vendor_metric_events_type_ts_idx
  ON vendor_metric_events(event_type, event_ts DESC);

CREATE INDEX IF NOT EXISTS vendor_metric_events_conversation_idx
  ON vendor_metric_events(conversation_id)
  WHERE conversation_id IS NOT NULL;
