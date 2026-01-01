-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Basic RAG chunk table
CREATE TABLE IF NOT EXISTS rag_chunks (
  id bigserial PRIMARY KEY,
  source_id text NOT NULL,
  source_type text NOT NULL,
  chunk_text text NOT NULL,
  embedding vector(1536),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Index for vector search (cosine)
-- Note: ivfflat requires ANALYZE and enough rows to be effective.
CREATE INDEX IF NOT EXISTS rag_chunks_embedding_idx
  ON rag_chunks
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Helpful btree index for filtering
CREATE INDEX IF NOT EXISTS rag_chunks_source_id_idx ON rag_chunks(source_id);
