CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS llm_call_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  requester_id text NULL,
  thread_id text NULL,
  request_id text NULL,
  provider text NOT NULL,
  endpoint text NOT NULL,
  model text NOT NULL,
  status text NOT NULL DEFAULT 'started'
    CHECK (status IN ('started', 'succeeded', 'failed')),
  http_status integer NULL,
  duration_ms integer NULL,
  response_candidate_count integer NULL,
  error_message text NULL,
  vehicle_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  context_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  request_payload_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  parsed_response_json jsonb NULL,
  raw_response_text text NULL,
  metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS llm_call_logs_created_at_idx
  ON llm_call_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS llm_call_logs_status_idx
  ON llm_call_logs(status);
CREATE INDEX IF NOT EXISTS llm_call_logs_requester_id_idx
  ON llm_call_logs(requester_id);
CREATE INDEX IF NOT EXISTS llm_call_logs_thread_id_idx
  ON llm_call_logs(thread_id);

CREATE TABLE IF NOT EXISTS llm_call_log_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  log_id uuid NOT NULL REFERENCES llm_call_logs(id) ON DELETE CASCADE,
  position integer NOT NULL,
  role text NOT NULL,
  content text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS llm_call_log_messages_log_id_idx
  ON llm_call_log_messages(log_id, position);
