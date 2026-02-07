-- Seed sample autoparts
INSERT INTO autoparts (name, whatsapp_phone_e164, address, city, state_uf, status, opening_hours, delivery_types, radius_km, categories, responsible_name, notes)
VALUES
  ('Auto Parts Central', '+5511999000111', 'Rua A, 123', 'São Paulo', 'SP', 'active', '08:00-18:00', '{pickup,delivery}', 30.0, '{brakes,lighting}', 'João', 'Central store - large stock')
ON CONFLICT (whatsapp_phone_e164) DO NOTHING;
