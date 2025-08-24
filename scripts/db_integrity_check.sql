-- =============================================
-- SQL Stories – v3 DB Integrity Test Session
-- Focus: PK/FK declaration visibility + orphan checks
-- Target DB: ecom_retailer_v3.db (SQLite)
-- =============================================

-- Ensure FK enforcement is active for this session
PRAGMA foreign_keys = ON;

/*
HOW TO USE
1) Open this file in your SQLite client connected to ecom_retailer_v3.db
2) Run the whole script. It will:
   - List tables & counts
   - Report declared PRIMARY KEYS per table
   - Report tables missing PKs
   - Report declared FOREIGN KEYS (if any)
   - Run orphan checks for the expected relationships
   - Check common uniqueness assumptions (incl. composite examples)
*/

-- =============================================
-- 0) Quick inventory of tables + row counts
-- =============================================
SELECT name AS table_name
FROM sqlite_master 
WHERE type='table' AND name NOT LIKE 'sqlite_%'
ORDER BY name;

-- NOTE: The following queries use explicit `UNION ALL` clauses for each table.
-- This is necessary because SQLite's `PRAGMA` statements and `sqlite_master` table
-- do not support dynamic iteration within a single query execution.
SELECT 'cart_items'        AS table_name, COUNT(*) AS rows FROM cart_items
UNION ALL SELECT 'customers',        COUNT(*) FROM customers
UNION ALL SELECT 'order_items',      COUNT(*) FROM order_items
UNION ALL SELECT 'orders',           COUNT(*) FROM orders
UNION ALL SELECT 'product_catalog',  COUNT(*) FROM product_catalog
UNION ALL SELECT 'return_items',     COUNT(*) FROM return_items
UNION ALL SELECT 'returns',          COUNT(*) FROM returns
UNION ALL SELECT 'shopping_carts',   COUNT(*) FROM shopping_carts
ORDER BY table_name;

-- =============================================
-- 1) PRIMARY KEY audit (declared PKs only)
--    Shows which columns are part of the PK for each table.
-- =============================================

-- Per-table PRAGMA outputs for quick inspection
PRAGMA table_info(customers);
PRAGMA table_info(orders);
PRAGMA table_info(order_items);
PRAGMA table_info(returns);
PRAGMA table_info(return_items);
PRAGMA table_info(product_catalog);
PRAGMA table_info(shopping_carts);
PRAGMA table_info(cart_items);

-- Compact PK summary
SELECT 'customers'       AS table_name, GROUP_CONCAT(name) AS pk_columns
FROM pragma_table_info('customers') WHERE pk > 0
UNION ALL
SELECT 'orders',         GROUP_CONCAT(name) FROM pragma_table_info('orders') WHERE pk > 0
UNION ALL
SELECT 'order_items',    GROUP_CONCAT(name) FROM pragma_table_info('order_items') WHERE pk > 0
UNION ALL
SELECT 'returns',        GROUP_CONCAT(name) FROM pragma_table_info('returns') WHERE pk > 0
UNION ALL
SELECT 'return_items',   GROUP_CONCAT(name) FROM pragma_table_info('return_items') WHERE pk > 0
UNION ALL
SELECT 'product_catalog',GROUP_CONCAT(name) FROM pragma_table_info('product_catalog') WHERE pk > 0
UNION ALL
SELECT 'shopping_carts', GROUP_CONCAT(name) FROM pragma_table_info('shopping_carts') WHERE pk > 0
UNION ALL
SELECT 'cart_items',     GROUP_CONCAT(name) FROM pragma_table_info('cart_items') WHERE pk > 0
;

