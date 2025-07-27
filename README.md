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

---

# 🛒 Ecommerce Sales Data Generator

A YAML-configurable Python engine for generating synthetic e-commerce sales data — built for SQL training, analytics storytelling, and realistic pipeline testing. Features a modular structure, configurable messiness, and test suites for quality assurance.
>📸 See it in action: [SQL Stories Demo](https://github.com/G-Schumacher44/sql_stories)

___

## 🧩 TLDR;

- Generate synthetic, realistic e-commerce data (orders, returns, customers, etc.)
- YAML-controlled configuration of row volumes, faker behavior, return rates, etc.
- Plug-and-play messiness injection (via --messiness-level flag) for simulating real-world inconsistencies 
- Built-in QA tests: referential integrity, refund audits, return rate checks
- CLI runner, Pytest test suite, and optional big/mess audit extensions
- Designed for SQL project demos, portfolio datasets, and analytics onboarding

<details>
<summary> ⏯️ Quick Start</summary>

1. Clone the repository  
   ```bash
   git clone https://github.com/your-username/ecom_sales_data_generator.git
   cd ecom_sales_data_generator. Install in editable mode  
   ```bash
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
- **QA Framework**: Hard-fail QA scripts and Pytest modules to catch data issues automatically
- **CLI Interface**: One-command generation + validation from terminal or VS Code tasks
- **Editable Dev Mode**: Install via `pip install -e .` for active development and local CLI usage

---

### 🧭 Orientation & Getting Started

<details>
<summary><strong>🧠 Notes from the Dev Team</strong></summary>
<br>

**Task and Purpose**

I built this system to reinforce, refresh, and evaluate my SQL skills through practical, repeatable analysis. Rather than relying on static datasets, I wanted something dynamic — a way to simulate the kinds of data challenges analysts face every day, with full control over volume, structure, and messiness.

**Why build a system and not just a script?**

You can see this engine in action in [SQL Stories Demo](https://github.com/G-Schumacher44/sql_stories), where I use AI-generated prompts to simulate realistic business scenarios and investigative workflows. This pairing gives me an unlimited sandbox to practice SQL storytelling, data diagnostics, and real-world problem solving — all powered by the datasets generated here.

**Human-readable. YAML-driven. Designed for learning.**

</details>

<details>
<summary><strong>🫆 Version Release Notes</strong></summary>

### ✅ v0.1.0 (Current)

- First production-ready release
- YAML-driven sales data generator with support for:
  - orders, order_items, returns, customers, and products
  - messiness injection (light/medium/heavy)
  - embedded CLI and Pytest-driven QA suite
  - config validation and baseline data audits
- Tested with `sql_stories` for simulated analytics workflows

---

### 🔮 v0.2.0 (Planned)

- Simulated data spike events - e.g., *"holiday sales surge"*, *"flash sales"*, ect..ect.
- B2B purchase logic: lines of credit, bulk buying behavior
- Reseller segmentation: cohort rules, volume-based discounts
- Shipping & fulfillment enrichment: lead times, delivery lag, backorders
- Marketing program metadata: coupons, campaign IDs
- Warehousing & inventory extension (WMS simulation layer)

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

#### `Expected Data Exports`

After running the generator, you'll find in the `output/` folder:
- `orders.csv`, `order_items.csv`, `returns.csv`, etc.
- `load_data.sql` — ready-to-run script for loading into Postgres or SQLite

#### `load_data.sql`
A YAML Schema defined Script that builds the database from your data
  - This script includes:
    - `CREATE TABLE` statements with inferred schema
    - `COPY` or `INSERT` statements to populate the tables
  - How to Use load_data.sql
    1. Open your SQL client (e.g., pgAdmin, DBeaver, terminal psql, SQLite CLI)
	2.	Connect to your database (Postgres or SQLite recommended)
	3.	Run the script:

For Postgres (terminal):
```bash
psql -U your_user -d your_database -f output/load_data.sql
```

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
<summary><strong>📖 Config Guide</strong></summary>

- **File:** [`📘 config_guide`](config_guide.md)  
- **Purpose:** Explains each YAML field line-by-line  
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
ecomgen --config config/ecom_sales_gen_template.yaml --messiness-level none
```

___

## 🧪 Testing and Validation Guide

This project includes a comprehensive testing framework to ensure the integrity and quality of the synthetic data. Running these tests is highly recommended, especially after making changes to the configuration or generating new datasets.

<details>
<summary>🎯 Test Objectives</summary>

- **Config Integrity:** Ensure the YAML config is correctly structured and all required parameters are present.
- **Data Quality Rules:** Validate linkages (e.g., `order_id` in `returns` exists in `orders`), logic (e.g., refund ≤ order total), and schema expectations.
- **Messiness Audits:** Assess the applied messiness level (e.g., null injection, typos, formatting issues).

</details>  

---

<details>
<summary>🛠️ Running the Tests</summary>

✅ 1. Pytest Suite — `src/pytests/`

These fast, targeted tests verify configuration structure and baseline data logic.

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

---

## 🔗 Ready to Explore?

Head to the [Config Guide](config_guide.md) to start generating your own custom e-commerce datasets — or visit the [SQL Stories Demo](https://github.com/G-Schumacher44/sql_stories) to see it used in real-world SQL challenges.