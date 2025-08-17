<p align="center">
  <img src="repo_files/dark_logo_banner.png" width="1000"/>
  <br>
  <em>Retail Scenario Data Generator + QA Framework</em>
</p>

<p align="center">
  <img alt="MIT License" src="https://img.shields.io/badge/license-MIT-blue">
  <img alt="Status" src="https://img.shields.io/badge/status-alpha-lightgrey">
  <img alt="Version" src="https://img.shields.io/badge/version-v0.2.0-blueviolet">
</p>

---

# ⚙️ Configuration Guide

This guide explains how to structure and modify the YAML configuration file [`📝 ecom_sales_gen_template.yaml`](config/ecom_sales_gen_template.yaml) to control the data generation process. Each section of the YAML allows you to fine-tune row counts, category distributions, vocabularies, and messiness parameters.

> ⬅️ [Back to Project README](README.md)

---

## 📚 Table of Contents

- ⚙️ Configuration Guide
  - 📚 Table of Contents
  - 📁 Top-Level Sections
  - 📊 Key Simulation Parameters
    - Sales Funnel & Conversion
    - Customer Lifecycle & Cohort Analysis
    - Returns
    - Order & Channel Behavior
  - 📋 Tables vs. Lookup Config
  - 🧪 Experimenting

## 📁 Top-Level Sections

The YAML file is organized into several key sections:

- **`row_generators`**: Maps table names to the specific Python generator functions responsible for creating their data.
- **`output_dir`**: Specifies the directory where all generated CSV files and the SQL loader script will be saved.
- **`faker_seed`**: A seed value for the Faker library to ensure that generated data (like names and addresses) is reproducible across runs.
- **`tables`**: Defines the schema and generation rules for transactional tables like `shopping_carts`, `orders`, and `returns`.
- **`lookup_config`**: Defines the generation rules for foundational lookup tables like `customers` and `product_catalog`.
- **`vocab`**: Contains lists of controlled vocabulary used to populate categorical fields (e.g., `payment_methods`, `shipping_speeds`).
- **`parameters`**: A powerful section for controlling the core logic and statistical properties of the simulation.
- **`channel_rules`**: Allows for defining specific business rules that apply to different order channels (e.g., "Web" vs. "Phone").

---

## 📊 Key Simulation Parameters

The `parameters` section is where you control the most important aspects of the business simulation.

### Sales Funnel & Conversion

`conversion_rate`:
- **What it is**: The probability that a `shopping_cart` will be successfully converted into an `order`.
- **Example**: A value of `0.08` means that, on average, 8% of all created shopping carts will become completed sales. The rest are considered "abandoned."
- **Use Case**: Set this low (e.g., `0.03`) to simulate a struggling retailer or higher (e.g., `0.12`) for a more successful one.

### Customer Lifecycle & Cohort Analysis

`repeat_purchase_settings`:
- This block controls the logic for customers returning to make subsequent purchases after their first one.
- **`propensity_by_tier`**: Defines the probability that a customer in a given `loyalty_tier` will return to create another shopping cart. This is the primary driver for repeat purchase behavior.
- **`time_delay_days_range`**: A range of days (e.g., `[20, 150]`) that determines the randomized time gap between a customer's visits. This is essential for realistic, time-based cohort analysis.

### Returns

`return_rate`:
- **What it is**: The percentage of total `orders` that will have a corresponding `return` generated.
- **Example**: A value of `0.25` means the system will generate returns for approximately 25% of all successfully placed orders.
- **Use Case**: This ensures that the volume of returns scales realistically with the volume of sales.

`category_return_rates`:
- **What it is**: Allows you to set different return propensities for different product categories.
- **Example**: You can set `electronics` to have a higher return rate (`0.35`) than `books` (`0.05`) to simulate real-world product differences.

### Order & Channel Behavior

`order_channel_distribution`:
- **What it is**: A weighted distribution that determines the likelihood of an order originating from a specific channel (e.g., Web, Phone, Social Media).

`channel_rules`:
- **What it is**: A section to define rules specific to an order channel.
- **Example**: You can specify that orders from the `"Ebay"` channel are only allowed to use the `"Ebay"` `payment_method`, while `"Web"` orders can use a broader range of options.

---

## 📋 Tables vs. Lookup Config

It's important to understand the distinction between these two sections.

- **`lookup_config`**: Use this to generate your foundational, "lookup" tables. These are tables that other tables depend on, like `customers` and `product_catalog`. The generator runs this section first to create a cache of customers and products.
- **`tables`**: Use this for all other transactional tables that are generated *after* the lookups are created. This includes `shopping_carts`, `orders`, `returns`, and their corresponding item tables.

By separating these, the configuration remains logical and easy to follow.

---

## 🧪 Experimenting

The best way to learn is to experiment! Try changing the `conversion_rate` or the `propensity_by_tier` and see how it affects the final number of orders and the overall shape of your dataset.

---

🔝 [Back to Top](#top) | ⬅️ [Back to Project README](README.md)

