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

---

# 🛒 Ecommerce Sales Database Generator

A YAML-configurable Python engine for generating synthetic, relational e-commerce databases — designed for SQL training, analytics storytelling, and realistic pipeline testing. This system goes beyond raw data: it simulates a full customer journey from browsing session to purchase, builds linked tables with referential integrity, and includes configurable messiness and built-in QA test suites to mirror real-world data challenges.
>📸 See it in action: [SQL Stories Portfolio Demo](https://github.com/G-Schumacher44/sql_stories_portfolio_demo)

___

## 🧩 TLDR;

- Generate synthetic, realistic e-commerce data (orders, returns, customers, etc.)
- **New:** Simulates cart abandonment, conversion rates, and repeat purchase behavior for realistic cohort analysis.
- YAML-controlled configuration of row volumes, faker behavior, return rates, etc.
- Plug-and-play messiness injection (via --messiness-level flag) for simulating real-world inconsistencies 
- Built-in QA tests: referential integrity, refund audits, return rate checks
- CLI runner, Pytest test suite, and optional big/mess audit extensions
- Designed for SQL project demos, portfolio datasets, and analytics onboarding


<details>
<summary> ⏯️ Quick Start</summary>

1. Clone the repository  
   ```bash
   git clone https://github.com/G-Schumacher44/ecom_sales_data_generator.git
   cd ecom_sales_data_generator
   # Install in editable mode
   pip install -e .
   ```

2. Run the CLI      
    ```bash
    ecomgen --config config/ecom_sales_gen_template.yaml --messiness-level none
    ```
</details>

---

## 📐 What’s Included

This project provides everything needed to simulate a realistic online retailer’s dataset for SQL, BI, or data science use:

- **Modular Generators**: Custom row generation logic for each core table (`orders`, `order_items`, `returns`, etc.)
- **YAML Config System**: Fine-grained control over generation volume, vocab, lookup tables, faker seed, and injection toggles
- **Messiness Engine**: Add typos, duplicates, nulls, formatting bugs, and numeric corruption
- **QA Framework**: Includes an automated Python suite (`qa_tests.py`) for validating data logic and a manual SQL script (`scripts/db_integrity_check.sql`) for direct database schema and integrity auditing.
- **CLI Interface**: One-command generation + validation from terminal or VS Code tasks
- **Editable Dev Mode**: Install via `pip install -e .` for active development and local CLI usage

### 📊 Database Overview

| Table Name        | Key Fields                                  | Purpose                                    |
| ----------------- | ------------------------------------------- | ------------------------------------------ |
| `orders`          | `order_id`, `customer_id`                   | Completed transactions and shipping costs  |
| `order_items`     | `order_item_id`, `order_id`, `product_id`   | Line-level product sales per order         |
| `returns`         | `return_id`, `order_id`, `return_reason`    | Return metadata per order                  |
| `return_items`    | `return_item_id`, `return_id`, `product_id` | Refunded products with values              |
| `shopping_carts`  | `cart_id`, `customer_id`, `status`          | Tracks cart activity (open, abandoned)     |
| `cart_items`      | `cart_item_id`, `cart_id`, `product_id`     | Products added to cart pre-purchase        |
| `product_catalog` | `product_id`, `product_name`, `unit_price`  | SKU definitions and margin proxy           |
| `customers`       | `customer_id`, `signup_date`                | Customer profiles and acquisition channels |

> 📌 View the full reference: [`database_schema_reference.md`](database_schema_reference.md)


### 🧭 Orientation & Getting Started

<details>
<summary><strong>🧠 Notes from the Dev Team</strong></summary>
<br>

**Task and Purpose**

I built this system to reinforce, refresh, and evaluate my SQL skills through practical, repeatable analysis. Rather than relying on static datasets, I wanted something dynamic — a way to simulate the kinds of data challenges analysts face every day, with full control over volume, structure, and messiness.

**Why build a system and not just a script?**

This tool doesn’t just generate data — it builds a complete relational database simulation. I designed a system to go beyond isolated datasets by embedding referential logic, conditionally required fields, and analytical scenarios into the generation process.

You can see this engine in action in the [SQL Stories Portfolio Demo](https://github.com/G-Schumacher44/sql_stories_portfolio_demo), where I use AI-generated prompts to simulate realistic business scenarios and investigative workflows. This pairing gives me an unlimited sandbox to practice SQL storytelling, data diagnostics, and real-world problem solving — all powered by the datasets generated here.

**Human-readable. YAML-driven. Designed for learning.**

</details>

<details>
<summary><strong> ✨ Key Simulation Features </strong></summary>
<br>

This generator goes beyond simple row creation by simulating a complete, interconnected e-commerce ecosystem.

- **Full Sales Funnel**: Models the entire customer journey from browsing to purchase. It generates a large volume of `shopping_carts` and then "converts" a small, configurable percentage into `orders`, realistically simulating cart abandonment.
- **Time-Aware Customer Behavior**: Simulates customer return visits over a one-year period. The likelihood of a repeat purchase is tied to `loyalty_tier`, and the time between visits is randomized, creating rich data for cohort analysis.
- **Nuanced Cart Abandonment**: The simulation distinguishes between carts that are abandoned with items still in them and carts that are explicitly emptied by the user, providing deeper insight into user intent.
- **Detailed Cart Lifecycle**: Each cart and cart item now includes `created_at`, `updated_at`, and `added_at` timestamps, allowing for granular analysis of shopping session duration and user behavior within the cart.
- **Dynamic Returns**: The number of returns is not fixed but is generated as a percentage of total orders, ensuring that return volumes scale realistically with sales.
- **Contextual Messiness**: The messiness engine can inject not just random noise but also contextual issues, like biased return reasons based on product category or seasonal sales spikes during holiday months.
- **Channel-Specific Behavior**: Models distinct customer behavior based on their acquisition channel (`signup_channel`), influencing their purchase frequency, return rates, and even product category preferences.
- **Earned Customer Value**: Customer `loyalty_tier` and `clv_bucket` are not pre-assigned but are calculated and "earned" based on their cumulative spending over time, creating a realistic progression of customer value.
- **Long-Tail Churn & Reactivation**: The simulation now includes logic for long-term customer churn and a configurable probability for dormant customers to reactivate after a long period, adding valuable edge cases for analysis.

</details>

<details>

<summary><strong>🗺️ About the Project Ecosystem</strong></summary>

This repository is one part of a larger, interconnected set of projects. Here’s how they fit together:

*   **ecom_sales_data_generator (This Repository)** `(The Engine)`
    *   A custom Python package that produces the realistic, synthetic e-commerce data used in all the case studies. It's the source of truth for the data.
*   **[sql_stories_skills_builder](https://github.com/G-Schumacher44/sql_stories_skills_builder)** `(Learning Lab)`
    *   The public-facing skill-building suite. This is the main "product" where my published story modules are available for the community to use for practice and learning.
*   **[`sql_stories_portfolio_demo`](https://github.com/G-Schumacher44/sql_stories_portfolio_demo/tree/main)** `(The Showcase)`
    *   A curated and polished version of the best case studies, designed specifically to be a professional portfolio. It demonstrates the practical application of the tools and data from the other repositories.

</details> 

<details>
<summary><strong>🫆 Version Release Notes</strong></summary>

### ✅ v0.3.0 (Current)

This release introduces a major leap in simulation depth, focusing on realistic customer behavior, detailed financial modeling, and enhanced data quality.

#### 📈 Customer Behavior & Funnel Analysis
- **Enriched Cart & Session Analysis**: Added detailed timestamps (`created_at`, `updated_at`, `added_at`) and distinguished between `abandoned` and `emptied` carts for granular analysis of user intent.
- **Advanced Behavioral Modeling**: Introduced highly stratified customer behavior based on `signup_channel` and `loyalty_tier`, influencing repeat purchase rates, timing, and product preferences.
- **Earned Customer Status**: Implemented logic for customers to "earn" their `loyalty_tier` and `clv_bucket` based on cumulative spend, creating a realistic customer lifecycle.
- **Long-Tail Churn & Reactivation**: Added simulation of long-term dormancy and customer reactivation for advanced LTV analysis.

#### 💰 Financial & Profitability Analysis
- **Detailed Financial Modeling**: Integrated `cost_price` for COGS, `discount_amount` for promotions, `actual_shipping_cost` for shipping profitability, and `payment_processing_fee` for transaction costs, enabling precise net margin analysis.

#### 🧰 Data Quality & Realism
- **Enhanced Refund Realism**: Refund logic is now driven by the `reason` for the return, with configurable probabilities for full vs. partial refunds.
- **Seasonal & Event-Driven Spikes**: Added `seasonal_factors` and `retention_shocks` to simulate volume spikes and external events, creating non-flat cohort shapes.
- **Improved Schema & Data Integrity**: Added composite primary keys and foreign key constraints to the auto-generated `load_data.sql` script and fixed data generation logic to prevent duplicate line items.
---
### ✅ v0.2.0
- **Full Funnel Simulation**: Added `shopping_carts` and `cart_items` to model the complete customer journey from browsing session to purchase.
- **Realistic Conversion Modeling**: Introduced a configurable `conversion_rate` to simulate cart abandonment and a `repeat_purchase_settings` block to model customer lifecycle behavior.
- **Enhanced for Cohort Analysis**: The generator now creates time-aware repeat purchase data based on customer loyalty tiers, enabling realistic retention and LTV analysis.

---

### ✅ v0.1.0

- First production-ready release
- YAML-driven sales data generator with support for:
  - orders, order_items, returns, customers, and products
  - messiness injection (light/medium/heavy)
  - embedded CLI and Pytest-driven QA suite
  - config validation and baseline data audits
- Tested with `SQL Stories` for simulated analytics workflows

</details>

<details>
<summary><strong>🔮 v0.4.0 (Planned)</strong></summary>

- **Marketing Attribution & Coupon Codes**: Introduce a `promotions` table and logic for applying coupon codes at checkout, allowing for analysis of campaign effectiveness and discount strategies.
- **Dynamic Inventory & Stockouts**: Evolve the static `product_catalog` into a dynamic inventory system where purchases deplete stock levels, potentially leading to stockouts that affect cart conversion.
- **Shipping & Fulfillment Lead Times**: Add `ship_date` and `delivery_date` to the `orders` table to simulate fulfillment lead times and analyze the impact of shipping speed on customer satisfaction.
- **Customer-Level Messiness**: Introduce more targeted messiness, such as customers changing their shipping address or having multiple accounts that need to be merged.
</details>
</details> 

<details>
<summary>⚙️ Project Structure</summary>

```
ecom_sales_data_generator/
├── config/                          # YAML config templates for data generation
│   └── ecom_sales_gen_template.yaml
├── output/                          # Output folder for generated CSVs (ignored by Git)
├── src/                             # Main package source
│   ├── __init__.py
│   ├── ecomgen                      # CLI entrypoint
│   ├── generators/                 # Core row generators (orders, returns, etc.)
│   ├── pytests/                    # Pytest-based unit tests
│   │   ├── test_config_integrity.py
│   │   ├── test_config_linting.py
│   │   └── test_data_quality_rules.py
│   ├── tests/                      # CLI-based test modules
│   │   ├── big_audit.py
│   │   ├── mess_audit.py
│   │   └── qa_tests.py
│   └── utils/                      # Shared utilities (config loading, date helpers, etc.)
├── build/                           # Local build artifacts (ignored)
├── pyproject.toml                  # Build system and project metadata
├── environment.yml                 # Conda environment for dev setup
├── requirements.txt                # Optional pip requirements (mirrors env)
├── README.md
├── LICENSE
└── .gitignore
```

</details>

<details>

<summary> 📤 Output Files & SQL Loader Guide</summary> 

#### Expected Data Exports

After running the generator, you'll find in the `output/` folder:
- `orders.csv`, `order_items.csv`, `returns.csv`, etc.
- `load_data.sql` — A ready-to-run script for loading data into Postgres or SQLite.

#### `load_data.sql` (for SQLite)
A script, generated from your YAML table schema, that builds the database from your data.
  - This script includes:
    - `CREATE TABLE` statements with inferred schema
    - `COPY` or `INSERT` statements to populate the tables
  - How to Use load_data.sql
    1. Open your SQL client (e.g., pgAdmin, DBeaver, terminal psql, SQLite CLI).
	2. Connect to your database (Postgres or SQLite recommended).
	3. Run the script:

For SQLite:
```bash
sqlite3 your_database.db < output/load_data.sql
```
>This creates all tables and imports your data — ready for analysis or training.
___

</details>

<details>

<summary>🛠️ Basic Troubleshooting</summary>

- **`ModuleNotFoundError` for `ecomgen`?**  
  Make sure you ran `pip install -e .` from the project root.

- **`yaml.YAMLError` when loading config?**  
  Check your indentation — YAML is very picky!

- **Output files not showing up?**  
  Confirm you ran the generator and check the `output/` folder.

</details>

<details>

<summary>💡 Sample AI Prompt for Scenario Design</summary>

Use this data generator alongside AI to create realistic business analysis scenarios. For the best results, upload your generated database to enable context-aware assistance.

```text
I have a synthetic e-commerce dataset with tables for orders, returns, customers, and products. 
Please help me design a business scenario that reflects a real-world problem an analyst might face.

Include a short background, 2–3 guiding business questions, and examples of SQL queries that could help answer them.
```

</details>

---

## ▶️ Setup 

### 🔩 Configuration Setup

Use the YAML-based configuration system to control the size, structure, and messiness of your generated data.

<details>
<summary><strong>🧰 YAML Template</strong></summary>

- **File:** [`📝 ecom_sales_gen_template.yaml`](config/ecom_sales_gen_template.yaml)
- **Purpose:** Defines how much data is generated, what kind of products are included, and the messiness level of the output.  
- **Use case:** Start here for most use cases. Adjust row counts, return rates, vocab, etc.

</details>

<details>
<summary><strong>📖 Full Config Guide</strong></summary>

- **File:** [`📘 CONFIG_GUIDE.md`](./CONFIG_GUIDE.md)
- **Purpose:** Explains how the YAML configuration works 
- **Use case:** Perfect when you're creating your own custom scenario or tweaking advanced parameters

</details>

### 📦 Dev Setup

Clone the repo and install in editable mode to enable local development:

```bash
# Clone repo and install in editable mode
git clone https://github.com/G-Schumacher44/ecom_sales_data_generator.git
cd ecom_sales_data_generator
pip install -e .
```

*Or set up the Conda environment:*

```bash
conda env create -f environment.yml
conda activate ecom_data_gen
```
___

### ▶️ CLI Usage

**Standard clean generation:**

```bash
ecomgen --config config/ecom_sales_gen_template.yaml --messiness-level baseline
```

___

## 🧪 Testing and Validation Guide

This project includes a comprehensive testing framework to ensure the integrity and quality of the synthetic data. Running these tests is highly recommended, especially after making changes to the configuration or generating new datasets.

For a detailed breakdown of each test suite, see the [**🧪 Testing and Validation Guide**](./TESTING_GUIDE.md).

<details>
<summary>🎯 Test Objectives</summary>

- **Config Integrity:** Ensure the YAML config is correctly structured and all required parameters are present.
- **Data Quality Rules:** Validate linkages (e.g., `order_id` in `returns` exists in `orders`), logic (e.g., refund ≤ order total), and schema expectations.
- **Messiness Audits:** Assess the applied messiness level (e.g., null injection, typos, formatting issues).

</details>

<details>
<summary>🛠️ Running the Tests</summary>

The two primary ways to test the system are:
1.  **Main QA Suite**: This runs automatically with the `ecomgen` command and validates the final data output.
2.  **Pytest Suite**: This is for developers to test the core logic in isolation.

- `test_config_integrity.py` – Confirms all required YAML fields exist
- `test_config_linting.py` – Lints YAML for structure and syntax
- `test_data_quality_rules.py` – Validates core business rules (e.g., referential integrity)

**Run them:**
```bash
pytest src/pytests/
```

</details>

___

## 🤝 On Generative AI Use

Generative AI tools (Gemini 2.5-PRO, ChatGPT 4o - 4.1) were used throughout this project as part of an integrated workflow — supporting code generation, documentation refinement, and idea testing. These tools accelerated development, but the logic, structure, and documentation reflect intentional, human-led design. This repository reflects a collaborative process: where automation supports clarity, and iteration deepens understanding.

---

## 📦 Licensing

This project is licensed under the [MIT License](LICENSE).</file>

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