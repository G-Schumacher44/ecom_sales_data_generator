import os
import sys
import argparse
import csv
import importlib
import pandas as pd

from faker import Faker
from generators.inject_mess import run_injection
from tests.qa_tests import run_all_tests
from tests.big_audit import run_big_audit
from utils.config import Config
from generators.generator_customers import generate_customers
from datetime import datetime, timedelta

import random
import copy


def save_table_to_csv(rows, columns, csv_path):
    """
    Save the generated rows to a CSV file.
    The 'columns' argument explicitly defines the order of columns in the CSV.
    """
    if isinstance(rows, pd.DataFrame):
        rows = rows.to_dict(orient='records')
    with open(csv_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def generate_load_script(tables_config, output_path, output_dir):
    """
    Generate a SQLite-compatible SQL script to load CSV data, including
    PRIMARY KEY and FOREIGN KEY constraints.
    """
    # Define the schema relationships, mirroring the logic in qa_tests.py
    pk_map = {
        "product_catalog": "product_id",
        "customers": "customer_id",
        "shopping_carts": "cart_id",
        "cart_items": "cart_item_id",
        "orders": "order_id",
        "order_items": ["order_id", "product_id"],
        "returns": "return_id",
        "return_items": "return_item_id",
    }
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

    with open(output_path, 'w') as f:
        # Add PRAGMA to ensure FKs are enforced by default when the DB is created
        f.write("PRAGMA foreign_keys = ON;\n\n")

        for table in tables_config:
            table_name = table.get('name')
            columns = table.get('columns', [])
            pk_col = pk_map.get(table_name)

            f.write(f'DROP TABLE IF EXISTS {table_name};\n')
            f.write(f'CREATE TABLE {table_name} (\n')
            
            col_defs = []
            for col in columns:
                col_name = col['name']
                col_type = col['type']
                col_def = f"  {col_name} {col_type}"
                # Handle single-column PKs inline for SQLite's `INTEGER PRIMARY KEY` optimization
                if isinstance(pk_col, str) and col_name == pk_col:
                    col_def += " PRIMARY KEY"
                col_defs.append(col_def)

            # Add foreign key constraints for the current table
            table_fks = [fk for fk in fk_relationships if fk[0] == table_name]
            for _, parent_table, child_key, parent_key in table_fks:
                fk_def = f"  FOREIGN KEY({child_key}) REFERENCES {parent_table}({parent_key})"
                col_defs.append(fk_def)

            # Add composite primary key constraint at the table level
            if isinstance(pk_col, list):
                pk_cols_str = ", ".join(pk_col)
                pk_def = f"  PRIMARY KEY ({pk_cols_str})"
                col_defs.append(pk_def)

            f.write(",\n".join(col_defs) + "\n")
            f.write(");\n\n")
            f.write(f".import --csv --skip 1 '{os.path.join(output_dir, f'{table_name}.csv')}' {table_name}\n\n")
    print(f" Generated SQL load script at: {output_path}")

def resave_patched_table(table_name, lookup_cache, config, output_dir):
    """Helper to re-save a table's CSV after its data has been updated in the lookup_cache."""
    if table_name in lookup_cache:
        table_config = config.get_table_config(table_name)
        if table_config and lookup_cache[table_name]:
            columns = [col['name'] for col in table_config.get('columns', [])]
            csv_path = os.path.join(output_dir, f"{table_name}.csv")
            save_table_to_csv(lookup_cache[table_name], columns, csv_path)
            print(f"💾 Re-saved patched '{table_name}' table CSV ➜ {csv_path}")


def _calculate_and_apply_earned_status(lookup_cache, config, output_dir):
    """
    Post-processing step to calculate final customer status.

    This function calculates each customer's total lifetime spend and uses it to
    assign a final "earned" loyalty tier and CLV bucket. This update is applied
    *only* to the `customers` table to reflect their current state. The `orders`
    table intentionally retains the historical tier/bucket from the time of purchase.
    """
    print("📊 Calculating cumulative spend to assign earned tiers and CLV buckets...")
    tier_thresholds = config.get_parameter("tier_spend_thresholds")
    clv_thresholds = config.get_parameter("clv_spend_thresholds")

    if not tier_thresholds and not clv_thresholds:
        print("  Skipping earned status calculation: no spend thresholds found in config.")
        return

    orders_df = pd.DataFrame(lookup_cache.get("orders", []))
    customers_df = pd.DataFrame(lookup_cache.get("customers", []))

    if orders_df.empty or customers_df.empty:
        print("  Skipping earned status calculation: orders or customers data not found.")
        return

    # Separate guests from registered customers to avoid assigning them tiers
    is_guest_col = customers_df['is_guest'].astype(bool)
    guests_df = customers_df[is_guest_col].copy()
    registered_customers_df = customers_df[~is_guest_col].copy()

    # Calculate cumulative spend per customer
    customer_spend = orders_df.groupby('customer_id')['gross_total'].sum().to_dict()

    def get_earned_value(spend, thresholds):
        # Sort thresholds by value descending to get the highest qualifying tier/bucket
        for name, min_spend in sorted(thresholds.items(), key=lambda item: item[1], reverse=True):
            if spend >= min_spend:
                return name
        return None

    # Apply earned tiers and CLV buckets only to the registered customers DataFrame
    registered_customers_df['cumulative_spend'] = registered_customers_df['customer_id'].map(customer_spend).fillna(0)
    if tier_thresholds:
        registered_customers_df['loyalty_tier'] = registered_customers_df['cumulative_spend'].apply(lambda x: get_earned_value(x, tier_thresholds))
    if clv_thresholds:
        registered_customers_df['clv_bucket'] = registered_customers_df['cumulative_spend'].apply(lambda x: get_earned_value(x, clv_thresholds))

    # Drop the temporary calculation column before saving
    if 'cumulative_spend' in registered_customers_df.columns:
        registered_customers_df = registered_customers_df.drop(columns=['cumulative_spend'])

    # Recombine the dataframes and update the master lookup_cache
    updated_customers_df = pd.concat([registered_customers_df, guests_df], ignore_index=True)
    # Update the master lookup_cache
    lookup_cache['customers'] = updated_customers_df.to_dict(orient='records')

    print("✅ Applied earned status to customers and orders.")

def main():
    """
    Main orchestrator for the e-commerce data generation pipeline.
    Parses command-line arguments, loads configuration, and iterates through
    the defined tables to generate and save synthetic data, inject messiness, and run QA tests.
    """
    parser = argparse.ArgumentParser(description="Generate data from YAML config.")
    parser.add_argument('--config', type=str, default=None, help='Path to YAML config file')
    parser.add_argument('--output-dir', type=str, default='output', help='Directory to save generated data')
    parser.add_argument('--messiness-level', type=str, default='baseline',
                        choices=["baseline", "none", "light_mess", "medium_mess", "heavy_mess"],
                        help='Level of messiness to inject into data post-generation.')
    parser.add_argument('--debug', action='store_true', help='Enable detailed debug logging for QA tests')
    args = parser.parse_args()

    if args.messiness_level == "none":
        args.messiness_level = "baseline"

    # Create config instance using provided config path or default
    from pathlib import Path
    config = Config(yaml_path=Path(args.config) if args.config else None)

    # Use config values from config instance
    category_vocab = config.category_vocab
    output_dir = args.output_dir or config.raw_config.get('output_dir', 'output')
    messiness_level = args.messiness_level
    os.makedirs(output_dir, exist_ok=True)
    print(f"📁 Output directory: {output_dir}")

    faker_instance = Faker()

    # --- NEW: Define Global Date Range for Data Generation ---
    # Using current date as the end date for the sales period
    global_end_date = datetime.now().date()
    # Calculate start date based on configured order_days_back
    order_days_back = config.get_parameter('order_days_back', 60) # Default to 60 days
    global_start_date = global_end_date - timedelta(days=order_days_back)

    # Store in lookup_cache for access by generators
    lookup_cache = {
        "global_start_date": global_start_date,
        "global_end_date": global_end_date
    }

    # Prepare row generators from config
    row_generators = {}
    if config.row_generators:
        for table_name, generator_path in config.row_generators.items():
            module_name, func_name = generator_path.rsplit('.', 1)
            module = importlib.import_module(module_name)
            row_generators[table_name] = getattr(module, func_name)

    # Generate lookup catalogs as defined
    lookup_config = config.lookup_config
    if lookup_config:
        print("🔍 Generating lookup catalogs as defined in lookup_config...")
        for lookup_name, lookup_params in lookup_config.items():
            generator_path = lookup_params.get('generator')
            if not generator_path:
                print(f"⚠️ No generator specified for lookup '{lookup_name}', skipping generation.")
                continue
            
            try:
                module_name, func_name = generator_path.rsplit('.', 1)
                module = importlib.import_module(module_name)
                generator_func = getattr(module, func_name)
            except Exception as e:
                print(f"❌ Failed to import generator for lookup '{lookup_name}': {e}")
                continue

            if lookup_name == 'customers':
                try:
                    num_customers = lookup_params.get('num_customers', 100)
                    guest_shopper_pct = lookup_params.get('guest_shopper_pct', 0.4)
                    # The customer generator has a specific signature
                    lookup_cache[lookup_name] = generator_func(
                        num_customers,
                        faker_instance,
                        config=config,
                        guest_shopper_pct=guest_shopper_pct,
                        global_start_date=lookup_cache.get("global_start_date"),
                        global_end_date=lookup_cache.get("global_end_date")
                    )
                    customers = lookup_cache["customers"]
                    if not customers:
                        print("❌ Error: Generated customers list is empty.")
                        raise ValueError("Generated customers list is empty.")
                    if not all(isinstance(c.get("customer_id"), str) for c in customers):
                        print("❌ Error: Some customer_id values are not strings.")
                        raise ValueError("Some customer_id values are not strings.")
                    print(f" Generated customers catalog with {num_customers} customers. Sample customer_id: {customers[0].get('customer_id')}")
                except Exception as e:
                    print(f"❌ Failed to generate lookup catalog 'customers': {e}")
            elif lookup_name == 'product_catalog':
                try:
                    num_products = lookup_params.get('num_products', 100)
                    # The product catalog generator has a different, simpler signature
                    lookup_cache[lookup_name] = generator_func(
                        n=num_products,
                        faker=faker_instance,
                        config=config
                    )
                    print(f" Generated product catalog with {num_products} products.")
                except Exception as e:
                    print(f"❌ Failed to generate lookup catalog '{lookup_name}': {e}")

            lookup_rows = lookup_cache.get(lookup_name, [])
            if lookup_rows:
                # Saving is now handled in the main table processing loop to avoid redundancy.
                # This loop just populates the cache.
                print(f"✅ Cached {len(lookup_rows)} rows for lookup table '{lookup_name}'.")


    tables = config.tables
    if not tables:
        print("❌ Fatal error: No tables defined in the YAML config.")
        raise ValueError("Config is missing the required 'tables' section or it's empty.")

    for table in tables:
        table_name = table.get('name')
        columns = table.get('columns', [])
        if not columns:
            print(f"❌ Fatal error: Table '{table_name}' is missing 'columns'.")
            raise ValueError(f"Table '{table_name}' is missing required 'columns' definition.")
        item_count_range = table.get("item_count_range")
        if item_count_range:
            lookup_cache["item_count_range"] = item_count_range

        if table.get('link_to_orders', False):
            num_rows = None
        else:
            num_rows = table.get('generate', 100)

        # Check if the table data was already generated as a lookup table
        if table_name in lookup_cache and isinstance(lookup_cache[table_name], list):
            rows = lookup_cache[table_name]
            print(f"✅ Using cached rows for table '{table_name}'")
        elif table_name in row_generators:
            print(f"🔄 Generating rows for table '{table_name}' with num_rows={num_rows}")
            if table_name == 'shopping_carts':
                rows = row_generators[table_name](columns, num_rows, faker_instance, lookup_cache, config)
            elif table_name == 'cart_items':
                cart_items, cart_updates = row_generators[table_name](columns, num_rows, faker_instance, lookup_cache, config)
                rows = cart_items
                # Apply updates to the cached carts
                for cart in lookup_cache.get('shopping_carts', []):
                    if cart['cart_id'] in cart_updates:
                        cart.update(cart_updates[cart['cart_id']])
            elif table_name == 'returns':
                # Pass global_end_date to returns generator for end boundary
                rows = row_generators[table_name](columns, num_rows, faker_instance, lookup_cache, config, global_end_date)
            elif table_name == 'customers':
                # Only pass columns, num_rows, faker_instance, and lookup_cache to customers generator
                rows = row_generators[table_name](columns, num_rows, faker_instance, lookup_cache)
            elif table_name == 'order_items':
                # The generator now handles its own de-duplication and returns clean data.
                rows, order_updates = row_generators[table_name](columns, None, faker_instance, lookup_cache, config)

                # Apply updates to the cached orders
                for order in lookup_cache.get('orders', []):
                    if order['order_id'] in order_updates:
                        order.update(order_updates[order['order_id']])
            elif table_name == 'return_items':
                return_items, return_updates = row_generators[table_name](columns, num_rows, faker_instance, lookup_cache, config)
                rows = return_items
                # Apply updates to the cached returns
                for ret in lookup_cache.get('returns', []):
                    if ret['return_id'] in return_updates:
                        ret['refunded_amount'] = return_updates[ret['return_id']]
            else:
                rows = row_generators[table_name](columns, num_rows, faker_instance, lookup_cache, config)
            actual_count = len(rows) if (rows is not None and not (hasattr(rows, 'empty') and rows.empty)) else 0
            print(f" Generated {actual_count} rows for table: '{table_name}'")
            if actual_count == 0:
                # It's valid for item tables to have 0 rows if there are no parent orders/returns
                if table_name in ['order_items', 'return_items']:
                    print(f"Info: Generator for table '{table_name}' returned 0 rows, which can be valid.")
                    continue
                print(f"❌ Fatal error: Generator for table '{table_name}' returned 0 rows.")
                raise ValueError(f"Row generator for table '{table_name}' returned 0 rows.")
        else:
            print(f"❌ Fatal error: No row generator found for table '{table_name}'.")
            raise ValueError(f"No row generator defined for table '{table_name}' and fallback is disabled.")

        if rows is not None and not (hasattr(rows, 'empty') and rows.empty):
            csv_path = os.path.join(output_dir, f"{table_name}.csv")
            save_table_to_csv(rows, [col['name'] for col in columns], csv_path)
            print(f"💾 Saved CSV for table '{table_name}' ➜ {csv_path}")
            lookup_cache[table_name] = rows
        else:
            print(f"Warning: No rows generated for table '{table_name}', skipping CSV save.")

        if table_name == "cart_items":
            # Re-save the shopping_carts table which has been updated with totals
            resave_patched_table("shopping_carts", lookup_cache, config, output_dir)

            print("🛒 Carts and items generated. Processing conversions...")
            conversion_rate = config.get_parameter('conversion_rate', 0.03)
            boosts = config.get_parameter('first_purchase_conversion_boost', {})
            emptied_prob = config.get_parameter('abandoned_cart_emptied_prob', 0.15)
            carts = lookup_cache.get('shopping_carts', [])

            if carts:
                customers_by_id = {c['customer_id']: c for c in lookup_cache.get('customers', [])}
                converted_carts = []
                customers_with_orders = set()
                abandoned_carts_to_process = []
                for cart in sorted(carts, key=lambda x: x['created_at']):
                    customer_id = cart['customer_id']
                    
                    # Determine the effective conversion rate for this cart
                    effective_conversion_rate = conversion_rate
                    if customer_id not in customers_with_orders:
                        # This is a potential first purchase, check for a boost
                        customer_signup_channel = customers_by_id.get(customer_id, {}).get('signup_channel')
                        boost_multiplier = boosts.get(customer_signup_channel, 1.0)
                        effective_conversion_rate *= boost_multiplier

                    if random.random() < effective_conversion_rate:
                        cart['status'] = 'converted'
                        converted_carts.append(cart)
                        customers_with_orders.add(customer_id)
                    else:
                        # Don't set status yet, just collect for post-processing
                        abandoned_carts_to_process.append(cart)

                # Now process the abandoned carts to set final status (abandoned vs emptied)
                cart_items_df = pd.DataFrame(lookup_cache.get('cart_items', []))
                cart_ids_to_empty = set()

                for cart in abandoned_carts_to_process:
                    if random.random() < emptied_prob:
                        cart['status'] = 'emptied'
                        cart['cart_total'] = 0.0
                        cart_ids_to_empty.add(cart['cart_id'])
                    else:
                        cart['status'] = 'abandoned'

                # Filter out items from emptied carts
                if not cart_items_df.empty and cart_ids_to_empty:
                    cart_items_df = cart_items_df[~cart_items_df['cart_id'].isin(cart_ids_to_empty)]
                    lookup_cache['cart_items'] = cart_items_df.to_dict(orient='records')
                    print(f"  Emptied {len(cart_ids_to_empty)} abandoned carts.")

                lookup_cache['converted_carts'] = converted_carts
                total_carts = len(carts)
                actual_conversion_rate = len(converted_carts) / total_carts if total_carts > 0 else 0
                print(f"  {len(converted_carts)} of {total_carts} carts converted into orders (Target: {conversion_rate:.2%}, Actual: {actual_conversion_rate:.2%}).")
                resave_patched_table("shopping_carts", lookup_cache, config, output_dir)
                # Re-save cart_items after some may have been emptied
                resave_patched_table("cart_items", lookup_cache, config, output_dir)

        if table_name == "return_items":
            resave_patched_table("returns", lookup_cache, config, output_dir)

        if table_name == "order_items":
            resave_patched_table("orders", lookup_cache, config, output_dir)

    # --- Post-Processing: Calculate Earned Tiers/CLV ---
    _calculate_and_apply_earned_status(lookup_cache, config, output_dir)

    # Re-save customers and orders CSVs after applying earned status
    resave_patched_table("customers", lookup_cache, config, output_dir)
    resave_patched_table("orders", lookup_cache, config, output_dir)

    sql_script_path = os.path.join(output_dir, "load_data.sql")
    generate_load_script(tables, sql_script_path, output_dir)
    print(f"📜 SQL load script ready ➜ {sql_script_path}")

    # Inject messiness after all CSVs are saved, before QA/Audit
    print("🔁 Running post-export messiness injection...")
    try:
        run_injection(data_dir=output_dir, messiness_level=messiness_level, config_path=str(config.yaml_path))
        print("✅ Messiness injection completed successfully.")
    except Exception as e:
        print(f"❌ Messiness injection failed: {e}")

    print("🧪 Running QA tests to validate output...")
    try:
        run_all_tests(data_dir=output_dir, messiness=messiness_level, debug=args.debug)
        print("✅ QA tests completed successfully.")
    except Exception as e:
        print(f"❌ QA tests failed with error: {e}")

    print("🔎 Running Big Audit tests...")
    try:
        run_big_audit(data_dir=output_dir, messiness=messiness_level)
        print("✅ Big Audit tests completed successfully.")
    except Exception as e:
        print(f"❌ Big Audit tests failed: {e}")


if __name__ == "__main__":
    main()
