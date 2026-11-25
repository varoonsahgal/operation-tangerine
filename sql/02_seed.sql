-- =====================================================================
-- Operation Tangerine - 02 seed data (deterministic, no external files)
--   5,000 customers | 200,000 products | 100,000 orders
-- Big inserts are split into 50k-row chunks so each Data API call stays well
-- under its 45-second synchronous limit.
-- Run with:  python3 labctl/labctl.py db-setup seed
-- =====================================================================

INSERT INTO customers (customer_id, full_name, email, segment, region, created_at)
SELECT 'C' || lpad(g::text, 5, '0'),
       (ARRAY['Avery','Jordan','Riley','Casey','Morgan','Quinn','Harper','Rowan','Sage','Emery'])[1 + g % 10]
         || ' ' ||
       (ARRAY['Lee','Patel','Garcia','Kim','Nguyen','Okafor','Silva','Cohen','Rossi','Novak','Haddad','Larsen'])[1 + (g * 7) % 12],
       'customer' || g || '@example.com',
       (ARRAY['enterprise','smb','consumer','startup'])[1 + (g * 3) % 4],
       (ARRAY['us-east','us-west','eu','apac','latam'])[1 + (g * 11) % 5],
       now() - make_interval(days => g % 1000)
FROM generate_series(1, 5000) AS g
ON CONFLICT (customer_id) DO NOTHING;

INSERT INTO products (product_id, sku, name, category, brand, price, rating, stock, description)
SELECT g,
       'SKU-' || lpad(g::text, 7, '0'),
       (ARRAY['Ultra','Pro','Eco','Smart','Classic','Turbo','Nano','Max','Zen','Flex'])[1 + g % 10]
         || ' ' ||
       (ARRAY['Blender','Headphones','Backpack','Keyboard','Lamp','Kettle','Monitor','Jacket','Tent','Speaker',
              'Drone','Watch','Mug','Router','Camera','Sneakers','Desk','Chair','Bottle','Charger'])[1 + (g / 10) % 20]
         || ' ' || (g % 997),
       (ARRAY['electronics','kitchen','outdoor','office','apparel','home','audio','fitness'])[1 + (g * 7) % 8],
       (ARRAY['Acme','Globex','Initech','Umbrella','Stark','Wayne','Tyrell','Wonka'])[1 + (g * 13) % 8],
       round((5 + ((g * 37) % 49500) / 100.0)::numeric, 2),
       round((1 + ((g * 17) % 41) / 10.0)::numeric, 1),
       (g * 29) % 500,
       'Citrus & Co. catalog item ' || g || '. Built for everyday use with a '
         || (ARRAY['1-year','2-year','90-day'])[1 + g % 3] || ' warranty.'
FROM generate_series(1, 50000) AS g
ON CONFLICT (product_id) DO NOTHING;

INSERT INTO products (product_id, sku, name, category, brand, price, rating, stock, description)
SELECT g,
       'SKU-' || lpad(g::text, 7, '0'),
       (ARRAY['Ultra','Pro','Eco','Smart','Classic','Turbo','Nano','Max','Zen','Flex'])[1 + g % 10]
         || ' ' ||
       (ARRAY['Blender','Headphones','Backpack','Keyboard','Lamp','Kettle','Monitor','Jacket','Tent','Speaker',
              'Drone','Watch','Mug','Router','Camera','Sneakers','Desk','Chair','Bottle','Charger'])[1 + (g / 10) % 20]
         || ' ' || (g % 997),
       (ARRAY['electronics','kitchen','outdoor','office','apparel','home','audio','fitness'])[1 + (g * 7) % 8],
       (ARRAY['Acme','Globex','Initech','Umbrella','Stark','Wayne','Tyrell','Wonka'])[1 + (g * 13) % 8],
       round((5 + ((g * 37) % 49500) / 100.0)::numeric, 2),
       round((1 + ((g * 17) % 41) / 10.0)::numeric, 1),
       (g * 29) % 500,
       'Citrus & Co. catalog item ' || g || '. Built for everyday use with a '
         || (ARRAY['1-year','2-year','90-day'])[1 + g % 3] || ' warranty.'
FROM generate_series(50001, 100000) AS g
ON CONFLICT (product_id) DO NOTHING;

