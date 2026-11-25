-- =====================================================================
-- Operation Tangerine - 01 schema
-- Run with:  python3 labctl/labctl.py db-setup schema
-- Or paste into the RDS Query Editor (Database: agentdb, admin secret).
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS vector;

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS customers (
    customer_id     text PRIMARY KEY,
    full_name       text NOT NULL,
    email           text,
    segment         text NOT NULL,          -- enterprise | smb | consumer | startup
    region          text NOT NULL,          -- us-east | us-west | eu | apac | latam
    lifetime_value  numeric(12,2) NOT NULL DEFAULT 0,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS products (
    product_id   bigint PRIMARY KEY,
    sku          text UNIQUE NOT NULL,
    name         text NOT NULL,
    category     text NOT NULL,
    brand        text NOT NULL,
    price        numeric(10,2) NOT NULL,
    rating       numeric(2,1) NOT NULL,
    stock        integer NOT NULL,
    description  text NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    order_id     bigint PRIMARY KEY,
    customer_id  text NOT NULL REFERENCES customers (customer_id),
    product_id   bigint NOT NULL REFERENCES products (product_id),
    quantity     integer NOT NULL,
    amount       numeric(12,2) NOT NULL DEFAULT 0,
    status       text NOT NULL,             -- processing | shipped | delivered | returned
    ordered_at   timestamptz NOT NULL
);

-- Semantic memory: past support notes with Titan V2 embeddings (1024 dims).
CREATE TABLE IF NOT EXISTS support_notes (
    note_id      bigserial PRIMARY KEY,
    customer_id  text REFERENCES customers (customer_id),
    note         text NOT NULL,
    embedding    vector(1024),
    created_at   timestamptz NOT NULL DEFAULT now()
);