-- Tables missing a declared PK
WITH all_tables AS (
  SELECT 'customers' t UNION ALL
  SELECT 'orders' UNION ALL
  SELECT 'order_items' UNION ALL
  SELECT 'returns' UNION ALL
  SELECT 'return_items' UNION ALL
  SELECT 'product_catalog' UNION ALL
  SELECT 'shopping_carts' UNION ALL
  SELECT 'cart_items'
), pk_present AS (
  SELECT 'customers' t, COUNT(*) AS n FROM pragma_table_info('customers') WHERE pk > 0
  UNION ALL SELECT 'orders', COUNT(*) FROM pragma_table_info('orders') WHERE pk > 0
  UNION ALL SELECT 'order_items', COUNT(*) FROM pragma_table_info('order_items') WHERE pk > 0
  UNION ALL SELECT 'returns', COUNT(*) FROM pragma_table_info('returns') WHERE pk > 0
  UNION ALL SELECT 'return_items', COUNT(*) FROM pragma_table_info('return_items') WHERE pk > 0
  UNION ALL SELECT 'product_catalog', COUNT(*) FROM pragma_table_info('product_catalog') WHERE pk > 0
  UNION ALL SELECT 'shopping_carts', COUNT(*) FROM pragma_table_info('shopping_carts') WHERE pk > 0
  UNION ALL SELECT 'cart_items', COUNT(*) FROM pragma_table_info('cart_items') WHERE pk > 0
)
SELECT a.t AS table_missing_pk
FROM all_tables a
LEFT JOIN pk_present p ON p.t = a.t
WHERE COALESCE(p.n,0) = 0
ORDER BY 1;

-- =============================================
-- 2) FOREIGN KEY audit (declared FKs only)
--    If your schema defines FKs, these will list them.
-- =============================================
PRAGMA foreign_key_list(customers);
PRAGMA foreign_key_list(orders);
PRAGMA foreign_key_list(order_items);
PRAGMA foreign_key_list(returns);
PRAGMA foreign_key_list(return_items);
PRAGMA foreign_key_list(product_catalog);
PRAGMA foreign_key_list(shopping_carts);
PRAGMA foreign_key_list(cart_items);

-- Verify FK enforcement is on (1 = ON)
PRAGMA foreign_keys;

-- If FKs are declared, this will list violations (empty means none — or no FKs declared)
PRAGMA foreign_key_check;

-- =============================================
-- 3) Orphan checks for expected relationships (works even without declared FKs)
--    These validate join integrity by convention.
-- =============================================

-- orders.customer_id → customers.customer_id
SELECT COUNT(*) AS orphan_orders_without_customer
FROM orders o
LEFT JOIN customers c ON c.customer_id = o.customer_id
WHERE c.customer_id IS NULL;

-- order_items.order_id → orders.order_id
SELECT COUNT(*) AS orphan_order_items_without_order
FROM order_items oi
LEFT JOIN orders o ON o.order_id = oi.order_id
WHERE o.order_id IS NULL;

-- order_items.product_id → product_catalog.product_id
SELECT COUNT(*) AS orphan_order_items_without_product
FROM order_items oi
LEFT JOIN product_catalog p ON p.product_id = oi.product_id
WHERE p.product_id IS NULL;

-- returns.order_id → orders.order_id
SELECT COUNT(*) AS orphan_returns_without_order
FROM returns r
LEFT JOIN orders o ON o.order_id = r.order_id
WHERE o.order_id IS NULL;

-- return_items.return_id → returns.return_id
SELECT COUNT(*) AS orphan_return_items_without_return
FROM return_items ri
LEFT JOIN returns r ON r.return_id = ri.return_id
WHERE r.return_id IS NULL;

-- shopping_carts.customer_id → customers.customer_id
SELECT COUNT(*) AS orphan_carts_without_customer
FROM shopping_carts sc
LEFT JOIN customers c ON c.customer_id = sc.customer_id
WHERE c.customer_id IS NULL;

-- cart_items.cart_id → shopping_carts.cart_id
SELECT COUNT(*) AS orphan_cart_items_without_cart
FROM cart_items ci
LEFT JOIN shopping_carts sc ON sc.cart_id = ci.cart_id
WHERE sc.cart_id IS NULL;

-- cart_items.product_id → product_catalog.product_id
SELECT COUNT(*) AS orphan_cart_items_without_product
FROM cart_items ci
LEFT JOIN product_catalog p ON p.product_id = ci.product_id
WHERE p.product_id IS NULL;