INSERT INTO products (product_id, sku, name, category, brand, price, rating, stock, description)
SELECT g,
       'SKU-' || lpad(g::text, 7, '0'),
       (ARRAY['Ultra','Pro','Eco','Smart','Classic','Turbo','Nano','Max','Zen','Flex'])[1 + g % 10]
         || ' ' ||
       (ARRAY['Blender','Headphones','Backpack','Keyboard','Lamp','Kettle','Monitor','Jacket','Tent','Speaker',
              'Drone','Watch','Mug','Router','Camera','Sneakers','Desk','Chair','Bottle','Charger'])[1 + (g / 10) % 20]
         || ' ' || (g % 997),
       (ARRAY['electronics','kitchen','outdoor','office','apparel','home','audio','fitness'])[1 + (g * 7) % 8],
       (ARRAY['Acme','Globex','Initech','Umbrella','Stark','Wayne','Tyrell','Wonka'])[1 + (g * 13) % 8],
       round((5 + ((g * 37) % 49500) / 100.0)::numeric, 2),
       round((1 + ((g * 17) % 41) / 10.0)::numeric, 1),
       (g * 29) % 500,
       'Citrus & Co. catalog item ' || g || '. Built for everyday use with a '
         || (ARRAY['1-year','2-year','90-day'])[1 + g % 3] || ' warranty.'
FROM generate_series(100001, 150000) AS g
ON CONFLICT (product_id) DO NOTHING;

INSERT INTO products (product_id, sku, name, category, brand, price, rating, stock, description)
SELECT g,
       'SKU-' || lpad(g::text, 7, '0'),
       (ARRAY['Ultra','Pro','Eco','Smart','Classic','Turbo','Nano','Max','Zen','Flex'])[1 + g % 10]
         || ' ' ||
       (ARRAY['Blender','Headphones','Backpack','Keyboard','Lamp','Kettle','Monitor','Jacket','Tent','Speaker',
              'Drone','Watch','Mug','Router','Camera','Sneakers','Desk','Chair','Bottle','Charger'])[1 + (g / 10) % 20]
         || ' ' || (g % 997),
       (ARRAY['electronics','kitchen','outdoor','office','apparel','home','audio','fitness'])[1 + (g * 7) % 8],
       (ARRAY['Acme','Globex','Initech','Umbrella','Stark','Wayne','Tyrell','Wonka'])[1 + (g * 13) % 8],
       round((5 + ((g * 37) % 49500) / 100.0)::numeric, 2),
       round((1 + ((g * 17) % 41) / 10.0)::numeric, 1),
       (g * 29) % 500,
       'Citrus & Co. catalog item ' || g || '. Built for everyday use with a '
         || (ARRAY['1-year','2-year','90-day'])[1 + g % 3] || ' warranty.'
FROM generate_series(150001, 200000) AS g
ON CONFLICT (product_id) DO NOTHING;

INSERT INTO orders (order_id, customer_id, product_id, quantity, status, ordered_at)
SELECT g,
       'C' || lpad((1 + (g * 7919) % 5000)::text, 5, '0'),
       1 + (g::bigint * 104729) % 200000,
       1 + g % 4,
       (ARRAY['delivered','delivered','shipped','processing','returned'])[1 + (g * 3) % 5],
       now() - make_interval(days => g % 365, hours => g % 24)
FROM generate_series(1, 50000) AS g
ON CONFLICT (order_id) DO NOTHING;

INSERT INTO orders (order_id, customer_id, product_id, quantity, status, ordered_at)
SELECT g,
       'C' || lpad((1 + (g * 7919) % 5000)::text, 5, '0'),
       1 + (g::bigint * 104729) % 200000,
       1 + g % 4,
       (ARRAY['delivered','delivered','shipped','processing','returned'])[1 + (g * 3) % 5],
       now() - make_interval(days => g % 365, hours => g % 24)
FROM generate_series(50001, 100000) AS g
ON CONFLICT (order_id) DO NOTHING;

UPDATE orders o
SET    amount = p.price * o.quantity
FROM   products p
WHERE  p.product_id = o.product_id
AND    o.amount = 0;

UPDATE customers c
SET    lifetime_value = s.total
FROM  (SELECT customer_id, sum(amount) AS total FROM orders GROUP BY customer_id) s
WHERE  s.customer_id = c.customer_id;

ANALYZE customers;

ANALYZE products;

ANALYZE orders;
