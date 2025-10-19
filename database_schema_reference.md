<p align="center">
  <img src="repo_files/sql_stories_logo.png" width="1000"/>
  <br>
  <em>Retail Scenario Data Generator + QA Framework</em>
</p>

<p align="center">
  <img alt="MIT License" src="https://img.shields.io/badge/license-MIT-blue">
  <img alt="Status" src="https://img.shields.io/badge/status-alpha-lightgrey">
  <img alt="Version" src="https://img.shields.io/badge/version-v0.3.0-blueviolet">
</p>

# 📊 SQL Stories Database Schema Reference

> This document provides a complete overview of the SQLite database created by this generator. It reflects the structure of `ecom_retailer_v3.db` — the canonical data environment for case studies, exercises, and analytics workflows.

---

## 🗂️ Core Sales & Fulfillment Tables

| Table Name     | Description                                                      | Key Columns                                                                                                                                                                         |
| -------------- | ---------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `orders`       | Purchase-level records for completed transactions                | `order_id`, `customer_id`, `order_date`, `order_channel`, `total_items`, `gross_total`, `net_total`, `shipping_cost`, `total_discount_amount`, `payment_processing_fee`, `agent_id` |
| `order_items`  | Items sold per order with quantity, price, and product linkage   | `order_id`, `product_id`, `product_name`, `category`, `quantity`, `unit_price`, `discount_amount`, `cost_price`                                                                     |
| `returns`      | Metadata on product returns including timestamp and reason codes | `return_id`, `order_id`, `customer_id`, `return_date`, `return_type`, `reason`, `return_channel`, `refund_method`, `refunded_amount`, `agent_id`                                    |
| `return_items` | Refunded items per return: quantity, product ID, refund value    | `return_item_id`, `return_id`, `order_id`, `product_id`, `product_name`, `category`, `quantity_returned`, `unit_price`, `cost_price`, `refunded_amount`                             |

---

## 🛒 Cart Behavior Tables

| Table Name       | Description                                                          | Key Columns                                                                                               |
| ---------------- | -------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `shopping_carts` | Tracks customer browsing carts, including timestamps and cart status | `cart_id`, `customer_id`, `created_at`, `updated_at`, `status`, `cart_total`                              |
| `cart_items`     | Items added to carts, supports funnel and abandonment analytics      | `cart_item_id`, `cart_id`, `product_id`, `product_name`, `category`, `added_at`, `quantity`, `unit_price` |

---

## 🏷️ Product Metadata

| Table Name        | Description                                                               | Key Columns                                                                                |
| ----------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `product_catalog` | Master data for all SKUs, including price, category, and cost assumptions | `product_id`, `product_name`, `category`, `unit_price`, `cost_price`, `inventory_quantity` |

---

## 🙍 Customer Information

| Table Name  | Description                                                             | Key Columns                                                                                                                                          |
| ----------- | ----------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `customers` | Customer profiles with signup dates, acquisition channels, and segments | `customer_id`, `first_name`, `last_name`, `email`, `signup_date`, `signup_channel`, `loyalty_tier`, `initial_loyalty_tier`, `is_guest`, `clv_bucket` |

---

## 🛠️ Join Notes & Modeling Suggestions

- **Conversion Funnel**: Use `shopping_carts → orders` relationship to track conversion vs abandonment.
- **Customer Journey**: Join `customers → orders → order_items` to measure lifetime value or behavior.
- **Returns Analysis**: Link `returns → return_items` and join to `orders`, `order_items`, and `product_catalog`.
- **Margin Estimates**: Compare `unit_price` and `cost_price` on `order_items` / `product_catalog` to analyze per-SKU profitability.

> ⚠️ No direct inventory or fulfillment tracking is modeled — this schema is designed for sales, retention, and profitability scenarios.

## 🔑 Primary & Foreign Key Reference

| Table             | Primary Key              | Foreign Keys                                                                                                       |
| ----------------- | ------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| `customers`       | `customer_id`            | *(none)*                                                                                                           |
| `product_catalog` | `product_id`             | *(none)*                                                                                                           |
| `shopping_carts`  | `cart_id`                | `customer_id` → `customers.customer_id`                                                                            |
| `cart_items`      | `cart_item_id`           | `cart_id` → `shopping_carts.cart_id`<br>`product_id` → `product_catalog.product_id`                                |
| `orders`          | `order_id`               | `customer_id` → `customers.customer_id`                                                                            |
| `order_items`     | `order_id`, `product_id` | `order_id` → `orders.order_id`<br>`product_id` → `product_catalog.product_id`                                      |
| `returns`         | `return_id`              | `order_id` → `orders.order_id`<br>`customer_id` → `customers.customer_id`                                          |
| `return_items`    | `return_item_id`         | `return_id` → `returns.return_id`<br>`order_id` → `orders.order_id`<br>`product_id` → `product_catalog.product_id` |  |
> ℹ️ `orders.agent_id` and `returns.agent_id` draw from the configured `agent_pool` roster and are not enforced as foreign keys because no agent dimension table is generated.
---

## 🔗 Regeneration & Exploration

This schema reflects the structure of `ecom_retailer_v3.db`, prebuilt in each scenario repo. To inspect or regenerate:

- Use the provided `ecom_retailer_v3.db` in a SQLite viewer
- Or rebuild using the CSVs and SQL in `db_builder.zip`

> 🧩 The schema supports modular scenario design — join logic is consistent across all stories.
