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
    - Sales Funnel &amp; Conversion
    - Customer Lifecycle &amp; Behavioral Modeling
    - Earned Customer Value
    - Returns &amp; Refunds
    - Order &amp; Channel Behavior
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

`conversion_rate`: The baseline probability that a `shopping_cart` will be successfully converted into an `order`.

`first_purchase_conversion_boost`: A multiplier that increases the conversion rate for a customer's *first* potential purchase, based on their `signup_channel`. This simulates more effective onboarding for certain channels (e.g., `Phone`).

`time_to_first_cart_days_range`: Controls how many days after signing up a new customer will create their first shopping cart, simulating the initial engagement period.

`abandoned_cart_emptied_prob`: The probability that a cart that is not converted will be marked as `emptied` (with a total of 0 and no items) versus `abandoned` (with items remaining). This helps distinguish between passive abandonment and active disinterest.
### Customer Lifecycle & Behavioral Modeling

This is controlled by the `repeat_purchase_settings` block, which now supports highly stratified behavior.

`propensity_by_channel_and_tier`: This nested mapping defines the average number of repeat visits a customer will make. The simulation first looks for a rule matching the customer's `signup_channel`, then their `loyalty_tier`. This allows you to model scenarios where, for example, a "Gold" tier customer from "Phone" sales is more loyal than a "Gold" tier customer from "Social Media".

`time_delay_by_channel_and_tier`: This defines the time gap between customer visits. It's a nested mapping that specifies both a `range` (in days) and a `sigma` value. The `sigma` controls the variance of a log-normal distribution, allowing you to create "heavy tails" in the data (i.e., more realistic clusters of short and very long gaps between orders).

`cart_behavior_by_tier`: Controls the size and value of a customer's cart based on their `loyalty_tier`. You can define the `item_count_range` (how many different products) and `quantity_range` (how many of each product) to ensure that high-value customers place larger, more valuable orders.

`reactivation_settings`: Simulates long-term churn and reactivation.
- **`probability`**: The chance that a customer who has gone dormant will eventually return to make another purchase.
- **`delay_days_range`**: The long period of inactivity (e.g., 200-400 days) before a potential reactivation.

### Earned Customer Value

A key feature of v0.3.0 is that customer value is no longer pre-assigned; it's **earned**.

`tier_spend_thresholds` & `clv_spend_thresholds`: These mappings define the cumulative spending required to achieve a certain `loyalty_tier` or `clv_bucket`.

The simulation follows a two-step process:
1.  A customer's *initial* `loyalty_tier` is assigned at signup. This initial tier influences their early purchasing behavior (propensity, cart size, etc.).
2.  After all orders are generated, a post-processing step calculates each customer's total lifetime spend and **re-assigns** their final `loyalty_tier` and `clv_bucket` based on the thresholds. This ensures the final dataset reflects a realistic progression of customer value.

### Returns & Refunds

`return_rate_by_signup_channel`: Sets the baseline probability of a return based on the customer's acquisition channel. This allows you to model higher return rates for impulse-buy channels like "Social Media".

`refund_behavior_by_reason`: This mapping makes refund amounts more realistic. Based on the `reason` for a return (e.g., "Defective" vs. "Changed mind"), you can control the probability of a full refund (`full_return_prob`) vs. a partial refund of a line item (`partial_quantity_prob`).

`return_timing_distribution`: Creates a realistic long tail for returns. You can specify what percentage of returns occur within 30, 90, or 365 days.

### Order & Channel Behavior

`order_channel_distribution`: A weighted distribution for the channel of any given order.

`category_preference_by_signup_channel`: Skews the product categories a customer is likely to purchase from based on their `signup_channel`. For example, you can make "Social Media" customers more likely to buy "electronics" and "toys".

`channel_rules`: Defines channel-specific business logic, such as which `payment_methods` are allowed for "Web" vs. "Phone" orders.

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
