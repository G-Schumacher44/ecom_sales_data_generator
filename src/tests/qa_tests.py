import argparse
import os
import pandas as pd
import logging
import sys
from collections import defaultdict, Counter
from datetime import datetime
from utils.config import Config

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

def load_data(data_dir):
    """Loads all CSVs into a dictionary of pandas DataFrames."""
    data_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
    dataframes = {}
    for f in data_files:
        table_name = os.path.splitext(f)[0]
        filepath = os.path.join(data_dir, f)
        try:
            df = pd.read_csv(filepath)
            df.name = table_name # Assign table name to df for better error messages
            dataframes[table_name] = df
        except Exception as e:
            logger.error(f"Failed to load {filepath}: {e}")
            raise
    return dataframes

### --- Baseline QA functions ---

def validate_numeric_fields(dataframes, messiness):
    """Validates numeric fields in order_items and return_items using pandas."""
    if 'order_items' in dataframes:
        df = dataframes['order_items']
        if not pd.to_numeric(df['quantity'], errors='coerce').dropna().between(1, 100).all():
            handle_issue("Invalid 'quantity' values found in order_items.", messiness)
        if (pd.to_numeric(df['unit_price'], errors='coerce') < 0).any():
            handle_issue("Negative 'unit_price' values found in order_items.", messiness)

    if 'return_items' in dataframes:
        df = dataframes['return_items']
        if not pd.to_numeric(df['quantity_returned'], errors='coerce').dropna().between(1, 100).all():
            handle_issue("Invalid 'quantity_returned' values found in return_items.", messiness)
        if (pd.to_numeric(df['unit_price'], errors='coerce') < 0).any():
            handle_issue("Negative 'unit_price' values found in return_items.", messiness)
        if (pd.to_numeric(df['refunded_amount'], errors='coerce') < 0).any():
            handle_issue("Negative 'refunded_amount' values found in return_items.", messiness)

    logger.info("✅ Numeric fields in order_items and return_items are valid and sane.")

def validate_primary_keys(dataframes, messiness):
    """Checks for uniqueness in all primary key columns."""
    pk_map = {
        "product_catalog": "product_id",
        "customers": "customer_id",
        "shopping_carts": "cart_id",
        "cart_items": "cart_item_id",
        "orders": "order_id",
        "returns": "return_id",
        "return_items": "return_item_id",
    }

    for table, pk_col in pk_map.items():
        if table in dataframes:
            df = dataframes[table]
            if df[pk_col].dropna().duplicated().any():
                duplicates = df[df[pk_col].duplicated()][pk_col].tolist()
                handle_issue(f"Duplicate primary key values found in '{table}.{pk_col}': {duplicates[:5]}", messiness)

    logger.info("✅ All primary key uniqueness checks passed.")

def validate_catalog_schema(dataframes, messiness):
    """Validates the schema of the product_catalog DataFrame."""
    if 'product_catalog' not in dataframes:
        return
    df = dataframes['product_catalog']
    required_fields = {"product_id", "product_name", "category", "unit_price"}
    missing = required_fields - set(df.columns)
    if missing:
        handle_issue(f"Product catalog is missing fields: {missing}", messiness)
    if (pd.to_numeric(df['unit_price'], errors='coerce') < 0).any():
        handle_issue("Negative unit_price values found in product_catalog.", messiness)
    logger.info("✅ Product catalog schema is valid.")

def validate_return_refunds(dataframes, messiness, tolerance=0.01):
    """Validates that return totals match the sum of their items using pandas."""
    if 'returns' not in dataframes or 'return_items' not in dataframes:
        return
    returns_df = dataframes['returns']
    return_items_df = dataframes['return_items']

    # Calculate sum of refunds per return from return_items
    item_refund_sums = return_items_df.groupby('return_id')['refunded_amount'].sum().reset_index()
    item_refund_sums.rename(columns={'refunded_amount': 'items_refund_sum'}, inplace=True)

    # Merge with the main returns table
    merged_df = pd.merge(returns_df, item_refund_sums, on='return_id', how='left').fillna(0)

    # Check for mismatches
    mismatches = merged_df[abs(merged_df['refunded_amount'] - merged_df['items_refund_sum']) > tolerance]
    if not mismatches.empty:
        for _, row in mismatches.iterrows():
            handle_issue(f"Refunded amount mismatch for return_id {row['return_id']}: header={row['refunded_amount']}, items_sum={row['items_refund_sum']}", messiness)

    logger.info("✅ All returns.refunded_amount values match the sum of their return_items.refunded_amount.")

def validate_date_fields(dataframes, messiness):
    """Validates date formats and logical consistency (return_date >= order_date)."""
    if 'orders' in dataframes and pd.to_datetime(dataframes['orders']['order_date'], errors='coerce').isnull().any():
        handle_issue("Invalid date formats found in orders.order_date.", messiness)
    if 'returns' in dataframes and pd.to_datetime(dataframes['returns']['return_date'], errors='coerce').isnull().any():
        handle_issue("Invalid date formats found in returns.return_date.", messiness)
    if 'orders' in dataframes and 'returns' in dataframes:
        merged = pd.merge(dataframes['returns'], dataframes['orders'][['order_id', 'order_date']], on='order_id', how='left')
        if (pd.to_datetime(merged['return_date']) < pd.to_datetime(merged['order_date'])).any():
            handle_issue("Found returns with a return_date before the order_date.", messiness)
    logger.info("✅ All order_date and return_date fields valid and logically consistent.")

