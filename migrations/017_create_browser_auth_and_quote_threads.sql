-- Browser-first auth credentials and quotation thread workflow tables.
-- Legacy WhatsApp/quotation tables remain untouched.

CREATE TABLE IF NOT EXISTS browser_auth_credentials (
  id bigserial PRIMARY KEY,
  role text NOT NULL CHECK (role IN ('mechanic', 'seller', 'admin')),
  actor_id bigint NULL,
  email text NOT NULL,
  password_hash text NOT NULL,
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS browser_auth_credentials_email_uniq
  ON browser_auth_credentials (LOWER(email))
  WHERE active = true;

CREATE UNIQUE INDEX IF NOT EXISTS browser_auth_credentials_actor_uniq
  ON browser_auth_credentials (role, actor_id)
  WHERE actor_id IS NOT NULL AND active = true;

CREATE TABLE IF NOT EXISTS quote_threads (
  id bigserial PRIMARY KEY,
  mechanic_id bigint NOT NULL REFERENCES mechanics(id) ON DELETE RESTRICT,
  workshop_id bigint NOT NULL REFERENCES workshops(id) ON DELETE RESTRICT,
  status text NOT NULL DEFAULT 'open'
    CHECK (status IN ('open', 'awaiting_seller_response', 'offer_received', 'closed')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  last_message_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS quote_threads_mechanic_id_idx
  ON quote_threads(mechanic_id);
CREATE INDEX IF NOT EXISTS quote_threads_workshop_id_idx
  ON quote_threads(workshop_id);
CREATE INDEX IF NOT EXISTS quote_threads_status_idx
  ON quote_threads(status);
CREATE INDEX IF NOT EXISTS quote_threads_last_message_at_idx
  ON quote_threads(last_message_at DESC);

CREATE TABLE IF NOT EXISTS part_requests (
  id bigserial PRIMARY KEY,
  thread_id bigint NOT NULL REFERENCES quote_threads(id) ON DELETE CASCADE,
  original_description text NOT NULL,
  requested_items_count integer NOT NULL DEFAULT 1 CHECK (requested_items_count > 0),
  part_number text NULL,
  vehicle_plate text NULL,
  vehicle_brand text NULL,
  vehicle_model text NULL,
  vehicle_year text NULL,
  vehicle_engine text NULL,
  vehicle_version text NULL,
  vehicle_notes text NULL,
  status text NOT NULL DEFAULT 'created'
    CHECK (status IN ('created', 'processing', 'ready_for_quote')),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS part_requests_thread_id_uniq
  ON part_requests(thread_id);

CREATE TABLE IF NOT EXISTS thread_messages (
  id bigserial PRIMARY KEY,
  thread_id bigint NOT NULL REFERENCES quote_threads(id) ON DELETE CASCADE,
  sender_role text NOT NULL CHECK (sender_role IN ('mechanic', 'seller', 'admin', 'system')),
  sender_user_ref text NULL,
  type text NOT NULL CHECK (type IN ('text', 'system', 'request_summary', 'offer_notice')),
  body text NOT NULL,
  metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS thread_messages_thread_id_idx
  ON thread_messages(thread_id, created_at, id);

CREATE TABLE IF NOT EXISTS suggested_parts (
  id bigserial PRIMARY KEY,
  thread_id bigint NOT NULL REFERENCES quote_threads(id) ON DELETE CASCADE,
  request_id bigint NOT NULL REFERENCES part_requests(id) ON DELETE CASCADE,
  title text NOT NULL,
  brand text NULL,
  part_number text NULL,
  confidence numeric(5,2) NULL,
  note text NULL,
  metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS suggested_parts_thread_id_idx
  ON suggested_parts(thread_id);
CREATE INDEX IF NOT EXISTS suggested_parts_request_id_idx
  ON suggested_parts(request_id);

CREATE TABLE IF NOT EXISTS seller_offers (
  id bigserial PRIMARY KEY,
  thread_id bigint NOT NULL REFERENCES quote_threads(id) ON DELETE CASCADE,
  seller_id bigint NOT NULL REFERENCES vendors(id) ON DELETE RESTRICT,
  seller_shop_id bigint NOT NULL REFERENCES autoparts(id) ON DELETE RESTRICT,
  status text NOT NULL DEFAULT 'draft'
    CHECK (status IN ('draft', 'submitted', 'cancelled')),
  notes text NULL,
  total_amount numeric(12,2) NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  submitted_at timestamptz NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS seller_offers_thread_seller_uniq
  ON seller_offers(thread_id, seller_id);
CREATE INDEX IF NOT EXISTS seller_offers_thread_id_idx
  ON seller_offers(thread_id);
CREATE INDEX IF NOT EXISTS seller_offers_seller_shop_id_idx
  ON seller_offers(seller_shop_id);

CREATE TABLE IF NOT EXISTS seller_offer_items (
  id bigserial PRIMARY KEY,
  offer_id bigint NOT NULL REFERENCES seller_offers(id) ON DELETE CASCADE,
  source_type text NOT NULL CHECK (source_type IN ('suggested', 'manual')),
  suggested_part_id bigint NULL REFERENCES suggested_parts(id) ON DELETE SET NULL,
  title text NOT NULL,
  brand text NULL,
  part_number text NULL,
  quantity integer NOT NULL DEFAULT 1 CHECK (quantity > 0),
  unit_price numeric(12,2) NULL,
  compatibility_note text NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS seller_offer_items_offer_id_idx
  ON seller_offer_items(offer_id);