-- =============================================
-- 4) Uniqueness sanity checks (PK expectations)
--    Single-column PK checks + composite checks for line-item tables
-- =============================================

-- Single-column PK duplicate checks (known columns only)
SELECT COUNT(*) AS dup_customers
FROM (
  SELECT customer_id, COUNT(*) c FROM customers GROUP BY customer_id HAVING COUNT(*) > 1
);

SELECT COUNT(*) AS dup_orders
FROM (
  SELECT order_id, COUNT(*) c FROM orders GROUP BY order_id HAVING COUNT(*) > 1
);

SELECT COUNT(*) AS dup_returns
FROM (
  SELECT return_id, COUNT(*) c FROM returns GROUP BY return_id HAVING COUNT(*) > 1
);

SELECT COUNT(*) AS dup_products
FROM (
  SELECT product_id, COUNT(*) c FROM product_catalog GROUP BY product_id HAVING COUNT(*) > 1
);

SELECT COUNT(*) AS dup_carts
FROM (
  SELECT cart_id, COUNT(*) c FROM shopping_carts GROUP BY cart_id HAVING COUNT(*) > 1
);

-- Composite key expectation checks (line-item tables commonly use composites)
-- Expect at most one row per (order_id, product_id) in order_items
SELECT COUNT(*) AS dup_order_items_order_product
FROM (
  SELECT order_id, product_id, COUNT(*) c
  FROM order_items
  GROUP BY order_id, product_id
  HAVING COUNT(*) > 1
);

-- Expect at most one row per (cart_id, product_id) in cart_items
SELECT COUNT(*) AS dup_cart_items_cart_product
FROM (
  SELECT cart_id, product_id, COUNT(*) c
  FROM cart_items
  GROUP BY cart_id, product_id
  HAVING COUNT(*) > 1
);

-- Optional variant if your model allows split lines at different prices:
-- SELECT COUNT(*) AS dup_order_items_order_product_price
-- FROM (
--   SELECT order_id, product_id, unit_price, COUNT(*) c
--   FROM order_items
--   GROUP BY order_id, product_id, unit_price
--   HAVING COUNT(*) > 1
-- );

-- =============================================
-- 5) DATETIME / RANGE INTEGRITY CHECKS (Generalized)
-- =============================================

-- Customers signup_date must be within [2019-01-01, 2025-12-31]
SELECT 'customers.signup_date_out_of_range' AS check_name,
       COUNT(*) AS violations
FROM customers
WHERE date(signup_date) < date('2019-01-01')
   OR date(signup_date) > date('2025-12-31')
   OR date(signup_date) > date('now');

-- Orders order_date must be within [2019-01-01, 2025-12-31]
SELECT 'orders.order_date_out_of_range' AS check_name,
       COUNT(*) AS violations
FROM orders
WHERE date(order_date) < date('2019-01-01')
   OR date(order_date) > date('2025-12-31')
   OR date(order_date) > date('now');

-- Returns return_date must be within [2019-01-01, 2025-12-31]
SELECT 'returns.return_date_out_of_range' AS check_name,
       COUNT(*) AS violations
FROM returns
WHERE date(return_date) < date('2019-01-01')
   OR date(return_date) > date('2025-12-31')
   OR date(return_date) > date('now');

-- Shopping carts created_at must be within [2019-01-01, 2025-12-31]
SELECT 'shopping_carts.created_at_out_of_range' AS check_name,
       COUNT(*) AS violations
FROM shopping_carts
WHERE date(created_at) < date('2019-01-01')
   OR date(created_at) > date('2025-12-31')
   OR date(created_at) > date('now');

-- Orders must not occur before customer signup
SELECT 'orders_before_signup' AS check_name,
       COUNT(*) AS violations
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
WHERE date(o.order_date) < date(c.signup_date);

-- Returns must not occur before the associated order
SELECT 'returns_before_order' AS check_name,
       COUNT(*) AS violations
FROM returns r
JOIN orders o ON o.order_id = r.order_id
WHERE date(r.return_date) < date(o.order_date);

-- =============================================
-- END OF TESTS
-- =============================================
