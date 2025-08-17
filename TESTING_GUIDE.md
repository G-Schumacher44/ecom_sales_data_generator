<p align="center">
  <img src="repo_files/dark_logo_banner.png" width="1000"/>
  <br>
  <em>Retail Scenario Data Generator + QA Framework</em>
</p>

<p align="center">
  <img alt="MIT License" src="https://img.shields.io/badge/license-MIT-blue">
  <img alt="Status" src="https://img.shields.io/badge/status-alpha-lightgrey">
  <img alt="Version" src="https://img.shields.io/badge/version-v0.1.0-blueviolet">
</p>

# 🧪 Testing and Validation Guide

This project includes a comprehensive testing framework to ensure the integrity, quality, and logical consistency of the synthetic data. This guide explains the different test suites and how to use them.

> ⬅️ [Back to Project README](README.md)

---

## 📚 Table of Contents
- [🧪 Testing and Validation Guide](#-testing-and-validation-guide)
  - [📚 Table of Contents](#-table-of-contents)
  - [🎯 Test Philosophy](#-test-philosophy)
  - [Main QA Suite (`qa_tests.py`)](#-main-qa-suite-qa_testspymain-qa-suite-qa_testspy)
    - Key Validation Functions
    - Interpreting the Output
  - 2. Big Audit (`big_audit.py`)
  - 3. Pytest Suite (`pytests/`)

---

## 🎯 Test Philosophy

The testing framework is divided into three main parts, each with a distinct purpose:

 **Main QA Suite (`qa_tests.py`)**: A suite of critical data quality checks that runs automatically after every data generation. Its purpose is to catch fundamental errors in the data.

**Big Audit (`big_audit.py`)**: A script that provides a high-level statistical summary of the generated data. It's designed for manual inspection and business logic validation rather than hard-fail checks.

**Pytest Suite (`src/pytests/`)**: A set of unit tests for developers to validate the core logic of the configuration and data quality rules in isolation.

---

## Main QA Suite (`qa_tests.py`)

This is the most important test suite for ensuring data quality. It is **executed automatically** by the `ecomgen` command.

### Key Validation Functions

- **`validate_primary_keys`**: Checks every primary key column (e.g., `orders.order_id`, `customers.customer_id`) to ensure all values are unique.
- **`validate_all_referential_integrity`**: The cornerstone of the QA suite. It systematically checks every foreign key relationship (e.g., `orders.customer_id` -> `customers.customer_id`) to guarantee there are no orphaned records.
- **`validate_conversion_funnel`**: Verifies two key aspects of the sales funnel:
  1.  That the number of rows in the `orders` table exactly matches the number of `shopping_carts` with a `status` of "converted."
  2.  That the actual cart-to-order conversion rate is statistically close to the `conversion_rate` configured in the YAML file.
- **`validate_repeat_purchase_propensity`**: Checks that the actual percentage of customers who make a second purchase aligns with the behavior defined in the `repeat_purchase_settings` in the YAML file.
- **`validate_return_refunds`**: Ensures that the `refunded_amount` in the `returns` table header correctly matches the sum of the `refunded_amount` of its associated `return_items`.
- **`validate_date_fields`**: Checks for invalid date formats and ensures logical consistency (e.g., a `return_date` cannot be before its `order_date`).

### Interpreting the Output

- **`INFO: ✅ ...`**: Indicates that a test has passed successfully.
- **`WARNING: ...`**: Indicates a minor issue or a statistical deviation that does not break the data's integrity but is worth noting. The script will **not** fail on warnings if you are running with a messiness level above `baseline`.
- **`ERROR: ...`**: Indicates a critical failure (e.g., a duplicate primary key or a broken foreign key relationship). This will stop the process and raise an error.

---

## Big Audit (`big_audit.py`)

This script is also run automatically by the `ecomgen` command. It prints summaries, null counts, and distributions for manual review.

**Purpose**: To provide a quick, human-readable summary of the dataset's shape and content. It's excellent for a "gut check" to see if the data feels right.

---

## Pytest Suite (`src/pytests/`)

This suite is primarily for developers working on the generator itself. It contains unit tests that validate the core logic of the configuration parser and the data quality rules in a controlled environment.

**Purpose**: To catch regressions and bugs in the generator's internal logic before they affect the data output.

**How to Run**:
```bash
pytest
```

By using these tools, you can have high confidence in the quality and realism of the data you generate.
