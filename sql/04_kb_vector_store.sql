-- =====================================================================
-- Operation Tangerine - 04 Bedrock Knowledge Base vector store (Lab 2.5)
--
-- Bedrock Knowledge Bases expects a table with (at least) these columns:
--   id        uuid PRIMARY KEY   -> "primary key field"
--   embedding vector(N)          -> "vector field"  (N must match the embedding model!)
--   chunks    text               -> "text field"
--   metadata  json               -> "Bedrock-managed metadata field"
--   custom_metadata jsonb        -> optional, for metadata filtering
-- plus an HNSW index on embedding and a GIN text index on chunks.
--
-- {{KB_USER_PASSWORD}} is filled in by labctl from the bedrock-user secret.
-- In the Query Editor, paste the password from:
--   aws secretsmanager get-secret-value --secret-id <kb_user_secret_arn> \
--       --query SecretString --output text
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS bedrock_integration;

CREATE ROLE bedrock_user WITH LOGIN PASSWORD '{{KB_USER_PASSWORD}}';

GRANT USAGE, CREATE ON SCHEMA bedrock_integration TO bedrock_user;

CREATE TABLE IF NOT EXISTS bedrock_integration.bedrock_kb (
    id               uuid PRIMARY KEY,
    embedding        vector(1024),
    chunks           text,
    metadata         json,
    custom_metadata  jsonb
);

GRANT SELECT, INSERT, UPDATE, DELETE ON bedrock_integration.bedrock_kb TO bedrock_user;

CREATE INDEX IF NOT EXISTS bedrock_kb_embedding_hnsw
    ON bedrock_integration.bedrock_kb USING hnsw (embedding vector_cosine_ops)
    WITH (ef_construction = 256);

CREATE INDEX IF NOT EXISTS bedrock_kb_chunks_fts
    ON bedrock_integration.bedrock_kb USING gin (to_tsvector('simple', chunks));

CREATE INDEX IF NOT EXISTS bedrock_kb_custom_metadata
    ON bedrock_integration.bedrock_kb USING gin (custom_metadata);
