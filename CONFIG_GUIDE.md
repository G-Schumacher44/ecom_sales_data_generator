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

`order_days_back`: Defines the total duration of the simulation in days (e.g., 365 for one year). All generated events, from signups to orders and returns, will occur within this time window, ending on the current date.

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

### Event-Driven & Seasonal Behavior

`retention_shocks`: Simulates external events that affect customer loyalty. You can define a multiplier for repeat visit propensity for customers who signed up in a specific month (`YYYY-MM`). A value `< 1.0` models increased churn, while `> 1.0` models re-engagement.

`seasonal_factors`: Simulates volume spikes for events like holiday sales. The value is a multiplier for cart volume in a given month, creating non-flat cohort shapes and more realistic sales patterns.

### Product & Profitability

`cost_price_margin_range`: A parameter in the `product_catalog` lookup configuration that defines the product's cost as a percentage of its `unit_price` (e.g., `[0.4, 0.7]` means cost is 40-70% of retail). This is used to generate the `cost_price` for each product.

The `cost_price` is then snapshotted into the `order_items` and `return_items` tables at the time of transaction. This ensures that historical margin analysis remains accurate even if product costs in the main catalog change over time.

### Operational Financials

The `financials` block in the `parameters` section adds another layer of operational cost data. This moves beyond simple revenue vs. product cost (COGS) to enable a much more precise analysis of net margin per order.

- **`shipping_business_costs`**: A block that defines a more realistic model for the business's actual shipping costs.
  - **`base_costs`**: Maps each `shipping_speed` to its base cost for the business (e.g., the rate negotiated with a carrier).
  - **`cost_variance_pct`**: A range (e.g., `[-0.1, 0.1]`) that introduces random variance to the base cost, simulating factors like fuel surcharges or package weight.
This decouples the business's cost from the customer-facing `shipping_cost`, allowing for more precise profitability analysis.
- **`payment_fee_rates`**: A mapping of payment methods to their processing fee percentages (e.g., `Credit Card: 0.025`). This is used to generate the `payment_processing_fee` for each order, calculated on the final `net_total`.
- **`discount_settings`**: Controls the application of discounts at the line-item level. You can set the `probability` of an item being discounted and the `range_pct` for the discount amount. This populates the `discount_amount` in `order_items` and is used to calculate the `gross_total` and `net_total` in the `orders` table.
The total discount for an order is also summed and stored in the `orders.total_discount_amount` column for easier analysis.
This is a random event for each line item, meaning the same product can be discounted in one order but not in another.

### Earned Customer Value

A key feature of v0.3.0 is that a customer's value is not static; it's **earned** over time. The simulation models this in two stages to create a realistic dataset.

`tier_spend_thresholds` & `clv_spend_thresholds`: These mappings define the cumulative spending required to achieve a certain `loyalty_tier` or `clv_bucket`.

1.  **Initial Tier at Signup**: When a customer is first created, they are assigned an `initial_loyalty_tier` based on their `signup_channel`. This initial tier influences their early purchasing behavior (e.g., a "Gold" tier customer might have a higher propensity to buy).
2.  **Evolving Tier at Purchase**: As the simulation generates orders chronologically, it tracks each customer's cumulative spend. The `customer_tier` saved on each `orders` record reflects the customer's status *at that moment in time*.
3.  **Final Tier in Customer Profile**: After all orders are generated, a final calculation is run. The `customers` table is updated so that each customer's `loyalty_tier` and `clv_bucket` reflect their final, up-to-date status based on their total lifetime spending.

This two-stage process ensures that the final `customers` table is a clean, current snapshot of your customer base, while the historical `orders` table contains the rich, evolving data needed for cohort analysis.

### Returns & Refunds

`return_rate`: The global probability that any given order will have at least one return event. This serves as a fallback if no channel-specific rate is defined.

`return_rate_by_signup_channel`: Sets the baseline probability of a return based on the customer's acquisition channel. This allows you to model higher return rates for impulse-buy channels like "Social Media".

`refund_behavior_by_reason`: This mapping makes refund amounts more realistic. Based on the `reason` for a return (e.g., "Defective" vs. "Changed mind"), you can control the probability of a full refund (`full_return_prob`) vs. a partial refund of a line item (`partial_quantity_prob`).

`return_timing_distribution`: Creates a realistic long tail for returns. You can specify what percentage of returns occur within 30, 90, or 365 days.

`multi_return_probability`: The probability that an order that already has one return will have a second, separate return event, simulating more complex customer service scenarios.

### Order & Channel Behavior

`order_channel_distribution`: A weighted distribution for the channel of any given order.

`signup_channel_distribution`: A weighted distribution that controls how new customers are acquired (e.g., 55% from "Website", 15% from "Social Media"). This is foundational for modeling acquisition funnels.

`loyalty_distribution_by_channel`: Defines the probability of a new customer being assigned to an initial loyalty tier (`Bronze`, `Silver`, etc.) based on their `signup_channel`. This allows you to model scenarios where certain channels attract higher-value customers from the start.

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
