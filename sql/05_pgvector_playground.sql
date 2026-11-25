-- =====================================================================
-- Operation Tangerine - 05 pgvector playground (Lab 2.3)
-- Tiny 3-dimensional "flavor vectors" so you can see distances by eye.
--   dims = [sweet, sour, bitter]
-- =====================================================================

CREATE TABLE IF NOT EXISTS fruit_vectors (
    fruit   text PRIMARY KEY,
    flavor  vector(3)
);

INSERT INTO fruit_vectors VALUES
    ('tangerine',  '[0.9, 0.4, 0.05]'),
    ('orange',     '[0.8, 0.5, 0.10]'),
    ('lemon',      '[0.2, 0.95, 0.20]'),
    ('lime',       '[0.15, 0.9, 0.30]'),
    ('grapefruit', '[0.4, 0.7, 0.60]'),
    ('mango',      '[0.95, 0.1, 0.02]'),
    ('kale',       '[0.05, 0.1, 0.90]')
ON CONFLICT (fruit) DO NOTHING;

-- L2 (Euclidean) distance  <->
SELECT fruit, flavor <-> '[0.9, 0.4, 0.05]' AS l2_distance
FROM fruit_vectors ORDER BY 2 LIMIT 4;

-- Cosine distance  <=>   (1 - cosine similarity)
SELECT fruit, flavor <=> '[0.9, 0.4, 0.05]' AS cosine_distance
FROM fruit_vectors ORDER BY 2 LIMIT 4;

-- Negative inner product  <#>   (more negative = more similar)
SELECT fruit, flavor <#> '[0.9, 0.4, 0.05]' AS neg_inner_product
FROM fruit_vectors ORDER BY 2 LIMIT 4;
