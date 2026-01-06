-- Mechanics / Workshops table (MVP)
CREATE TABLE IF NOT EXISTS mechanics (
  id bigserial PRIMARY KEY,
  name text NOT NULL,
  whatsapp_phone_e164 text NOT NULL UNIQUE,
  city text NOT NULL,
  state_uf char(2) NOT NULL,
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'blocked')),
  address text NULL,
  email text NULL,
  responsible_name text NULL,
  categories text[] NOT NULL DEFAULT '{}',
  notes text NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS mechanics_status_idx ON mechanics(status);
CREATE INDEX IF NOT EXISTS mechanics_city_uf_idx ON mechanics(city, state_uf);
