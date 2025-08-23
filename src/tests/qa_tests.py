import argparse
import os
import pandas as pd
import logging
import sys
import numpy as np
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
    """Checks for uniqueness in all single-column and composite primary keys."""
    pk_map = {
        "product_catalog": "product_id",
        "customers": "customer_id",
        "shopping_carts": "cart_id",
        "cart_items": "cart_item_id",
        "orders": "order_id",
        "returns": "return_id",
        "return_items": "return_item_id",
    }
    composite_pk_map = {
        "order_items": ["order_id", "product_id"]
    }

    for table, pk_col in pk_map.items():
        if table in dataframes:
            df = dataframes[table]
            if df[pk_col].dropna().duplicated().any():
                duplicates = df[df[pk_col].duplicated()][pk_col].tolist()
                handle_issue(f"Duplicate primary key values found in '{table}.{pk_col}': {duplicates[:5]}", messiness)

    for table, pk_cols in composite_pk_map.items():
        if table in dataframes:
            df = dataframes[table]
            if df.duplicated(subset=pk_cols).any():
                duplicate_rows = df[df.duplicated(subset=pk_cols, keep=False)].head(5)
                handle_issue(f"Duplicate composite primary key values found in '{table}' for columns {pk_cols}. Sample duplicates:\n{duplicate_rows}", messiness)

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

def validate_cart_totals(dataframes, messiness, tolerance=0.01):
    """Validates that shopping_cart totals match the sum of their items."""
    if 'shopping_carts' not in dataframes or 'cart_items' not in dataframes:
        return
    carts_df = dataframes['shopping_carts']
    cart_items_df = dataframes['cart_items']

    # Calculate sum of item totals per cart from cart_items
    cart_items_df['item_total'] = pd.to_numeric(cart_items_df['quantity'], errors='coerce') * pd.to_numeric(cart_items_df['unit_price'], errors='coerce')
    item_totals_sum = cart_items_df.groupby('cart_id')['item_total'].sum().reset_index()
    item_totals_sum.rename(columns={'item_total': 'items_total_sum'}, inplace=True)

    # Merge with the main carts table and fill missing sums with 0
    merged_df = pd.merge(carts_df, item_totals_sum, on='cart_id', how='left').fillna(0)

    # Make status check case-insensitive to handle messiness
    merged_df['status_lower'] = merged_df['status'].str.strip().str.lower()

    # --- Validation Logic ---
    # 1. For 'emptied' carts, total must be 0 and there should be no items.
    emptied_carts = merged_df[merged_df['status_lower'] == 'emptied']
    if not emptied_carts.empty:
        if (emptied_carts['cart_total'] != 0).any():
            handle_issue("Found 'emptied' carts with a non-zero cart_total.", messiness, level="warn")
        if (emptied_carts['items_total_sum'] != 0).any():
            handle_issue("Found cart_items associated with 'emptied' carts.", messiness, level="warn")

    # 2. For all other carts, the total must match the sum of items.
    other_carts = merged_df[merged_df['status_lower'] != 'emptied']
    mismatches = other_carts[abs(other_carts['cart_total'] - other_carts['items_total_sum']) > tolerance]

    if not mismatches.empty:
        for _, row in mismatches.iterrows():
            handle_issue(f"Cart total mismatch for cart_id {row['cart_id']}: header={row['cart_total']}, items_sum={row['items_total_sum']}", messiness, level="warn")

    logger.info("✅ All shopping_carts.cart_total values are consistent with their status and items.")

def validate_cart_timestamps(dataframes, messiness):
    """Validates logical consistency of cart-related timestamps."""
    if 'shopping_carts' not in dataframes or 'cart_items' not in dataframes:
        return
    carts_df = dataframes['shopping_carts']
    cart_items_df = dataframes['cart_items']

    # Convert to datetime, coercing errors to NaT
    carts_df['created_at_dt'] = pd.to_datetime(carts_df['created_at'], errors='coerce')
    carts_df['updated_at_dt'] = pd.to_datetime(carts_df['updated_at'], errors='coerce')
    cart_items_df['added_at_dt'] = pd.to_datetime(cart_items_df['added_at'], errors='coerce')

    # Merge to check relationships
    merged_df = pd.merge(cart_items_df, carts_df[['cart_id', 'created_at_dt', 'updated_at_dt']], on='cart_id', how='left')

    if (merged_df['added_at_dt'] < merged_df['created_at_dt']).any():
        handle_issue("Found cart_items with an 'added_at' before the cart's 'created_at'.", messiness, level="warn")
    if (carts_df['updated_at_dt'] < carts_df['created_at_dt']).any():
        handle_issue("Found shopping_carts with an 'updated_at' before its 'created_at'.", messiness, level="warn")

    logger.info("✅ All cart-related timestamps are logically consistent.")

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
def validate_agent_assignments(config, dataframes, messiness):
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
        # Make status check case-insensitive to handle messiness from inject_mess.py
        converted_carts = carts_df[carts_df["status"].str.strip().str.lower() == "converted"]
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

