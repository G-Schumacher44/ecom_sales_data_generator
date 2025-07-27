

import pandas as pd
from pathlib import Path
import pytest

def test_orders_have_unique_ids():
    df = pd.read_csv("output/orders.csv")
    assert df["order_id"].is_unique, "Duplicate order_id values found in orders.csv"

def test_order_items_match_orders():
    orders = pd.read_csv("output/orders.csv")
    order_items = pd.read_csv("output/order_items.csv")
    missing = order_items[~order_items["order_id"].isin(orders["order_id"])]
    assert missing.empty, f"{len(missing)} order_items reference missing orders"

def test_return_items_match_returns():
    returns = pd.read_csv("output/returns.csv")
    return_items = pd.read_csv("output/return_items.csv")
    missing = return_items[~return_items["return_id"].isin(returns["return_id"])]
    assert missing.empty, f"{len(missing)} return_items reference missing returns"

def test_refunded_amount_not_exceed_unit_price():
    ri = pd.read_csv("output/return_items.csv")
    # Round the calculated total to 2 decimal places to match the rounding
    # applied to refunded_amount during generation. This avoids floating point
    # precision issues where `round(x*y, 2)` can be slightly larger than the
    # raw float result of `x*y`.
    calculated_total = (ri["unit_price"] * ri["quantity_returned"]).round(2)
    overpaid = ri[ri["refunded_amount"] > calculated_total]
    assert overpaid.empty, f"{len(overpaid)} return_items have excessive refunded amounts. Sample:\n{overpaid.head()}"