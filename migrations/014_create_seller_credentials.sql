-- Seller credentials for Seller Portal login.
-- Idempotent migration.

CREATE TABLE IF NOT EXISTS seller_credentials (
  id bigserial PRIMARY KEY,
  seller_id bigint NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
  autopart_id bigint NOT NULL REFERENCES autoparts(id) ON DELETE CASCADE,
  email text NOT NULL,
  password_hash text NOT NULL,
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Each email must be unique among active credentials.
CREATE UNIQUE INDEX IF NOT EXISTS seller_credentials_email_uniq
  ON seller_credentials(email)
  WHERE active = true;

CREATE INDEX IF NOT EXISTS seller_credentials_seller_id_idx
  ON seller_credentials(seller_id);

CREATE INDEX IF NOT EXISTS seller_credentials_autopart_id_idx
  ON seller_credentials(autopart_id);
