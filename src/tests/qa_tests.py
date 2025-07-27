import argparse
import os
import pandas as pd
import logging
import sys
from collections import defaultdict, Counter
from datetime import datetime
from src.utils.config import Config

# Custom warning exception to differentiate warnings from errors
class QAWarning(Warning):
    pass

# Setup logging
logger = logging.getLogger("qa_tests")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(levelname)s: %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

# Messiness severity config
MESSINESS_LEVELS = {
    "baseline": {"fail_on_warning": True},
    "light_mess": {"fail_on_warning": False},
    "medium_mess": {"fail_on_warning": False},
    "heavy_mess": {"fail_on_warning": False},
}

def handle_issue(message, messiness, level="error"):
    """
    Handle QA issues based on messiness and severity.
    level: 'error' or 'warn'
    """
    if level == "warn":
        if MESSINESS_LEVELS[messiness]["fail_on_warning"]:
            logger.error(message)
            raise ValueError(message)
        else:
            logger.warning(message)
    elif level == "error":
        logger.error(message)
        raise ValueError(message)
    else:
        logger.info(message)

def load_csv_as_dict(filepath):
    df = pd.read_csv(filepath)
    return df.to_dict(orient='records')

### --- Baseline QA functions ---

def validate_numeric_fields(order_items, return_items, messiness):
    for item in order_items:
        qty_raw = item.get("quantity")
        try:
            qty = int(qty_raw)
            if qty <= 0 or qty > 100:
                handle_issue(f"Invalid quantity '{qty_raw}' in order_item {item.get('order_id')}", messiness)
        except Exception:
            handle_issue(f"Invalid quantity '{qty_raw}' in order_item {item.get('order_id')}", messiness)
        try:
            price = float(item.get("unit_price", -1))
            if price < 0:
                handle_issue(f"Invalid or negative unit_price '{item.get('unit_price')}' in order_item {item.get('order_id')}", messiness)
        except Exception:
            handle_issue(f"Invalid or negative unit_price '{item.get('unit_price')}' in order_item {item.get('order_id')}", messiness)
    for item in return_items:
        qty_raw = item.get("quantity_returned")
        try:
            qty = int(qty_raw)
            if qty <= 0 or qty > 100:
                handle_issue(f"Invalid quantity_returned '{qty_raw}' in return_item {item.get('return_item_id')}", messiness)
        except Exception:
            handle_issue(f"Invalid quantity_returned '{qty_raw}' in return_item {item.get('return_item_id')}", messiness)
        try:
            price = float(item.get("unit_price", -1))
            if price < 0:
                handle_issue(f"Invalid or negative unit_price '{item.get('unit_price')}' in return_item {item.get('return_item_id')}", messiness)
        except Exception:
            handle_issue(f"Invalid or negative unit_price '{item.get('unit_price')}' in return_item {item.get('return_item_id')}", messiness)
        try:
            refunded = float(item.get("refunded_amount", -1))
            if refunded < 0:
                handle_issue(f"Invalid or negative refunded_amount '{item.get('refunded_amount')}' in return_item {item.get('return_item_id')}", messiness)
        except Exception:
            handle_issue(f"Invalid or negative refunded_amount '{item.get('refunded_amount')}' in return_item {item.get('return_item_id')}", messiness)
    logger.info("✅ Numeric fields in order_items and return_items are valid and sane.")

def validate_unique_ids(orders, returns, return_items, messiness):
    def check_unique(items, key, name):
        ids = [item.get(key) for item in items]
        duplicates = [x for x, c in Counter(ids).items() if c > 1]
        if duplicates:
            handle_issue(f"Duplicate {key} values found in {name}: {duplicates}", messiness)
    check_unique(orders, "order_id", "orders")
    check_unique(returns, "return_id", "returns")
    check_unique(return_items, "return_item_id", "return_items")
    logger.info("✅ All IDs in orders, returns, and return_items are unique.")

