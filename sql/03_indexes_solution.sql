-- =====================================================================
-- Operation Tangerine - 03 product-search indexes  (SPOILER: Lab 3.6)
--
-- The agent's product search is:
--   SELECT ... FROM products
--   WHERE name ILIKE '%' || :q || '%' [AND category = :category]
--   ORDER BY rating DESC, product_id LIMIT :lim
--
-- A b-tree can't serve a leading-wildcard ILIKE. A pg_trgm GIN index can.
-- A composite (category, rating DESC) b-tree serves the filter + sort + LIMIT.
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_products_name_trgm
    ON products USING gin (name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_products_category_rating
    ON products (category, rating DESC, product_id);

CREATE INDEX IF NOT EXISTS idx_orders_customer_ordered
    ON orders (customer_id, ordered_at DESC);

ANALYZE products;

ANALYZE orders;
