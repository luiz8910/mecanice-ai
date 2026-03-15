-- Backfill seller visibility for existing browser threads.
-- Every active vendor receives a draft offer per thread, making the thread
-- visible in the seller inbox without needing manual assignment.

WITH status_value AS (
  SELECT CASE
    WHEN EXISTS (
      SELECT 1
      FROM pg_constraint
      WHERE conname = 'seller_offers_status_check'
        AND pg_get_constraintdef(oid) LIKE '%DRAFT%'
    ) THEN 'DRAFT'
    ELSE 'draft'
  END AS value
)
INSERT INTO seller_offers (
  thread_id,
  seller_id,
  seller_shop_id,
  status
)
SELECT
  t.id,
  v.id,
  v.autopart_id,
  sv.value
FROM quote_threads t
CROSS JOIN vendors v
CROSS JOIN status_value sv
WHERE v.soft_delete = false
  AND v.active = true
ON CONFLICT (thread_id, seller_id) DO NOTHING;
