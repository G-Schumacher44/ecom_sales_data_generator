DROP TABLE IF EXISTS customers;
CREATE TABLE customers (
  customer_id TEXT,
  first_name TEXT,
  last_name TEXT,
  email TEXT,
  phone_number TEXT,
  signup_date DATE,
  gender TEXT,
  age INTEGER,
  is_guest BOOLEAN,
  customer_status TEXT,
  signup_channel TEXT,
  loyalty_tier TEXT,
  email_verified BOOLEAN,
  marketing_opt_in BOOLEAN,
  mailing_address TEXT,
  billing_address TEXT,
  loyalty_enrollment_date DATE,
  clv_bucket TEXT
);

.import --csv --skip 1 'output/customers.csv' customers

DROP TABLE IF EXISTS product_catalog;
CREATE TABLE product_catalog (
  product_id INTEGER,
  product_name TEXT,
  category TEXT,
  unit_price REAL,
  inventory_quantity INTEGER
);

.import --csv --skip 1 'output/product_catalog.csv' product_catalog

DROP TABLE IF EXISTS shopping_carts;
CREATE TABLE shopping_carts (
  cart_id TEXT,
  customer_id TEXT,
  created_at DATE,
  cart_total REAL,
  status TEXT
);

.import --csv --skip 1 'output/shopping_carts.csv' shopping_carts

DROP TABLE IF EXISTS cart_items;
CREATE TABLE cart_items (
  cart_item_id INTEGER,
  cart_id TEXT,
  product_id INTEGER,
  product_name TEXT,
  category TEXT,
  quantity INTEGER,
  unit_price REAL
);

.import --csv --skip 1 'output/cart_items.csv' cart_items

DROP TABLE IF EXISTS orders;
CREATE TABLE orders (
  order_id TEXT,
  total_items INTEGER,
  order_date DATE,
  customer_id TEXT,
  email TEXT,
  order_channel TEXT,
  is_expedited BOOLEAN,
  customer_tier TEXT,
  order_total REAL,
  payment_method TEXT,
  shipping_speed TEXT,
  shipping_cost REAL,
  agent_id TEXT,
  shipping_address TEXT,
  billing_address TEXT,
  clv_bucket TEXT,
  is_reactivated BOOLEAN
);

.import --csv --skip 1 'output/orders.csv' orders

DROP TABLE IF EXISTS order_items;
CREATE TABLE order_items (
  order_id TEXT,
  product_id INTEGER,
  product_name TEXT,
  category TEXT,
  quantity INTEGER,
  unit_price REAL
);

.import --csv --skip 1 'output/order_items.csv' order_items

DROP TABLE IF EXISTS returns;
CREATE TABLE returns (
  return_id TEXT,
  order_id TEXT,
  customer_id TEXT,
  email TEXT,
  return_date DATE,
  reason TEXT,
  return_type TEXT,
  refunded_amount REAL,
  return_channel TEXT,
  agent_id TEXT,
  refund_method TEXT
);

.import --csv --skip 1 'output/returns.csv' returns

DROP TABLE IF EXISTS return_items;
CREATE TABLE return_items (
  return_item_id INTEGER,
  return_id TEXT,
  order_id TEXT,
  product_id INTEGER,
  product_name TEXT,
  category TEXT,
  quantity_returned INTEGER,
  unit_price REAL,
  refunded_amount REAL
);

.import --csv --skip 1 'output/return_items.csv' return_items