def validate_repeat_purchase_propensity(dataframes, messiness, config, tolerance=0.07, debug=False):
    """
    Checks if the actual repeat purchase rate per customer segment (channel/tier)
    is within a reasonable tolerance of the configured propensity.
    """
    if 'orders' not in dataframes or 'customers' not in dataframes:
        logger.warning("Skipping repeat purchase validation: orders or customers data not found.")
        return

    orders_df = dataframes['orders']
    customers_df = dataframes['customers']
    repeat_settings = config.get_parameter('repeat_purchase_settings', {})

    # Exclude reactivation orders from this specific validation, as they are
    # driven by a separate probability model (reactivation_settings).
    if 'is_reactivated' in orders_df.columns:
        orders_df = orders_df[orders_df['is_reactivated'] == False]

    carts_df = dataframes.get('shopping_carts')
    seasonal_factors = config.get_parameter('seasonal_factors', {})

    propensity_config = repeat_settings.get('propensity_by_channel_and_tier', {})
    cart_conversion_rate = config.get_parameter('conversion_rate', 0.03)

    if not propensity_config:
        logger.info("✅ Skipping repeat purchase validation: no propensity settings found in config.")
        return

    order_counts = orders_df.groupby('customer_id').size().reset_index(name='order_count')
    # BUG FIX: The population for validation must be ALL customers in a segment,
    # not just those who made a purchase. We start with customers_df and left-join order counts.
    merged_df = pd.merge(customers_df[['customer_id', 'initial_loyalty_tier', 'signup_channel']], order_counts, on='customer_id', how='left')
    merged_df['order_count'] = merged_df['order_count'].fillna(0) # Customers with no orders get a count of 0.

    merged_df['initial_loyalty_tier'] = merged_df['initial_loyalty_tier'].fillna('default')
    merged_df['signup_channel'] = merged_df['signup_channel'].fillna('default')

    # Iterate through the nested configuration to validate each segment
    for channel, tier_propensities in propensity_config.items():
        if not isinstance(tier_propensities, dict): continue
        for tier, avg_visits_propensity in tier_propensities.items():
            segment_customers = merged_df[(merged_df['signup_channel'] == channel) & (merged_df['initial_loyalty_tier'] == tier)]
            if segment_customers.empty:
                continue

            # --- NEW: Calculate effective seasonality multiplier on a PER-SEGMENT basis ---
            # The previous logic used a single global multiplier, which was incorrect because
            # different segments have different temporal distributions and are thus affected
            # by seasonality differently. This logic now calculates the multiplier for each segment.
            effective_multiplier = 1.0
            if carts_df is not None and not carts_df.empty and seasonal_factors:
                segment_customer_ids = set(segment_customers['customer_id'])
                segment_carts_df = carts_df[carts_df['customer_id'].isin(segment_customer_ids)].copy()

                if not segment_carts_df.empty:
                    # From this segment's carts, find the repeaters. Seasonality only affects them.
                    cart_counts = segment_carts_df['customer_id'].value_counts()
                    repeater_ids_in_segment = cart_counts[cart_counts > 1].index
                    repeater_carts_df = segment_carts_df[segment_carts_df['customer_id'].isin(repeater_ids_in_segment)].copy()

                    if not repeater_carts_df.empty:
                        repeater_carts_df['created_at_dt'] = pd.to_datetime(repeater_carts_df['created_at'], errors='coerce')
                        repeater_carts_df.dropna(subset=['created_at_dt'], inplace=True)
                        repeater_carts_df['month'] = repeater_carts_df['created_at_dt'].dt.month

                        final_carts_per_month = repeater_carts_df['month'].value_counts()

                        base_carts_sum = 0
                        for month, count in final_carts_per_month.items():
                            multiplier = seasonal_factors.get(str(month), seasonal_factors.get(month, 1.0))
                            base_carts_sum += count / multiplier
                        
                        if base_carts_sum > 0:
                            effective_multiplier = len(repeater_carts_df) / base_carts_sum

            # --- NEW: Zero-Inflated Poisson Model for Expected Rate ---
            # The generator's logic is a mixture model:
            # 1. A Bernoulli trial determines IF a customer is a "repeater" based on base propensity.
            # 2. Seasonality ONLY increases cart volume for those who are already repeaters.
            # The test must model this, not a simple Poisson process.

            # Base lambda for repeat CARTS (before seasonality)
            lambda_base_carts = avg_visits_propensity

            # The test is validating against non-reactivated orders, so the model
            # should only consider the organic repeat process.
            # P(is_repeater) = 1 - P(no organic repeats)
            prob_is_repeater = 1 - np.exp(-lambda_base_carts)

            if prob_is_repeater > 1e-9: # Avoid division by zero for tiny probabilities
                # The model should only consider the organic repeat carts.
                # The average number of base carts for a repeater is 1 (initial) + the
                # conditional mean of the Poisson process for repeat carts.
                # E[X|X>0] for a Poisson(lambda) is lambda / (1 - e^-lambda)
                # So, avg_base_total_carts = 1 + (lambda / prob_is_repeater)
                lambda_total_base_repeat_carts = lambda_base_carts
                avg_base_total_carts_for_repeater = 1 + (lambda_base_carts / prob_is_repeater)

                # 2. Amplify this by the seasonality multiplier to get the final cart volume
                avg_final_total_carts_for_repeater = avg_base_total_carts_for_repeater * effective_multiplier

                # 3. Calculate the lambda for REPEAT orders based on the amplified cart volume
                # The number of repeat carts is the total minus the one initial cart.
                lambda_repeat_orders_for_repeater = (avg_final_total_carts_for_repeater - 1) * cart_conversion_rate

                # 4. Use this lambda in the formula for P(total_orders > 1 | is_repeater)
                boost_config = config.get_parameter('first_purchase_conversion_boost', {})
                boost_multiplier = boost_config.get(channel, 1.0)
                boosted_conversion_rate = cart_conversion_rate * boost_multiplier

                # P(total <= 1 | repeater) = P(repeat_orders=0) + P(initial=0, repeat_orders=1)
                prob_repeater_has_0_repeat_orders = np.exp(-lambda_repeat_orders_for_repeater)
                prob_repeater_has_1_repeat_order = lambda_repeat_orders_for_repeater * prob_repeater_has_0_repeat_orders
                prob_total_le_1_for_repeater = prob_repeater_has_0_repeat_orders + (1 - boosted_conversion_rate) * prob_repeater_has_1_repeat_order
                prob_gt_1_order_for_repeater = 1 - prob_total_le_1_for_repeater
                
                expected_repeat_order_rate = prob_is_repeater * prob_gt_1_order_for_repeater
            else:
                expected_repeat_order_rate = 0.0

            total_customers_in_segment = len(segment_customers)
            repeat_customers_in_segment = len(segment_customers[segment_customers['order_count'] > 1])
            actual_repeat_order_rate = repeat_customers_in_segment / total_customers_in_segment if total_customers_in_segment > 0 else 0

            if debug:
                logger.debug(f"--- Debugging Segment: {channel}/{tier} ---")
                logger.debug(f"  Configured Avg Visits (lambda): {avg_visits_propensity}")
                logger.debug(f"  Seasonal Multiplier: {effective_multiplier:.4f}")
                logger.debug(f"  Prob. is Repeater: {prob_is_repeater:.4f}")
                logger.debug(f"  Avg Final Carts for Repeater: {avg_final_total_carts_for_repeater:.4f}")
                logger.debug(f"  Lambda for Repeater Orders: {lambda_repeat_orders_for_repeater:.4f}")
                logger.debug(f"  P(>1 order | is repeater): {prob_gt_1_order_for_repeater:.4f}")
                logger.debug(f"  Expected Rate: {expected_repeat_order_rate:.4f}")
                logger.debug(f"  Actual Rate:   {actual_repeat_order_rate:.4f}")
                logger.debug(f"  Total Customers in Segment: {total_customers_in_segment}")
                logger.debug(f"  Repeat Customers in Segment: {repeat_customers_in_segment}")

            if not (expected_repeat_order_rate - tolerance <= actual_repeat_order_rate <= expected_repeat_order_rate + tolerance * 1.5): # Allow more upside variance
                handle_issue(
                    f"Repeat purchase rate for segment '{channel}/{tier}' ({actual_repeat_order_rate:.2%}) is outside the expected range of ~{expected_repeat_order_rate:.2%}.",
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

def run_all_tests(data_dir: str, messiness: str, run_big_audit: bool = False, debug: bool = False):
    config = Config()

    # Load all data into a dictionary of DataFrames
    dataframes = load_data(data_dir)

    # Run baseline QA tests
    logger.info("--- Starting Primary Key / Foreign Key Audit ---")
    validate_primary_keys(dataframes, messiness)
    validate_all_referential_integrity(dataframes, messiness)
    logger.info("--- PK/FK Audit Complete ---")
    validate_numeric_fields(dataframes, messiness)
    validate_catalog_schema(dataframes, messiness)
    validate_return_refunds(dataframes, messiness)
    validate_cart_totals(dataframes, messiness)
    validate_cart_timestamps(dataframes, messiness)
    validate_date_fields(dataframes, messiness)
    validate_agent_assignments(config, dataframes, messiness)
    validate_conversion_funnel(dataframes, messiness, config)
    validate_repeat_purchase_propensity(dataframes, messiness, config, debug=debug)

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
    parser.add_argument("--debug", action="store_true", help="Enable detailed debug logging for propensity tests")
    args = parser.parse_args()
    try:
        run_all_tests(data_dir=args.data_dir, messiness=args.messiness, run_big_audit=args.run_big_audit, debug=args.debug)
    except Exception as e:
        logger.error(f"QA tests failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
