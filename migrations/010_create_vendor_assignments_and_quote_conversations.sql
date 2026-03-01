-- Vendors, exclusive workshop-store assignments, and WhatsApp conversation tracking.
-- Idempotent migration.

CREATE TABLE IF NOT EXISTS vendors (
  id bigserial PRIMARY KEY,
  autopart_id bigint NOT NULL REFERENCES autoparts(id) ON DELETE CASCADE,
  name text NOT NULL,
  email text NULL,
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS vendors_autopart_id_idx ON vendors(autopart_id);
CREATE INDEX IF NOT EXISTS vendors_active_idx ON vendors(active);
CREATE UNIQUE INDEX IF NOT EXISTS vendors_autopart_email_uniq
  ON vendors(autopart_id, email)
  WHERE email IS NOT NULL;

CREATE TABLE IF NOT EXISTS vendor_assignments (
  id bigserial PRIMARY KEY,
  workshop_id bigint NOT NULL REFERENCES workshops(id) ON DELETE CASCADE,
  autopart_id bigint NOT NULL REFERENCES autoparts(id) ON DELETE CASCADE,
  vendor_id bigint NOT NULL REFERENCES vendors(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (workshop_id, autopart_id)
);

CREATE INDEX IF NOT EXISTS vendor_assignments_vendor_id_idx ON vendor_assignments(vendor_id);

CREATE TABLE IF NOT EXISTS quote_conversations (
  conversation_id text PRIMARY KEY,
  source_event_id text NOT NULL,
  request_id text NOT NULL,
  mechanic_phone_e164 text NOT NULL,
  workshop_id bigint NOT NULL REFERENCES workshops(id) ON DELETE RESTRICT,
  autopart_id bigint NOT NULL REFERENCES autoparts(id) ON DELETE RESTRICT,
  vendor_id bigint NOT NULL REFERENCES vendors(id) ON DELETE RESTRICT,
  last_mechanic_message text NULL,
  status text NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (source_event_id, autopart_id)
);

CREATE INDEX IF NOT EXISTS quote_conversations_request_id_idx ON quote_conversations(request_id);
CREATE INDEX IF NOT EXISTS quote_conversations_vendor_id_idx ON quote_conversations(vendor_id);
CREATE INDEX IF NOT EXISTS quote_conversations_workshop_id_idx ON quote_conversations(workshop_id);