def validate_foreign_key(child_df, parent_df, child_key, parent_key, messiness):
    """Generic function to validate a single foreign key relationship."""
    # Drop NA values from keys before checking, as FK constraints usually ignore NULLs
    parent_ids = set(parent_df[parent_key].dropna().unique())
    child_ids = child_df[child_key].dropna()

    invalid_ids = child_ids[~child_ids.isin(parent_ids)]

    if not invalid_ids.empty:
        error_message = (
            f"Referential integrity violation: "
            f"'{child_df.name}' contains '{child_key}' values that do not exist in '{parent_df.name}.{parent_key}'. "
            f"Sample invalid IDs: {list(invalid_ids.unique())[:5]}"
        )
        handle_issue(error_message, messiness, level="error")

def validate_all_referential_integrity(dataframes, messiness):
    """Runs all foreign key validation checks."""
    fk_relationships = [
        ("shopping_carts", "customers", "customer_id", "customer_id"),
        ("cart_items", "shopping_carts", "cart_id", "cart_id"),
        ("cart_items", "product_catalog", "product_id", "product_id"),
        ("orders", "customers", "customer_id", "customer_id"),
        ("order_items", "orders", "order_id", "order_id"),
        ("order_items", "product_catalog", "product_id", "product_id"),
        ("returns", "orders", "order_id", "order_id"),
        ("returns", "customers", "customer_id", "customer_id"),
        ("return_items", "returns", "return_id", "return_id"),
        ("return_items", "orders", "order_id", "order_id"),
        ("return_items", "product_catalog", "product_id", "product_id"),
    ]

    for child_table, parent_table, child_key, parent_key in fk_relationships:
        if child_table in dataframes and parent_table in dataframes:
            validate_foreign_key(dataframes[child_table], dataframes[parent_table], child_key, parent_key, messiness)
    logger.info("✅ All referential integrity (FK) checks passed.")
def test_agent_assignments(config, dataframes, messiness):
    agent_pool = getattr(config, 'vocab', {}).get('agent_pool', {})
    agents = agent_pool.get('agents', [])
    config_agents = set(agent['id'] for agent in agents)
    orders_df = dataframes.get("orders")
    returns_df = dataframes.get("returns")

    if orders_df is not None:
        for _, order in orders_df.iterrows():
            order_channel = str(order["order_channel"]).strip()
            agent_id = order.get("agent_id")
            if order_channel.lower() == "phone":
                if pd.notna(agent_id) and agent_id not in config_agents:
                    handle_issue(f"Order {order['order_id']} has invalid agent_id {agent_id}", messiness, level="warn")
            elif pd.notna(agent_id) and agent_id != "ONLINE":
                handle_issue(f"Order {order['order_id']} should have agent_id 'ONLINE' for channel '{order_channel}'", messiness, level="warn")

    if returns_df is not None:
        for _, ret in returns_df.iterrows():
            return_channel = str(ret["return_channel"]).strip()
            agent_id = ret.get("agent_id")
            if return_channel.lower() == "phone":
                if pd.notna(agent_id) and agent_id not in config_agents:
                    handle_issue(f"Return {ret['return_id']} has invalid agent_id {agent_id}", messiness, level="warn")
            elif pd.notna(agent_id) and agent_id != "ONLINE":
                handle_issue(f"Return {ret['return_id']} should have agent_id 'ONLINE' for channel '{return_channel}'", messiness, level="warn")

    logger.info("✅ Agent assignment QA tests passed.")

def validate_conversion_funnel(dataframes, messiness, config):
    """Checks that the number of orders matches the number of converted carts."""
    if "orders" in dataframes and "shopping_carts" in dataframes:
        orders_df = dataframes["orders"]
        carts_df = dataframes["shopping_carts"]

        num_orders = len(orders_df)
        converted_carts = carts_df[carts_df["status"] == "converted"]
        num_converted_carts = len(converted_carts)

        if num_orders != num_converted_carts:
            message = (
                f"Funnel inconsistency: The number of generated orders ({num_orders}) "
                f"does not match the number of 'converted' shopping carts ({num_converted_carts})."
            )
            handle_issue(message, messiness, level="error")

        # Also check if the actual conversion rate is close to the configured rate
        total_carts = len(carts_df)
        actual_rate = num_converted_carts / total_carts if total_carts > 0 else 0
        configured_rate = config.get_parameter("conversion_rate", 0.03)
        tolerance = 0.02 # Allow for 2% absolute tolerance
        if not (configured_rate - tolerance <= actual_rate <= configured_rate + tolerance):
            handle_issue(f"Actual conversion rate ({actual_rate:.2%}) is outside the expected range of the configured rate ({configured_rate:.2%}).", messiness, level="warn")

    logger.info("✅ Conversion funnel (carts to orders) is consistent.")

