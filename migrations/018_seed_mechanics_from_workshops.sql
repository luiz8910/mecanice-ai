-- Seed one mechanic for each active workshop that still has no mechanic.
-- Idempotent: skips workshops that already have active mechanics and avoids
-- duplicate phone numbers on re-runs.

INSERT INTO mechanics (
  name,
  whatsapp_phone_e164,
  city,
  state_uf,
  status,
  email,
  workshop_id,
  categories,
  notes
)
SELECT
  'Mecanico - ' || w.name,
  '+5500001' || LPAD(w.id::text, 6, '0'),
  w.city,
  w.state_uf,
  'active',
  'mecanico+' || w.id::text || '@mecanice.local',
  w.id,
  '{}'::text[],
  'Seed automatico criado a partir da oficina cadastrada'
FROM workshops w
WHERE w.soft_delete = false
  AND w.status = 'active'
  AND NOT EXISTS (
    SELECT 1
    FROM mechanics m
    WHERE m.workshop_id = w.id
      AND m.soft_delete = false
  )
ON CONFLICT (whatsapp_phone_e164) DO NOTHING;
