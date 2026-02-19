-- Create workshops table and enforce mechanic -> workshop relationship (1:N).

CREATE TABLE IF NOT EXISTS workshops (
  id bigserial PRIMARY KEY,
  name text NOT NULL,
  whatsapp_phone_e164 text NOT NULL UNIQUE,
  city text NOT NULL,
  state_uf char(2) NOT NULL,
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'blocked')),
  address text NULL,
  email text NULL,
  notes text NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  soft_delete boolean NOT NULL DEFAULT false
);

CREATE INDEX IF NOT EXISTS workshops_status_idx ON workshops(status);
CREATE INDEX IF NOT EXISTS workshops_city_uf_idx ON workshops(city, state_uf);

-- Ensure at least one workshop exists for legacy rows.
INSERT INTO workshops (id, name, whatsapp_phone_e164, city, state_uf, status)
VALUES (1, 'Workshop Padrão', '+5500000000000', 'N/A', 'SP', 'active')
ON CONFLICT (id) DO NOTHING;

-- Align mechanics.workshop_id type and constraints.
ALTER TABLE IF EXISTS mechanics
  ALTER COLUMN workshop_id TYPE bigint USING workshop_id::bigint;

ALTER TABLE IF EXISTS mechanics
  ALTER COLUMN workshop_id DROP DEFAULT;

UPDATE mechanics
SET workshop_id = 1
WHERE workshop_id IS NULL;

ALTER TABLE IF EXISTS mechanics
  ALTER COLUMN workshop_id SET NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'mechanics_workshop_id_fk'
  ) THEN
    ALTER TABLE mechanics
      ADD CONSTRAINT mechanics_workshop_id_fk
      FOREIGN KEY (workshop_id)
      REFERENCES workshops(id)
      ON UPDATE RESTRICT
      ON DELETE RESTRICT;
  END IF;
END
$$;

CREATE INDEX IF NOT EXISTS mechanics_workshop_id_idx ON mechanics(workshop_id);