def validate_repeat_purchase_propensity(dataframes, messiness, config):
    """
    Checks if the actual repeat purchase rate per customer tier is within a
    reasonable tolerance of the configured propensity.
    """
    if 'orders' not in dataframes or 'customers' not in dataframes:
        logger.warning("Skipping repeat purchase validation: orders or customers data not found.")
        return

    orders_df = dataframes['orders']
    customers_df = dataframes['customers']

    # Get relevant settings from config
    repeat_settings = config.get_parameter('repeat_purchase_settings', {})
    propensity_by_tier = repeat_settings.get('propensity_by_tier', {})
    cart_conversion_rate = config.get_parameter('conversion_rate', 0.03)

    if not propensity_by_tier:
        logger.info("✅ Skipping repeat purchase validation: no propensity settings found in config.")
        return

    # Calculate the number of orders per customer
    order_counts = orders_df.groupby('customer_id').size().reset_index(name='order_count')

    # Merge with customer data to get loyalty tiers
    merged_df = pd.merge(order_counts, customers_df[['customer_id', 'loyalty_tier']], on='customer_id', how='left')
    merged_df['loyalty_tier'] = merged_df['loyalty_tier'].fillna('default')

    # For each tier, calculate and validate the actual repeat purchase rate
    for tier, cart_propensity in propensity_by_tier.items():
        tier_customers = merged_df[merged_df['loyalty_tier'] == tier]
        if tier_customers.empty:
            continue

        # The expected rate is the chance of creating a new cart * the chance of that cart converting
        expected_repeat_order_rate = cart_propensity * cart_conversion_rate
        tolerance = 0.05  # Allow for 5% absolute tolerance due to randomness

        total_customers_in_tier = len(tier_customers)
        repeat_customers_in_tier = len(tier_customers[tier_customers['order_count'] > 1])
        actual_repeat_order_rate = repeat_customers_in_tier / total_customers_in_tier if total_customers_in_tier > 0 else 0

        if not (expected_repeat_order_rate - tolerance <= actual_repeat_order_rate <= expected_repeat_order_rate + tolerance):
            handle_issue(
                f"Repeat purchase rate for tier '{tier}' ({actual_repeat_order_rate:.2%}) is outside the expected range of ~{expected_repeat_order_rate:.2%}.",
                messiness, level="warn"
            )

    logger.info("✅ Repeat purchase propensity validation passed.")
### --- Big Audit functions ---

# Placeholder: you can integrate your big_audit.py functions here with similar messiness control.
# For example:

def big_audit_statistical_checks(orders, returns, messiness, config):
    """Performs high-level statistical checks against configured parameters."""
    total_orders = len(orders)
    total_returns = len(returns)
    actual_return_rate = total_returns / total_orders if total_orders else 0

    # Get configured rate and tolerance
    configured_rate = config.get_parameter("return_rate", 0.25)
    tolerance = 0.05 # Allow for 5% tolerance due to randomness

    if not (configured_rate - tolerance <= actual_return_rate <= configured_rate + tolerance):
        handle_issue(f"Return rate ({actual_return_rate:.2%}) is outside the expected range of the configured rate ({configured_rate:.2%}).", messiness, level="warn")

    logger.info(f"✅ Statistical audits completed. Actual return rate: {actual_return_rate:.2%}")

### --- Main ---

def run_all_tests(data_dir: str, messiness: str, run_big_audit: bool = False):
    config = Config()

    # Load all data into a dictionary of DataFrames
    dataframes = load_data(data_dir)

    # Run baseline QA tests
    validate_primary_keys(dataframes, messiness)
    validate_all_referential_integrity(dataframes, messiness)
    validate_numeric_fields(dataframes, messiness)
    validate_catalog_schema(dataframes, messiness)
    validate_return_refunds(dataframes, messiness)
    validate_date_fields(dataframes, messiness)
    test_agent_assignments(config, dataframes, messiness)
    validate_conversion_funnel(dataframes, messiness, config)
    validate_repeat_purchase_propensity(dataframes, messiness, config)

    # Optionally run big audit tests
    orders_dict = dataframes.get('orders', pd.DataFrame()).to_dict('records')
    returns_dict = dataframes.get('returns', pd.DataFrame()).to_dict('records')
    if run_big_audit:
        big_audit_statistical_checks(orders_dict, returns_dict, messiness, config)
        # Add more big audit calls here as you integrate them

    logger.info("✅ All requested QA and audits completed successfully.")

def main():
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="Run QA and Big Audit on generated data.")
    parser.add_argument("--data-dir", type=str, required=True, help="Directory where CSV output files are located")
    parser.add_argument("--run-big-audit", action="store_true", help="Run the big audit checks in addition to baseline QA")
    parser.add_argument("--messiness", type=str, choices=["baseline", "light_mess", "medium_mess", "heavy_mess"], default="baseline", help="Level of messiness tolerance for QA")
    args = parser.parse_args()
    try:
        run_all_tests(data_dir=args.data_dir, messiness=args.messiness, run_big_audit=args.run_big_audit)
    except Exception as e:
        logger.error(f"QA tests failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
