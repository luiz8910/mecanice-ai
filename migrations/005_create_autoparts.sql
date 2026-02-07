-- AutoParts table (english version)
CREATE TABLE IF NOT EXISTS autoparts (
  id bigserial PRIMARY KEY,
  name text NOT NULL,
  whatsapp_phone_e164 text NOT NULL UNIQUE,
  address text NULL,
  city text NOT NULL,
  state_uf char(2) NOT NULL,
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','paused')),
  opening_hours text NULL,
  delivery_types text[] NOT NULL DEFAULT '{}',
  radius_km double precision NULL,
  categories text[] NOT NULL DEFAULT '{}',
  responsible_name text NULL,
  notes text NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS autoparts_status_idx ON autoparts(status);
CREATE INDEX IF NOT EXISTS autoparts_city_uf_idx ON autoparts(city, state_uf);
