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

# 📘 Config Guide for ecom_sales_data_generator

This guide explains how to structure and modify the YAML configuration file (`ecom_sales_gen_template.yaml`) to control the data generation process. Each section of the YAML allows you to fine-tune row counts, category distributions, vocabularies, and messiness parameters.

> 📄 Default Config: [`config/ecom_sales_gen_template.yaml`](config/ecom_sales_gen_template.yaml)

---

## 📚 Table of Contents

- [� Config Guide for ecom\_sales\_data\_generator](#-config-guide-for-ecom_sales_data_generator)
  - [📚 Table of Contents](#-table-of-contents)
  - [📁 Top-Level Sections](#-top-level-sections)
    - [`row_counts`](#row_counts)
    - [`row_generators`](#row_generators)
    - [`lookup_tables`](#lookup_tables)
    - [`baseline_return_reason_weights`](#baseline_return_reason_weights)
    - [`vocab`](#vocab)
    - [`messiness_settings`](#messiness_settings)
    - [`parameters`](#parameters)
  - [🛠️ Notes](#️-notes)
    - [`tables` (Advanced Schema Definitions)](#tables-advanced-schema-definitions)
    - [`channel_rules`](#channel_rules)
  - [🔁 `Testing and Validation`](#testing-and-validation)


>⬅️ [Back to Project README](README.md)
___

## 📁 Top-Level Sections

### `tables` → `generate`

Row counts are now defined directly within each entry under the `tables` section using the `generate` field.

```yaml
tables:
  - name: customers
    generate: 1000
    columns:
      - name: customer_id
        type: TEXT
```

---

### `row_generators`
Specify the Python function path to use for generating each table. The generator must return a list of dictionaries (rows). These paths must align with your `src/generators/` directory.

```yaml
row_generators:
  orders: generators.generator_orders.generate_orders
  returns: generators.generator_returns.generate_returns
```

---

### `lookup_config`
Define generation rules and parameters for cached lookup tables like customers or products. These values are reused across other tables and help maintain consistency in the dataset.

```yaml
lookup_tables:
  customer_status: ["active", "inactive", "guest"]
  order_channels: ["web", "phone"]
  categories: ["electronics", "clothing", "books"]
```

---

### `baseline_return_reason_weights`
Set the percentage distribution of return reasons by category. All sub-values per category **must sum to 1.0**.

```yaml
baseline_return_reason_weights:
  clothing:
    wrong_size: 0.4
    changed_mind: 0.3
    damaged: 0.3
```

---

### `vocab`
Define randomization pools for names, brands, categories, and SKUs.

```yaml
vocab:
  first_names: ["Alice", "Bob", "Charlie"]
  product_brands: ["TechCo", "StyleInc"]
  product_categories: ["gadgets", "accessories"]
```

---

### `messiness_settings`
Control the amount and type of simulated data mess injected into the dataset. These will only take effect if `--messiness-level` is set to anything other than `none`.

```yaml
messiness_settings:
  nulls:
    enabled: true
    columns: ["email", "gender"]
    null_rate: 0.1
  typos:
    enabled: true
    columns: ["product_name"]
    typo_rate: 0.05
```

---

### `parameters`
Control core behavior patterns in the simulation — customer signup history, shipping costs, return lags, etc.

```yaml
parameters:
  signup_years: 1
  order_days_back: 365
  expedited_pct: 20
  shipping_costs:
    Standard: 5.0
    Two-Day: 45.0
```

Use `category_return_rates` and `baseline_return_reason_weights` to influence return dynamics by product type.

---

## 🛠️ Notes

- **Messiness Levels**: The CLI accepts one of four levels: `none`, `light_mess`, `medium_mess`, `heavy_mess`. These toggle how aggressively the `messiness_settings` are applied.
- **Referential Integrity**: All generated rows will link logically across tables (e.g., returns must match existing orders).
- **Optional Customization**: You can expand vocab or return reasons freely as long as the YAML remains valid.

---

### `tables` (Advanced Schema Definitions)
Each table can include custom rules such as conditional requirements or logic-based linkages:

```yaml
- name: mailing_address
  type: TEXT
  required_if_signup_channel_in: ["Website", "Phone"]

- name: loyalty_enrollment_date
  type: DATE
  required_if_loyalty_tier_present: true

- name: clv_bucket
  type: TEXT
  linked_to_loyalty_tier: true
```

---

### `channel_rules`
Override behavior based on the `order_channel` field. You can define allowed payment methods and preferred return channels per channel.

```yaml
channel_rules:
  Web:
    allowed_payment_methods: ["Credit Card", "ACH", "PayPal"]
    return_channel_preference: "Web"
```

---

### `Testing and Validation`

### 🔁 Quick Validation Loop

```bash
# Run generation
ecomgen --config config/ecom_sales_gen_template.yaml --messiness-level light_mess

# Run Pytest QA
pytest src/pytests/
```

---

## 🧪 PyTest Validation

After editing the config, you can run Pytest to validate structure and weights:

```bash
pytest src/pytests/
```

---

🔝 [Back to Top](#table-of-contents) | ⬅️ [Return to Project README](README.md)