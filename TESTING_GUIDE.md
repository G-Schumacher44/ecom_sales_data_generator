<p align="center">
  <img src="repo_files/dark_logo_banner.png" width="1000"/>
  <br>
  <em>Retail Scenario Data Generator + QA Framework</em>
</p>

<p align="center">
  <img alt="MIT License" src="https://img.shields.io/badge/license-MIT-blue">
  <img alt="Status" src="https://img.shields.io/badge/status-alpha-lightgrey">
  <img alt="Version" src="https://img.shields.io/badge/version-v0.3.0-blueviolet">
</p>

# 🧪 Testing and Validation Guide

This project includes a comprehensive testing framework to ensure the integrity, quality, and logical consistency of the synthetic data. This guide explains the different test suites and how to use them.

> ⬅️ [Back to Project README](README.md)

---

## 📚 Table of Contents
- [🧪 Testing and Validation Guide](#-testing-and-validation-guide)
  - [📚 Table of Contents](#-table-of-contents)
  - [🎯 Test Philosophy](#-test-philosophy)
  - [1. Main QA Suite (`qa_tests.py`)](#1-main-qa-suite-qa_testspy)
    - [Key Validation Functions](#key-validation-functions)
    - [Interpreting the Output](#interpreting-the-output)
  - [2. Big Audit (`big_audit.py`)](#2-big-audit-big_auditpy)
  - [3. Pytest Suite (`src/pytests/`)](#3-pytest-suite-srcpytests)
  - [4. SQL Integrity Check (`scripts/db_integrity_check.sql`)](#4-sql-integrity-check-scriptsdb_integrity_checksql)

---

## 🎯 Test Philosophy

The testing framework is divided into four main parts, each with a distinct purpose:

1.  **Main QA Suite (`qa_tests.py`)**: A suite of critical data quality checks that runs **automatically** after every data generation. Its purpose is to catch fundamental errors in the data.
2.  **Big Audit (`big_audit.py`)**: A script that provides a high-level statistical summary of the generated data, also run automatically. It's designed for manual inspection and business logic validation rather than hard-fail checks.
3.  **Pytest Suite (`src/pytests/`)**: A set of unit tests for developers to validate the core logic of the configuration and data quality rules in isolation.
4.  **SQL Integrity Check (`scripts/db_integrity_check.sql`)**: A manual SQL script for hands-on, in-database auditing. It's designed for analysts and developers to directly inspect the final schema, keys, and data integrity after the database has been loaded.

---

## 1. Main QA Suite (`qa_tests.py`)

This is the most important test suite for ensuring data quality. It is **executed automatically** by the `ecomgen` command.

### Key Validation Functions

- **`validate_primary_keys`**: Checks every primary key—both single-column (e.g., `orders.order_id`) and composite (e.g., `order_items` on `order_id`, `product_id`)—to ensure all values are unique.
- **`validate_all_referential_integrity`**: The cornerstone of the QA suite. It systematically checks every foreign key relationship (e.g., `orders.customer_id` -> `customers.customer_id`) to guarantee there are no orphaned records.
- **`validate_conversion_funnel`**: Verifies two key aspects of the sales funnel:
  1.  That the number of rows in the `orders` table exactly matches the number of `shopping_carts` with a `status` of "converted."
  2.  That the actual cart-to-order conversion rate is statistically close to the `conversion_rate` configured in the YAML file.
- **`validate_repeat_purchase_propensity`**: Checks that the actual percentage of customers who make a second purchase aligns with the behavior defined in the `repeat_purchase_settings` in the YAML file.
- **`validate_repeat_purchase_propensity`**: A sophisticated statistical check that validates the customer lifecycle simulation. It verifies that the actual repeat purchase rate for each customer segment (defined by channel and tier) is statistically close to the configured propensity. The test uses a zero-inflated Poisson model to account for seasonality, conversion rates, and cohort-based shocks, ensuring the behavioral simulation is accurate.
- **`validate_financial_logic`**: Verifies the integrity of order-level financial calculations. It confirms that `orders.net_total` correctly equals `orders.gross_total` - `orders.total_discount_amount`. It also ensures other key financial columns like `actual_shipping_cost` and `payment_processing_fee` contain valid, non-negative values.
- **`validate_cogs_logic`**: Ensures product profitability by checking that `cost_price` is not greater than `unit_price` in the `product_catalog`. It also validates that this `cost_price` is correctly snapshotted to the `order_items` and `return_items` tables.
- **`validate_cart_totals`**: Ensures that the `cart_total` in the `shopping_carts` table is consistent with its status. For `converted` and `abandoned` carts, it must match the sum of its items. For `emptied` carts, the total must be zero and it must have no associated items.
- **`validate_cart_timestamps`**: Checks for logical consistency among cart-related timestamps (e.g., an item's `added_at` cannot be before the cart's `created_at`).
- **`validate_return_refunds`**: Ensures that the `refunded_amount` in the `returns` table header correctly matches the sum of the `refunded_amount` of its associated `return_items`.

### Interpreting the Output

- **`INFO: ✅ ...`**: Indicates that a test has passed successfully.
- **`WARNING: ...`**: Indicates a minor issue or a statistical deviation that does not break the data's integrity but is worth noting. The script will **not** fail on warnings if you are running with a messiness level above `baseline`.
- **`ERROR: ...`**: Indicates a critical failure (e.g., a duplicate primary key or a broken foreign key relationship). This will stop the process and raise an error.

---

## 2. Big Audit (`big_audit.py`)

This script is also run automatically by the `ecomgen` command. It prints summaries, null counts, and distributions for manual review.

**Purpose**: To provide a quick, human-readable summary of the dataset's shape and content. It's excellent for a "gut check" to see if the data feels right.

---

## 3. Pytest Suite (`src/pytests/`)

This suite is primarily for developers working on the generator itself. It contains unit tests that validate the core logic of the configuration parser and the data quality rules in a controlled environment.

**Purpose**: To catch regressions and bugs in the generator's internal logic before they affect the data output.

**How to Run**:
```bash
pytest
```

By using these tools, you can have high confidence in the quality and realism of the data you generate.

---

## 4. SQL Integrity Check (`scripts/db_integrity_check.sql`)

For analysts and developers who want to perform a hands-on audit directly within the database, the project includes a powerful SQL script.

**Purpose**: This script serves as a manual, in-database complement to the automated Python tests. It allows you to directly inspect the final database schema, verify primary and foreign key declarations, and run detailed checks for data integrity issues like orphaned records.

**How to Use**:

1.  **Generate and Load the Database**: First, run the data generator and load the output into a SQLite database.
    ```bash
    # Generate data (if you haven't already)
    ecomgen --config config/ecom_sales_gen_template.yaml

    # Load data into a new SQLite database file
    sqlite3 ecom_retailer_v3.db < output/load_data.sql
    ```

2.  **Run the Integrity Check Script**: Open the `scripts/db_integrity_check.sql` file in a SQLite-compatible client (like DBeaver, VS Code's SQLite extension, or the command-line tool) connected to your `ecom_retailer_v3.db` file and execute the entire script.

**Key Checks Performed**:

-   **Primary Key Audit**: Reports which columns are declared as primary keys for each table and lists any tables missing a PK.
-   **Foreign Key Audit**: Lists all declared foreign key relationships and uses `PRAGMA foreign_key_check` to find any violations.
-   **Orphan Record Checks**: Systematically runs `LEFT JOIN` queries to find records that violate referential integrity by convention (e.g., an `order_item` pointing to a non-existent `order_id`), even if FK constraints aren't declared.
-   **Uniqueness Checks**: Verifies that columns expected to be unique (like `customers.customer_id`) do not contain duplicates.
-   **Date Logic**: Ensures that timestamps are logical (e.g., `return_date` is not before `order_date`).

___

<p align="center">
  <a href="README.md">🏠 <b>Main README</b></a>
  &nbsp;·&nbsp;
  <a href="CONFIG_GUIDE.md">⚙️ <b>Config Guide</b></a>
  &nbsp;·&nbsp;
  <a href="TESTING_GUIDE.md">🧪 <b>Testing Guide</b></a>
  &nbsp;·&nbsp;
  <a href="https://github.com/G-Schumacher44/sql_stories_portfolio_demo">📸 <b>See it in Action</b></a>
</p>

<p align="center">
  <sub>✨ Synthetic Data · Python · QA Framework ✨</sub>
</p>