def validate_catalog_schema(catalog, messiness):
    required_fields = {"product_id", "product_name", "category", "unit_price"}
    for idx, product in enumerate(catalog):
        missing = required_fields - product.keys()
        if missing:
            handle_issue(f"Product at index {idx} is missing fields: {missing}", messiness)
        try:
            price = float(product["unit_price"])
            if price < 0:
                handle_issue(f"Negative unit_price in product at index {idx}: {price}", messiness)
        except Exception:
            handle_issue(f"Invalid unit_price in product at index {idx}: {product['unit_price']}", messiness)
    logger.info("✅ Product catalog schema is valid.")
    return True

def validate_return_refunds(returns, return_items, messiness, tolerance=0.01):
    sums = defaultdict(float)
    for ri in return_items:
        rid = ri.get("return_id")
        try:
            amt = float(ri.get("refunded_amount", 0) or 0)
        except Exception:
            amt = 0.0
        if rid is not None:
            sums[rid] += amt
    for ret in returns:
        rid = ret.get("return_id")
        try:
            ret_amt = float(ret.get("refunded_amount", 0) or 0)
        except Exception:
            ret_amt = 0.0
        items_sum = sums.get(rid, 0.0)
        if abs(ret_amt - items_sum) > tolerance:
            handle_issue(
                f"Refunded amount mismatch for return_id {rid}: returns={ret_amt}, sum of return_items={items_sum}",
                messiness,
            )
    logger.info("✅ All returns.refunded_amount values match the sum of their return_items.refunded_amount.")

def validate_date_fields(orders, returns, messiness):
    for order in orders:
        order_date = order.get("order_date")
        try:
            datetime.strptime(order_date, "%Y-%m-%d")
        except Exception:
            handle_issue(f"Invalid order_date format: {order_date} in order {order.get('order_id')}", messiness)
    for ret in returns:
        return_date = ret.get("return_date")
        order_date = None
        for order in orders:
            if order.get("order_id") == ret.get("order_id"):
                order_date = order.get("order_date")
                break
        try:
            r_date = datetime.strptime(return_date, "%Y-%m-%d")
            o_date = datetime.strptime(order_date, "%Y-%m-%d") if order_date else None
            if o_date and r_date < o_date:
                handle_issue(f"Return date {return_date} before order date {order_date} for return {ret.get('return_id')}", messiness)
        except Exception:
            handle_issue(f"Invalid return_date format: {return_date} in return {ret.get('return_id')}", messiness)
    logger.info("✅ All order_date and return_date fields valid and logically consistent.")

def validate_customer_references(customers, orders, returns, messiness):
    customer_ids = {c["customer_id"] for c in customers}
    guest_ids = {c["customer_id"] for c in customers if c.get("customer_status", "").lower() == "guest"}
    all_valid_customer_ids = customer_ids.union(guest_ids)
    invalid_order_customers = {o["customer_id"] for o in orders if o["customer_id"] not in all_valid_customer_ids}
    invalid_return_customers = {r["customer_id"] for r in returns if r["customer_id"] not in all_valid_customer_ids}
    if invalid_order_customers:
        handle_issue(f"Orders reference unknown customer_id(s): {invalid_order_customers}", messiness)
    if invalid_return_customers:
        handle_issue(f"Returns reference unknown customer_id(s): {invalid_return_customers}", messiness)
    logger.info("✅ All customer references in orders and returns are valid.")

def test_agent_assignments(config, data_dir, messiness):
    agent_pool = getattr(config, 'vocab', {}).get('agent_pool', {})
    agents = agent_pool.get('agents', [])
    config_agents = set(agent['id'] for agent in agents)

    orders = load_csv_as_dict(os.path.join(data_dir, "orders.csv"))
    returns = load_csv_as_dict(os.path.join(data_dir, "returns.csv"))

    for order in orders:
        order_channel = order["order_channel"]
        agent_id = order.get("agent_id")
        if order_channel == "Phone":
            if agent_id not in config_agents:
                handle_issue(f"Order {order['order_id']} has invalid agent_id {agent_id}", messiness, level="warn")
        else:
            if agent_id != "ONLINE":
                handle_issue(f"Order {order['order_id']} should have agent_id 'ONLINE'", messiness, level="warn")

    for ret in returns:
        return_channel = ret["return_channel"]
        agent_id = ret.get("agent_id")
        if return_channel == "Phone":
            if agent_id not in config_agents:
                handle_issue(f"Return {ret['return_id']} has invalid agent_id {agent_id}", messiness, level="warn")
        else:
            if agent_id != "ONLINE":
                handle_issue(f"Return {ret['return_id']} should have agent_id 'ONLINE'", messiness, level="warn")

    logger.info("✅ Agent assignment QA tests passed.")

