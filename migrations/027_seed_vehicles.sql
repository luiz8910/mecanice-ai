-- Seed Brazilian fleet vehicles (models up to 20 years old, 2006-2026).
-- Idempotent: skips rows already present (matched by manufacturer + model + model_year_start).

WITH mfr AS (
    SELECT id, name FROM manufacturers WHERE soft_delete = false
),
new_vehicles(manufacturer_name, model, model_year_start, model_year_end, body_type, fuel_type, engine_displacement) AS (
    VALUES
    -- ── Volkswagen ────────────────────────────────────────────────────
    ('Volkswagen'::text, 'Gol'::text,        2008::int, 2022::int, 'hatchback'::text, 'flex'::text,     '1.0'::text),
    ('Volkswagen',       'Fox',              2006, 2017, 'hatchback', 'flex',     '1.0'),
    ('Volkswagen',       'CrossFox',         2005, 2015, 'hatchback', 'flex',     '1.6'),
    ('Volkswagen',       'Polo Hatch',       2002, 2014, 'hatchback', 'flex',     '1.6'),
    ('Volkswagen',       'Polo Sedan',       2002, 2014, 'sedan',     'flex',     '1.6'),
    ('Volkswagen',       'Polo',             2018, NULL, 'hatchback', 'flex',     '1.0 TSI'),
    ('Volkswagen',       'Golf',             2013, 2020, 'hatchback', 'flex',     '1.4 TSI'),
    ('Volkswagen',       'Jetta',            2006, 2021, 'sedan',     'flex',     '2.0'),
    ('Volkswagen',       'Virtus',           2018, NULL, 'sedan',     'flex',     '1.6'),
    ('Volkswagen',       'Voyage',           2009, 2022, 'sedan',     'flex',     '1.0'),
    ('Volkswagen',       'Saveiro',          2010, NULL, 'pickup',    'flex',     '1.6'),
    ('Volkswagen',       'Spacefox',         2006, 2013, 'hatchback', 'flex',     '1.6'),
    ('Volkswagen',       'Up',               2014, 2021, 'hatchback', 'flex',     '1.0'),
    ('Volkswagen',       'Amarok',           2011, NULL, 'pickup',    'diesel',   '2.0 TDI'),
    ('Volkswagen',       'Tiguan',           2009, NULL, 'suv',       'gasoline', '2.0 TSI'),
    ('Volkswagen',       'T-Cross',          2019, NULL, 'suv',       'flex',     '1.0 TSI'),
    ('Volkswagen',       'Nivus',            2020, NULL, 'suv',       'flex',     '1.0 TSI'),
    ('Volkswagen',       'Taos',             2021, NULL, 'suv',       'flex',     '1.4 TSI'),

    -- ── Fiat ─────────────────────────────────────────────────────────
    ('Fiat', 'Palio',       2004, 2018, 'hatchback', 'flex',     '1.0'),
    ('Fiat', 'Uno',         2010, NULL, 'hatchback', 'flex',     '1.0'),
    ('Fiat', 'Punto',       2007, 2017, 'hatchback', 'flex',     '1.4'),
    ('Fiat', 'Bravo',       2010, 2014, 'hatchback', 'flex',     '1.8'),
    ('Fiat', 'Linea',       2008, 2016, 'sedan',     'flex',     '1.8'),
    ('Fiat', 'Siena',       2008, 2016, 'sedan',     'flex',     '1.0'),
    ('Fiat', 'Grand Siena', 2012, 2020, 'sedan',     'flex',     '1.4'),
    ('Fiat', 'Idea',        2005, 2016, 'hatchback', 'flex',     '1.4'),
    ('Fiat', 'Doblo',       2001, 2017, 'minivan',   'flex',     '1.8'),
    ('Fiat', 'Strada',      2004, NULL, 'pickup',    'flex',     '1.3'),
    ('Fiat', 'Toro',        2016, NULL, 'pickup',    'flex',     '1.8'),
    ('Fiat', 'Mobi',        2016, NULL, 'hatchback', 'flex',     '1.0'),
    ('Fiat', 'Argo',        2017, NULL, 'hatchback', 'flex',     '1.0'),
    ('Fiat', 'Cronos',      2018, NULL, 'sedan',     'flex',     '1.3'),
    ('Fiat', 'Pulse',       2021, NULL, 'suv',       'flex',     '1.0 Turbo'),
    ('Fiat', 'Fastback',    2022, NULL, 'suv',       'flex',     '1.0 Turbo'),
    ('Fiat', 'Freemont',    2011, 2016, 'suv',       'flex',     '2.4'),
    ('Fiat', '500',         2012, 2017, 'hatchback', 'gasoline', '1.4'),
    ('Fiat', 'Ducato',      2006, NULL, 'van',       'diesel',   '2.3'),

    -- ── Chevrolet ────────────────────────────────────────────────────
    ('Chevrolet', 'Celta',       2001, 2016, 'hatchback', 'flex',     '1.0'),
    ('Chevrolet', 'Classic',     2002, 2016, 'sedan',     'flex',     '1.0'),
    ('Chevrolet', 'Corsa Sedan', 2006, 2012, 'sedan',     'flex',     '1.4'),
    ('Chevrolet', 'Astra',       2002, 2011, 'hatchback', 'flex',     '2.0'),
    ('Chevrolet', 'Vectra',      2006, 2011, 'sedan',     'flex',     '2.0'),
    ('Chevrolet', 'Zafira',      2001, 2012, 'minivan',   'flex',     '2.0'),
    ('Chevrolet', 'Montana',     2003, 2022, 'pickup',    'flex',     '1.4'),
    ('Chevrolet', 'S10',         2006, NULL, 'pickup',    'diesel',   '2.8'),
    ('Chevrolet', 'Captiva',     2008, 2016, 'suv',       'flex',     '2.4'),
    ('Chevrolet', 'Spin',        2012, NULL, 'minivan',   'flex',     '1.8'),
    ('Chevrolet', 'Cobalt',      2011, 2021, 'sedan',     'flex',     '1.8'),
    ('Chevrolet', 'Prisma',      2013, 2020, 'sedan',     'flex',     '1.4'),
    ('Chevrolet', 'Onix',        2012, NULL, 'hatchback', 'flex',     '1.0 Turbo'),
    ('Chevrolet', 'Onix Plus',   2019, NULL, 'sedan',     'flex',     '1.0 Turbo'),
    ('Chevrolet', 'Tracker',     2013, NULL, 'suv',       'flex',     '1.2 Turbo'),
    ('Chevrolet', 'Equinox',     2018, NULL, 'suv',       'flex',     '2.0 Turbo'),
    ('Chevrolet', 'Trailblazer', 2012, NULL, 'suv',       'diesel',   '2.8'),
    ('Chevrolet', 'Cruze',       2012, NULL, 'sedan',     'flex',     '1.4 Turbo'),
    ('Chevrolet', 'Camaro',      2011, NULL, 'coupe',     'gasoline', '6.2'),
    ('Chevrolet', 'Silverado',   2006, NULL, 'pickup',    'diesel',   '6.0'),

    -- ── Ford ─────────────────────────────────────────────────────────
    ('Ford', 'Ka',          2002, 2021, 'hatchback', 'flex',     '1.0'),
    ('Ford', 'Ka Sedan',    2014, 2021, 'sedan',     'flex',     '1.0'),
    ('Ford', 'Fiesta',      2006, 2014, 'hatchback', 'flex',     '1.6'),
    ('Ford', 'Focus',       2009, 2019, 'sedan',     'flex',     '2.0'),
    ('Ford', 'EcoSport',    2003, 2022, 'suv',       'flex',     '2.0'),
    ('Ford', 'Ranger',      2006, NULL, 'pickup',    'diesel',   '3.2'),
    ('Ford', 'Fusion',      2006, 2019, 'sedan',     'flex',     '2.5'),
    ('Ford', 'Edge',        2011, 2020, 'suv',       'gasoline', '2.0 Turbo'),
    ('Ford', 'Territory',   2020, NULL, 'suv',       'gasoline', '1.5 Turbo'),
    ('Ford', 'Bronco Sport',2021, NULL, 'suv',       'flex',     '1.5 Turbo'),
    ('Ford', 'Maverick',    2022, NULL, 'pickup',    'hybrid',   '2.5'),
    ('Ford', 'Bronco',      2022, NULL, 'suv',       'gasoline', '2.7 Biturbo'),
    ('Ford', 'F-250',       2006, NULL, 'pickup',    'diesel',   '6.7'),

    -- ── Toyota ───────────────────────────────────────────────────────
    ('Toyota', 'Corolla',       2006, NULL, 'sedan',     'flex',     '2.0'),
    ('Toyota', 'Camry',         2012, NULL, 'sedan',     'hybrid',   '2.5'),
    ('Toyota', 'Hilux',         2005, NULL, 'pickup',    'diesel',   '2.8'),
    ('Toyota', 'SW4',           2006, NULL, 'suv',       'diesel',   '2.8'),
    ('Toyota', 'RAV4',          2009, NULL, 'suv',       'flex',     '2.0'),
    ('Toyota', 'Yaris Hatch',   2018, NULL, 'hatchback', 'flex',     '1.5'),
    ('Toyota', 'Yaris Sedan',   2018, NULL, 'sedan',     'flex',     '1.5'),
    ('Toyota', 'Etios Hatch',   2012, 2023, 'hatchback', 'flex',     '1.3'),
    ('Toyota', 'Etios Sedan',   2012, 2023, 'sedan',     'flex',     '1.5'),
    ('Toyota', 'Prius',         2013, NULL, 'sedan',     'hybrid',   '1.8'),
    ('Toyota', 'Fortuner',      2016, NULL, 'suv',       'diesel',   '2.7'),
    ('Toyota', 'Land Cruiser Prado', 2006, NULL, 'suv',  'diesel',   '4.0'),
    ('Toyota', 'C-HR',          2020, NULL, 'suv',       'hybrid',   '2.0'),
    ('Toyota', 'Corolla Cross',  2021, NULL, 'suv',       'hybrid',   '2.0'),

    -- ── Honda ────────────────────────────────────────────────────────
    ('Honda', 'Fit',     2008, NULL, 'hatchback', 'flex',     '1.5'),
    ('Honda', 'City',    2009, NULL, 'sedan',     'flex',     '1.5'),
    ('Honda', 'Civic',   2006, NULL, 'sedan',     'flex',     '2.0'),
    ('Honda', 'Accord',  2008, 2014, 'sedan',     'flex',     '3.5'),
    ('Honda', 'CR-V',    2007, NULL, 'suv',       'flex',     '2.0'),
    ('Honda', 'HR-V',    2015, NULL, 'suv',       'flex',     '1.8'),
    ('Honda', 'WR-V',    2017, NULL, 'suv',       'flex',     '1.5'),

    -- ── Hyundai ──────────────────────────────────────────────────────
    ('Hyundai', 'HB20',        2012, NULL, 'hatchback', 'flex',     '1.0 Turbo'),
    ('Hyundai', 'HB20S',       2013, NULL, 'sedan',     'flex',     '1.0 Turbo'),
    ('Hyundai', 'HB20X',       2013, NULL, 'suv',       'flex',     '1.6'),
    ('Hyundai', 'Tucson',      2006, NULL, 'suv',       'flex',     '1.6 Turbo'),
    ('Hyundai', 'ix35',        2010, 2018, 'suv',       'flex',     '2.0'),
    ('Hyundai', 'Santa Fe',    2007, NULL, 'suv',       'flex',     '3.3'),
    ('Hyundai', 'Creta',       2016, NULL, 'suv',       'flex',     '1.0 Turbo'),
    ('Hyundai', 'Elantra',     2007, NULL, 'sedan',     'flex',     '2.0'),
    ('Hyundai', 'i30',         2008, 2012, 'hatchback', 'flex',     '2.0'),

    -- ── Renault ──────────────────────────────────────────────────────
    ('Renault', 'Clio',    2006, 2016, 'hatchback', 'flex',     '1.0'),
    ('Renault', 'Sandero', 2008, NULL, 'hatchback', 'flex',     '1.0 Turbo'),
    ('Renault', 'Logan',   2007, NULL, 'sedan',     'flex',     '1.0 Turbo'),
    ('Renault', 'Megane',  2007, 2017, 'hatchback', 'flex',     '2.0'),
    ('Renault', 'Symbol',  2009, 2012, 'sedan',     'flex',     '1.6'),
    ('Renault', 'Fluence', 2012, 2016, 'sedan',     'flex',     '2.0'),
    ('Renault', 'Duster',  2012, NULL, 'suv',       'flex',     '1.3 Turbo'),
    ('Renault', 'Oroch',   2016, NULL, 'pickup',    'flex',     '1.3 Turbo'),
    ('Renault', 'Kwid',    2017, NULL, 'hatchback', 'flex',     '1.0'),
    ('Renault', 'Captur',  2017, NULL, 'suv',       'flex',     '1.3 Turbo'),
    ('Renault', 'Stepway', 2014, NULL, 'hatchback', 'flex',     '1.0 Turbo'),

    -- ── Jeep ─────────────────────────────────────────────────────────
    ('Jeep', 'Wrangler',       2006, NULL, 'suv', 'gasoline', '3.6'),
    ('Jeep', 'Grand Cherokee', 2006, NULL, 'suv', 'gasoline', '3.6'),
    ('Jeep', 'Cherokee',       2014, NULL, 'suv', 'gasoline', '2.0'),
    ('Jeep', 'Renegade',       2015, NULL, 'suv', 'flex',     '1.3 Turbo'),
    ('Jeep', 'Compass',        2017, NULL, 'suv', 'diesel',   '2.0'),
    ('Jeep', 'Commander',      2021, NULL, 'suv', 'diesel',   '2.0'),

    -- ── Nissan ───────────────────────────────────────────────────────
    ('Nissan', 'March',    2011, 2020, 'hatchback', 'flex',     '1.0'),
    ('Nissan', 'Versa',    2011, NULL, 'sedan',     'flex',     '1.0 Turbo'),
    ('Nissan', 'Tiida',    2007, 2014, 'hatchback', 'flex',     '1.8'),
    ('Nissan', 'Livina',   2009, 2018, 'minivan',   'flex',     '1.6'),
    ('Nissan', 'Sentra',   2008, 2019, 'sedan',     'flex',     '2.0'),
    ('Nissan', 'Frontier', 2008, NULL, 'pickup',    'diesel',   '2.5'),
    ('Nissan', 'Kicks',    2016, NULL, 'suv',       'flex',     '1.6'),
    ('Nissan', 'X-Trail',  2010, 2014, 'suv',       'flex',     '2.5'),
    ('Nissan', 'Leaf',     2018, NULL, 'hatchback', 'electric', NULL),

    -- ── Peugeot ──────────────────────────────────────────────────────
    ('Peugeot', '207',   2006, 2014, 'hatchback', 'flex',     '1.4'),
    ('Peugeot', '307',   2006, 2010, 'hatchback', 'flex',     '1.6'),
    ('Peugeot', '308',   2011, 2015, 'hatchback', 'flex',     '1.6'),
    ('Peugeot', '408',   2012, 2016, 'sedan',     'flex',     '2.0'),
    ('Peugeot', '2008',  2014, NULL, 'suv',       'flex',     '1.6 Turbo'),
    ('Peugeot', '3008',  2010, NULL, 'suv',       'gasoline', '1.6 Turbo'),
    ('Peugeot', '5008',  2010, NULL, 'suv',       'gasoline', '2.0 Turbo'),
    ('Peugeot', '208',   2019, NULL, 'hatchback', 'flex',     '1.2 Turbo'),

    -- ── Citroën ──────────────────────────────────────────────────────
    ('Citroën', 'C3',          2006, NULL, 'hatchback', 'flex',     '1.5 Turbo'),
    ('Citroën', 'C4 Hatch',    2006, 2011, 'hatchback', 'flex',     '1.6'),
    ('Citroën', 'C4 Lounge',   2012, 2021, 'sedan',     'flex',     '1.6 Turbo'),
    ('Citroën', 'C4 Cactus',   2019, NULL, 'hatchback', 'flex',     '1.6 Turbo'),
    ('Citroën', 'Aircross',    2010, 2019, 'suv',       'flex',     '1.6'),
    ('Citroën', 'C3 Aircross', 2018, NULL, 'suv',       'flex',     '1.6 Turbo'),
    ('Citroën', 'C5',          2007, 2012, 'sedan',     'flex',     '2.0'),
    ('Citroën', 'Jumper',      2006, NULL, 'van',       'diesel',   '2.2'),

    -- ── Mitsubishi ───────────────────────────────────────────────────
    ('Mitsubishi', 'L200 Triton',   2008, NULL, 'pickup',    'diesel',   '2.4'),
    ('Mitsubishi', 'Pajero TR4',    2007, 2019, 'suv',       'flex',     '2.0'),
    ('Mitsubishi', 'Pajero Dakar',  2010, 2018, 'suv',       'diesel',   '3.2'),
    ('Mitsubishi', 'Pajero Sport',  2016, NULL, 'suv',       'diesel',   '2.4'),
    ('Mitsubishi', 'Outlander',     2012, NULL, 'suv',       'gasoline', '2.0'),
    ('Mitsubishi', 'Eclipse Cross', 2018, NULL, 'suv',       'gasoline', '1.5 Turbo'),
    ('Mitsubishi', 'ASX',          2010, 2019, 'suv',       'flex',     '2.0'),
    ('Mitsubishi', 'Lancer',        2009, 2016, 'sedan',     'flex',     '2.0'),

    -- ── Kia ──────────────────────────────────────────────────────────
    ('Kia', 'Cerato',   2010, 2018, 'sedan',   'flex',     '1.6'),
    ('Kia', 'Sportage', 2010, NULL, 'suv',     'flex',     '2.0'),
    ('Kia', 'Sorento',  2010, NULL, 'suv',     'flex',     '3.3'),
    ('Kia', 'Soul',     2010, 2018, 'hatchback','flex',    '2.0'),
    ('Kia', 'Stinger',  2018, NULL, 'sedan',   'gasoline', '3.3 Biturbo'),
    ('Kia', 'Carnival', 2021, NULL, 'minivan', 'gasoline', '3.5'),
    ('Kia', 'Seltos',   2022, NULL, 'suv',     'flex',     '1.6 Turbo'),
    ('Kia', 'EV6',      2022, NULL, 'suv',     'electric', NULL),

    -- ── BMW ──────────────────────────────────────────────────────────
    ('BMW', 'Series 1', 2006, NULL, 'hatchback', 'gasoline', '1.5 Turbo'),
    ('BMW', 'Series 3', 2006, NULL, 'sedan',     'gasoline', '2.0 Turbo'),
    ('BMW', 'Series 4', 2014, NULL, 'coupe',     'gasoline', '2.0 Turbo'),
    ('BMW', 'Series 5', 2006, NULL, 'sedan',     'gasoline', '2.0 Turbo'),
    ('BMW', 'X1',       2010, NULL, 'suv',       'gasoline', '2.0 Turbo'),
    ('BMW', 'X3',       2006, NULL, 'suv',       'gasoline', '2.0 Turbo'),
    ('BMW', 'X5',       2006, NULL, 'suv',       'diesel',   '3.0 Turbo'),
    ('BMW', 'X6',       2008, NULL, 'suv',       'gasoline', '3.0 Biturbo'),

    -- ── Mercedes-Benz ────────────────────────────────────────────────
    ('Mercedes-Benz', 'Classe A',  2013, NULL, 'hatchback', 'gasoline', '1.3 Turbo'),
    ('Mercedes-Benz', 'Classe B',  2012, NULL, 'hatchback', 'gasoline', '1.6 Turbo'),
    ('Mercedes-Benz', 'Classe C',  2008, NULL, 'sedan',     'gasoline', '2.0 Turbo'),
    ('Mercedes-Benz', 'Classe E',  2010, NULL, 'sedan',     'gasoline', '2.0 Turbo'),
    ('Mercedes-Benz', 'GLA',       2015, NULL, 'suv',       'gasoline', '1.3 Turbo'),
    ('Mercedes-Benz', 'GLC',       2016, NULL, 'suv',       'diesel',   '2.0 Turbo'),
    ('Mercedes-Benz', 'GLE',       2016, NULL, 'suv',       'gasoline', '3.0 Biturbo'),
    ('Mercedes-Benz', 'Sprinter',  2006, NULL, 'van',       'diesel',   '2.1'),

    -- ── Audi ─────────────────────────────────────────────────────────
    ('Audi', 'A1', 2011, NULL, 'hatchback', 'gasoline', '1.4 TFSI'),
    ('Audi', 'A3', 2007, NULL, 'hatchback', 'flex',     '1.4 TFSI'),
    ('Audi', 'A4', 2006, NULL, 'sedan',     'gasoline', '2.0 TFSI'),
    ('Audi', 'A5', 2009, NULL, 'coupe',     'gasoline', '2.0 TFSI'),
    ('Audi', 'A6', 2012, NULL, 'sedan',     'gasoline', '3.0 TFSI'),
    ('Audi', 'Q3', 2012, NULL, 'suv',       'flex',     '1.4 TFSI'),
    ('Audi', 'Q5', 2009, NULL, 'suv',       'gasoline', '2.0 TFSI'),
    ('Audi', 'Q7', 2007, NULL, 'suv',       'gasoline', '3.0 TFSI'),

    -- ── Land Rover ───────────────────────────────────────────────────
    ('Land Rover', 'Range Rover Evoque',  2012, NULL, 'suv', 'gasoline', '2.0 Turbo'),
    ('Land Rover', 'Discovery Sport',     2015, NULL, 'suv', 'diesel',   '2.0 Turbo'),
    ('Land Rover', 'Range Rover Sport',   2006, NULL, 'suv', 'diesel',   '3.0 Turbo'),
    ('Land Rover', 'Discovery',           2010, NULL, 'suv', 'diesel',   '3.0 Turbo'),
    ('Land Rover', 'Defender',            2020, NULL, 'suv', 'diesel',   '2.0 Turbo'),

    -- ── Volvo ────────────────────────────────────────────────────────
    ('Volvo', 'XC60', 2010, NULL, 'suv',       'gasoline', '2.0 Turbo'),
    ('Volvo', 'XC90', 2006, NULL, 'suv',       'gasoline', '2.0 Turbo'),
    ('Volvo', 'S60',  2011, NULL, 'sedan',     'gasoline', '2.0 Turbo'),
    ('Volvo', 'V40',  2012, 2020, 'hatchback', 'gasoline', '2.0 Turbo'),

    -- ── Subaru ───────────────────────────────────────────────────────
    ('Subaru', 'Impreza',  2008, NULL, 'hatchback', 'gasoline', '2.0'),
    ('Subaru', 'Outback',  2010, NULL, 'wagon',     'gasoline', '2.5'),
    ('Subaru', 'Forester', 2010, NULL, 'suv',       'gasoline', '2.5'),

    -- ── Caoa Chery ───────────────────────────────────────────────────
    ('Caoa Chery', 'Celer',     2012, 2019, 'hatchback', 'flex',     '1.5'),
    ('Caoa Chery', 'QQ',        2012, 2019, 'hatchback', 'gasoline', '1.0'),
    ('Caoa Chery', 'Tiggo 5X',  2019, NULL, 'suv',       'flex',     '1.5 Turbo'),
    ('Caoa Chery', 'Tiggo 7 Pro',2021, NULL, 'suv',      'flex',     '1.5 Turbo'),
    ('Caoa Chery', 'Tiggo 8 Pro',2021, NULL, 'suv',      'flex',     '1.5 Turbo'),

    -- ── BYD ──────────────────────────────────────────────────────────
    ('BYD', 'Han',      2022, NULL, 'sedan',     'electric', NULL),
    ('BYD', 'Atto 3',   2023, NULL, 'suv',       'electric', NULL),
    ('BYD', 'Dolphin',  2023, NULL, 'hatchback', 'electric', NULL),
    ('BYD', 'Seal',     2023, NULL, 'sedan',     'electric', NULL),
    ('BYD', 'King',     2024, NULL, 'pickup',    'hybrid',   '1.5 Turbo'),

    -- ── RAM ──────────────────────────────────────────────────────────
    ('RAM', '1500',    2019, NULL, 'pickup', 'gasoline', '5.7'),
    ('RAM', '2500',    2011, NULL, 'pickup', 'diesel',   '6.7'),
    ('RAM', 'Rampage', 2023, NULL, 'pickup', 'flex',     '2.0 Turbo'),

    -- ── Troller ──────────────────────────────────────────────────────
    ('Troller', 'T4', 2014, 2021, 'suv', 'diesel', '3.2'),

    -- ── Porsche ──────────────────────────────────────────────────────
    ('Porsche', 'Cayenne', 2007, NULL, 'suv',       'gasoline', '3.6'),
    ('Porsche', 'Macan',   2014, NULL, 'suv',       'gasoline', '2.0 Turbo'),
    ('Porsche', '718',     2016, NULL, 'convertible','gasoline', '2.0 Turbo'),

    -- ── JAC Motors ───────────────────────────────────────────────────
    ('JAC Motors', 'J3',      2011, 2018, 'sedan',   'flex',     '1.5'),
    ('JAC Motors', 'T40',     2018, NULL, 'suv',     'flex',     '1.5'),
    ('JAC Motors', 'T60',     2018, NULL, 'pickup',  'diesel',   '2.0 Turbo'),
    ('JAC Motors', 'iEV 40',  2020, NULL, 'hatchback','electric', NULL),

    -- ── GWM ──────────────────────────────────────────────────────────
    ('GWM', 'Haval H6',  2021, NULL, 'suv', 'gasoline', '1.5 Turbo'),
    ('GWM', 'Ora 03',    2023, NULL, 'hatchback', 'electric', NULL),
    ('GWM', 'Poer',      2022, NULL, 'pickup',    'diesel',   '2.0 Turbo')
)
INSERT INTO vehicles (manufacturer_id, model, model_year_start, model_year_end, body_type, fuel_type, engine_displacement)
SELECT mfr.id,
       nv.model,
       nv.model_year_start,
       nv.model_year_end,
       nv.body_type,
       nv.fuel_type,
       nv.engine_displacement
FROM new_vehicles nv
JOIN mfr ON lower(mfr.name) = lower(nv.manufacturer_name)
WHERE NOT EXISTS (
    SELECT 1
    FROM vehicles v
    WHERE v.manufacturer_id = mfr.id
      AND lower(v.model) = lower(nv.model)
      AND v.model_year_start = nv.model_year_start
      AND v.soft_delete = false
);
