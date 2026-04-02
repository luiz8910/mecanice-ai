-- Create manufacturers (montadoras) reference table.
CREATE TABLE IF NOT EXISTS manufacturers (
    id               bigserial PRIMARY KEY,
    name             text      NOT NULL,
    country_of_origin text     NOT NULL,
    soft_delete      boolean   NOT NULL DEFAULT false,
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now()
);

-- Case-insensitive unique name among active records
CREATE UNIQUE INDEX IF NOT EXISTS manufacturers_name_active_uidx
    ON manufacturers(lower(name))
    WHERE soft_delete = false;

CREATE INDEX IF NOT EXISTS manufacturers_country_idx
    ON manufacturers(country_of_origin);
