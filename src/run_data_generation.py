import os
import sys
import argparse
import csv
import importlib
import subprocess
import pandas as pd

from faker import Faker
from generators.generator_catalog import generate_product_catalog
from generators.generator_customers import generate_customers
from utils.config import Config
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
        writer = csv.DictWriter(csvfile, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def generate_load_script(tables_config, output_path, output_dir):
    """
    Generate a SQLite-compatible SQL script to load CSV data.
    """
    with open(output_path, 'w') as f:
        for table in tables_config:
            table_name = table.get('name')
            columns = table.get('columns', [])
            f.write(f'DROP TABLE IF EXISTS {table_name};\n')
            f.write(f'CREATE TABLE {table_name} (\n')
            col_defs = [f"  {col['name']} {col['type']}" for col in columns]
            f.write(",\n".join(col_defs) + "\n")
            f.write(");\n\n")
            f.write(f".mode csv\n")
            f.write(f".import '{os.path.join(output_dir, f'{table_name}.csv')}' {table_name}\n\n")
    print(f" Generated SQL load script at: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate data from YAML config.")
    parser.add_argument('--config', type=str, default=None, help='Path to YAML config file')
    parser.add_argument('--output-dir', type=str, default='output', help='Directory to save generated data')
    parser.add_argument('--messiness-level', type=str, default='none',
                        choices=["none", "light_mess", "medium_mess", "heavy_mess"],
                        help='Level of messiness to inject into data post-generation.')
    args = parser.parse_args()

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
            if lookup_name == 'product_catalog':
                num_products = lookup_params.get('num_products', 100)
                # Pass the main config object for consistent access to vocab and params
                lookup_cache["product_catalog"] = generate_product_catalog(
                    n=num_products,
                    faker=faker_instance,
                    config=config
                )
                print(f" Generated product catalog with {num_products} products.")
            elif lookup_name == 'customers':
                try:
                    num_customers = lookup_params.get('num_customers', 100)
                    guest_shopper_pct = lookup_params.get('guest_shopper_pct', 0.4)
                    # Pass the full config object to the customer generator for consistency
                    lookup_cache["customers"] = generate_customers(num_customers, faker_instance, config=config, guest_shopper_pct=guest_shopper_pct)
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
            else:
                generator_path = lookup_params.get('generator')
                if generator_path:
                    try:
                        module_name, func_name = generator_path.rsplit('.', 1)
                        module = importlib.import_module(module_name)
                        generator_func = getattr(module, func_name)
                        lookup_cache[lookup_name] = generator_func(lookup_params, faker_instance, lookup_cache)
                        print(f" Generated lookup catalog '{lookup_name}' using {generator_path}.")
                    except Exception as e:
                        print(f"❌ Failed to generate lookup catalog '{lookup_name}': {e}")
                else:
                    print(f"⚠️ No generator specified for lookup '{lookup_name}', skipping generation.")

            lookup_rows = lookup_cache.get(lookup_name, [])
            if lookup_rows:
                yaml_table_config = config.get_table_config(lookup_name)
                if yaml_table_config:
                    lookup_columns = [col['name'] for col in yaml_table_config.get('columns', [])]
                else:
                    lookup_columns = list(lookup_rows[0].keys())
                lookup_csv_path = os.path.join(output_dir, f"{lookup_name}.csv")
                save_table_to_csv(lookup_rows, lookup_columns, lookup_csv_path)
                print(f"💾 Saved CSV for lookup catalog '{lookup_name}' ➜ {lookup_csv_path}")


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

        if table_name in row_generators:
            print(f"🔄 Generating rows for table '{table_name}' with num_rows={num_rows}")
            if table_name == 'orders':
                customers_list = lookup_cache.get("customers")
                if not customers_list:
                    print(f"❌ Error: Customers data not found in cache or empty but required for table '{table_name}'.")
                    raise ValueError(f"Customers data not found in cache or empty but required for table '{table_name}'.")

                # Pass all arguments positionally to the orders generator
                rows = row_generators[table_name](
                    columns,
                    num_rows,
                    faker_instance,
                    lookup_cache,
                    config,
                    customers_list,
                    global_start_date,
                    global_end_date
                )
            elif table_name == 'returns':
                # Pass global_end_date to returns generator for end boundary
                rows = row_generators[table_name](columns, num_rows, faker_instance, lookup_cache, config, global_end_date)
            elif table_name == 'customers':
                # Only pass columns, num_rows, faker_instance, and lookup_cache to customers generator
                rows = row_generators[table_name](columns, num_rows, faker_instance, lookup_cache)
            elif table_name == 'order_items':
                order_items, order_updates = row_generators[table_name](columns, num_rows, faker_instance, lookup_cache, config)
                rows = order_items
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

        # (Removed guest customer extraction and merging after orders generation)

        if table_name == "return_items":
            if "returns" in lookup_cache:
                returns_table_config = next((t for t in tables if t.get('name') == "returns"), None)
                if returns_table_config and lookup_cache["returns"]:
                    returns_columns = [col['name'] for col in returns_table_config.get('columns', [])]
                    returns_csv_path = os.path.join(output_dir, "returns.csv")
                    save_table_to_csv(lookup_cache["returns"], returns_columns, returns_csv_path)
                    print(f"💾 Re-saved patched 'returns' table CSV ➜ {returns_csv_path}")

        if table_name == "order_items":
            if "orders" in lookup_cache:
                orders_table_config = next((t for t in tables if t.get('name') == "orders"), None)
                if orders_table_config and lookup_cache["orders"]:
                    orders_columns = [col['name'] for col in orders_table_config.get('columns', [])]
                    orders_csv_path = os.path.join(output_dir, "orders.csv")
                    save_table_to_csv(lookup_cache["orders"], orders_columns, orders_csv_path)
                    print(f"💾 Re-saved patched 'orders' table CSV ➜ {orders_csv_path}")

    sql_script_path = os.path.join(output_dir, "load_data.sql")
    generate_load_script(tables, sql_script_path, output_dir)
    print(f"📜 SQL load script ready ➜ {sql_script_path}")

    # Inject messiness after all CSVs are saved, before QA/Audit
    print("🔁 Running post-export messiness injection...")
    try:
        inject_cmd = [sys.executable, "-m", "generators.inject_mess", "--data-dir", output_dir,
                      "--messiness-level", messiness_level, "--config", str(config.yaml_path)]
        print(f"  Executing: {' '.join(inject_cmd)}")
        subprocess.run(inject_cmd, check=True)
        print("✅ Messiness injection completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Messiness injection failed with error: {e}")

    print("🧪 Running QA tests to validate output...")
    try:
        # Pass output_dir and messiness_level to QA tests
        subprocess.run(["python", "-m", "tests.qa_tests", "--data-dir", output_dir, "--messiness", messiness_level], check=True)
        print("✅ QA tests completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"❌ QA tests failed: {e}")

    print("🔎 Running Big Audit tests...")
    try:
        # Pass output_dir and messiness_level to Big Audit tests
        subprocess.run(["python", "-m", "tests.big_audit", "--data-dir", output_dir, "--messiness", messiness_level], check=True)
        print("✅ Big Audit tests completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Big Audit tests failed: {e}")


if __name__ == "__main__":
    main()
