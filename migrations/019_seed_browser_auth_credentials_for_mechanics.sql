-- Seed browser auth credentials for active mechanics.
-- Default password for seeded accounts: secret123
-- Email pattern: mecanico+<mechanic_id>@mecanice.local

INSERT INTO browser_auth_credentials (
  role,
  actor_id,
  email,
  password_hash,
  active
)
SELECT
  'mechanic',
  m.id,
  'mecanico+' || m.id::text || '@mecanice.local',
  '$2b$12$gqK2nhhsQp4LYx3OvUjRWuqERjGfUdIOgY7p4/S6sJ7x1IGVAhX.y',
  true
FROM mechanics m
WHERE m.soft_delete = false
  AND m.status = 'active'
  AND NOT EXISTS (
    SELECT 1
    FROM browser_auth_credentials bac
    WHERE bac.role = 'mechanic'
      AND bac.actor_id = m.id
      AND bac.active = true
  )
  AND NOT EXISTS (
    SELECT 1
    FROM browser_auth_credentials bac
    WHERE LOWER(bac.email) = LOWER('mecanico+' || m.id::text || '@mecanice.local')
      AND bac.active = true
  )
  AND NOT EXISTS (
    SELECT 1
    FROM seller_credentials sc
    WHERE LOWER(sc.email) = LOWER('mecanico+' || m.id::text || '@mecanice.local')
      AND sc.active = true
  );
