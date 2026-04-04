-- Create vehicles reference table (frota brasileira).
CREATE TABLE IF NOT EXISTS vehicles (
    id                   bigserial PRIMARY KEY,
    manufacturer_id      bigint    NOT NULL REFERENCES manufacturers(id),
    model                text      NOT NULL,
    model_year_start     int       NOT NULL CHECK (model_year_start BETWEEN 1900 AND 2100),
    model_year_end       int                CHECK (
                             model_year_end IS NULL
                             OR (model_year_end >= model_year_start AND model_year_end <= 2100)
                         ),
    body_type            text      NOT NULL CHECK (body_type IN (
                             'hatchback', 'sedan', 'pickup', 'suv',
                             'minivan', 'coupe', 'van', 'wagon', 'convertible'
                         )),
    fuel_type            text      NOT NULL DEFAULT 'flex' CHECK (fuel_type IN (
                             'flex', 'gasoline', 'diesel', 'hybrid', 'electric', 'cng'
                         )),
    engine_displacement  text,
    soft_delete          boolean   NOT NULL DEFAULT false,
    created_at           timestamptz NOT NULL DEFAULT now(),
    updated_at           timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS vehicles_manufacturer_idx ON vehicles(manufacturer_id);
CREATE INDEX IF NOT EXISTS vehicles_model_idx        ON vehicles(lower(model));
CREATE INDEX IF NOT EXISTS vehicles_year_range_idx   ON vehicles(model_year_start, model_year_end);
CREATE INDEX IF NOT EXISTS vehicles_body_type_idx    ON vehicles(body_type);
CREATE INDEX IF NOT EXISTS vehicles_fuel_type_idx    ON vehicles(fuel_type);
