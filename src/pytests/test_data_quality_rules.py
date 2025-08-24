

import pandas as pd
from pathlib import Path
import pytest

# --- Uniqueness Tests ---

def test_orders_have_unique_ids():
    df = pd.read_csv("output/orders.csv")
    assert df["order_id"].is_unique, "Duplicate order_id values found in orders.csv"

def test_customers_have_unique_ids():
    df = pd.read_csv("output/customers.csv")
    assert df["customer_id"].is_unique, "Duplicate customer_id values found in customers.csv"

def test_products_have_unique_ids():
    df = pd.read_csv("output/product_catalog.csv")
    assert df["product_id"].is_unique, "Duplicate product_id values found in product_catalog.csv"

# --- Referential Integrity Tests ---

def test_order_items_match_orders():
    orders = pd.read_csv("output/orders.csv")
    order_items = pd.read_csv("output/order_items.csv")
    missing = order_items[~order_items["order_id"].isin(orders["order_id"])]
    assert missing.empty, f"{len(missing)} order_items reference missing orders"

def test_order_items_link_to_valid_products():
    order_items = pd.read_csv("output/order_items.csv")
    products = pd.read_csv("output/product_catalog.csv")
    missing = order_items[~order_items["product_id"].isin(products["product_id"])]
    assert missing.empty, f"{len(missing)} order_items reference missing products"

def test_orders_link_to_valid_customers():
    orders = pd.read_csv("output/orders.csv")
    customers = pd.read_csv("output/customers.csv")
    missing = orders[~orders["customer_id"].isin(customers["customer_id"])]
    assert missing.empty, f"{len(missing)} orders reference missing customers"

def test_return_items_match_returns():
    returns = pd.read_csv("output/returns.csv")
    return_items = pd.read_csv("output/return_items.csv")
    missing = return_items[~return_items["return_id"].isin(returns["return_id"])]
    assert missing.empty, f"{len(missing)} return_items reference missing returns"

def test_returns_link_to_valid_orders():
    returns = pd.read_csv("output/returns.csv")
    orders = pd.read_csv("output/orders.csv")
    missing = returns[~returns["order_id"].isin(orders["order_id"])]
    assert missing.empty, f"{len(missing)} returns reference missing orders"

# --- Logical Consistency Tests ---

def test_refunded_amount_not_exceed_unit_price():
    ri = pd.read_csv("output/return_items.csv")
    # Round the calculated total to 2 decimal places to match the rounding
    # applied to refunded_amount during generation. This avoids floating point
    # precision issues where `round(x*y, 2)` can be slightly larger than the
    # raw float result of `x*y`.
    calculated_total = (ri["unit_price"] * ri["quantity_returned"]).round(2)
    overpaid = ri[ri["refunded_amount"] > calculated_total]
    assert overpaid.empty, f"{len(overpaid)} return_items have excessive refunded amounts. Sample:\n{overpaid.head()}"

def test_return_date_after_order_date():
    returns = pd.read_csv("output/returns.csv")
    orders = pd.read_csv("output/orders.csv")
    merged = pd.merge(returns, orders[['order_id', 'order_date']], on='order_id', how='left')
    # Drop rows where order_date might be missing due to a failed merge (already caught by other tests)
    merged.dropna(subset=['order_date', 'return_date'], inplace=True)
    # Convert to datetime for comparison
    merged['return_date_dt'] = pd.to_datetime(merged['return_date'])
    merged['order_date_dt'] = pd.to_datetime(merged['order_date'])
    invalid_dates = merged[merged['return_date_dt'] < merged['order_date_dt']]
    assert invalid_dates.empty, f"{len(invalid_dates)} returns have a return_date before the order_date. Sample:\n{invalid_dates.head()}"

def test_order_date_after_signup_date():
    orders = pd.read_csv("output/orders.csv")
    customers = pd.read_csv("output/customers.csv")
    merged = pd.merge(orders, customers[['customer_id', 'signup_date']], on='customer_id', how='left')
    merged.dropna(subset=['order_date', 'signup_date'], inplace=True)
    merged['order_date_dt'] = pd.to_datetime(merged['order_date'])
    merged['signup_date_dt'] = pd.to_datetime(merged['signup_date'])
    invalid_dates = merged[merged['order_date_dt'] < merged['signup_date_dt']]
    assert invalid_dates.empty, f"{len(invalid_dates)} orders occurred before the customer's signup_date. Sample:\n{invalid_dates.head()}"