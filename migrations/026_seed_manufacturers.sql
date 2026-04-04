-- Seed Brazilian market manufacturers (montadoras).
-- Idempotent: skips rows that already exist (case-insensitive match).

INSERT INTO manufacturers (name, country_of_origin)
SELECT v.name, v.country_of_origin
FROM (VALUES
    ('Volkswagen',    'Germany'),
    ('Fiat',          'Italy'),
    ('Chevrolet',     'United States'),
    ('Ford',          'United States'),
    ('Toyota',        'Japan'),
    ('Honda',         'Japan'),
    ('Hyundai',       'South Korea'),
    ('Renault',       'France'),
    ('Jeep',          'United States'),
    ('Nissan',        'Japan'),
    ('Peugeot',       'France'),
    ('Citroën',       'France'),
    ('Mitsubishi',    'Japan'),
    ('Kia',           'South Korea'),
    ('BMW',           'Germany'),
    ('Mercedes-Benz', 'Germany'),
    ('Audi',          'Germany'),
    ('Land Rover',    'United Kingdom'),
    ('Volvo',         'Sweden'),
    ('Subaru',        'Japan'),
    ('Caoa Chery',    'China'),
    ('BYD',           'China'),
    ('JAC Motors',    'China'),
    ('GWM',           'China'),
    ('RAM',           'United States'),
    ('Dodge',         'United States'),
    ('Porsche',       'Germany'),
    ('Troller',       'Brazil'),
    ('Agrale',        'Brazil'),
    ('Suzuki',        'Japan')
) AS v(name, country_of_origin)
WHERE NOT EXISTS (
    SELECT 1
    FROM manufacturers m
    WHERE lower(m.name) = lower(v.name)
      AND m.soft_delete = false
);