### --- Big Audit functions ---

# Placeholder: you can integrate your big_audit.py functions here with similar messiness control.
# For example:
def big_audit_fk_integrity(orders, order_items, returns, return_items, messiness):
    # Check that order_items.order_id exists in orders
    order_ids = {o["order_id"] for o in orders}
    for oi in order_items:
        if oi["order_id"] not in order_ids:
            handle_issue(f"order_item with order_id {oi['order_id']} has no matching order", messiness)
    # Similarly for returns and return_items
    return_ids = {r["return_id"] for r in returns}
    for ri in return_items:
        if ri["return_id"] not in return_ids:
            handle_issue(f"return_item with return_id {ri['return_id']} has no matching return", messiness)
        if ri["order_id"] not in order_ids:
            handle_issue(f"return_item with order_id {ri['order_id']} has no matching order", messiness)
    logger.info("✅ Referential integrity checks passed.")

def big_audit_statistical_checks(orders, returns, messiness):
    # Example: check plausible return rate
    total_orders = len(orders)
    total_returns = len(returns)
    return_rate = total_returns / total_orders if total_orders else 0
    if return_rate > 0.5:
        handle_issue(f"High return rate detected: {return_rate:.2%}", messiness, level="warn")
    logger.info("✅ Statistical audits completed.")

### --- Main ---

def main():
    parser = argparse.ArgumentParser(description="Run QA and Big Audit on generated data.")
    parser.add_argument("--data-dir", type=str, default="story_01_upstart_retailer/data/output",
                        help="Directory where CSV output files are located")
    parser.add_argument("--run-big-audit", action="store_true",
                        help="Run the big audit checks in addition to baseline QA")
    parser.add_argument("--messiness", type=str, choices=["baseline", "light_mess", "medium_mess", "heavy_mess"],
                        default="baseline", help="Level of messiness tolerance for QA")

    args = parser.parse_args()
    data_dir = args.data_dir
    run_big_audit = args.run_big_audit
    messiness = args.messiness

    config = Config()

    # Load data
    orders = load_csv_as_dict(os.path.join(data_dir, "orders.csv"))
    returns = load_csv_as_dict(os.path.join(data_dir, "returns.csv"))
    return_items = load_csv_as_dict(os.path.join(data_dir, "return_items.csv"))
    order_items = load_csv_as_dict(os.path.join(data_dir, "order_items.csv"))
    customers = load_csv_as_dict(os.path.join(data_dir, "customers.csv"))
    catalog = load_csv_as_dict(os.path.join(data_dir, "product_catalog.csv"))

    # Run baseline QA tests
    validate_numeric_fields(order_items, return_items, messiness)
    validate_unique_ids(orders, returns, return_items, messiness)
    validate_catalog_schema(catalog, messiness)
    validate_return_refunds(returns, return_items, messiness)
    validate_date_fields(orders, returns, messiness)
    validate_customer_references(customers, orders, returns, messiness)
    test_agent_assignments(config, data_dir, messiness)

    # Optionally run big audit tests
    if run_big_audit:
        big_audit_fk_integrity(orders, order_items, returns, return_items, messiness)
        big_audit_statistical_checks(orders, returns, messiness)
        # Add more big audit calls here as you integrate them

    logger.info("✅ All requested QA and audits completed successfully.")

if __name__ == "__main__":
    main()
