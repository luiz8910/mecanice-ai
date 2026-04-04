-- Catalog documents: stores metadata about uploaded PDF parts catalogs
CREATE TABLE IF NOT EXISTS catalog_documents (
  id               bigserial PRIMARY KEY,
  manufacturer_id  bigint REFERENCES manufacturers(id) ON DELETE SET NULL,
  original_filename text NOT NULL,
  stored_filename   text NOT NULL,
  file_size_bytes   bigint,
  description       text,
  status            text NOT NULL DEFAULT 'pending',  -- pending | processing | ready | error
  page_count        int,
  chunk_count       int,
  error_message     text,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS catalog_documents_manufacturer_id_idx
  ON catalog_documents(manufacturer_id);

CREATE INDEX IF NOT EXISTS catalog_documents_status_idx
  ON catalog_documents(status);

-- Expression index so filtering rag_chunks by catalog_id is fast
CREATE INDEX IF NOT EXISTS rag_chunks_metadata_catalog_id_idx
  ON rag_chunks ((metadata->>'catalog_id'));
