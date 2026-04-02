-- Add brand support and soft delete to catalog management

-- Add brand and is_active columns to catalog_documents
ALTER TABLE catalog_documents
  ADD COLUMN brand VARCHAR(100) NULL,
  ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT true;

-- Add brand column to rag_chunks for fast filtering
ALTER TABLE rag_chunks
  ADD COLUMN brand VARCHAR(100) NULL;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS catalog_documents_brand_idx
  ON catalog_documents(brand);

CREATE INDEX IF NOT EXISTS catalog_documents_is_active_idx
  ON catalog_documents(is_active)
  WHERE is_active = true;

CREATE INDEX IF NOT EXISTS rag_chunks_brand_idx
  ON rag_chunks(brand)
  WHERE source_type = 'catalog';

-- Composite index for common filtered queries
CREATE INDEX IF NOT EXISTS catalog_documents_active_brand_idx
  ON catalog_documents(is_active, brand)
  WHERE is_active = true;
