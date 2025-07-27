import argparse
import os
import pandas as pd

# Names of CSV files to audit
TABLE_NAMES = [
    'orders.csv',
    'customers.csv',
    'returns.csv',
    'return_items.csv',
    'order_items.csv',
]

# Columns to exclude from messiness audit per table (keys, financial columns, etc.)
EXCLUDE_COLS = {
    'orders.csv': {'order_id', 'customer_id', 'order_total', 'quantity'},
    'customers.csv': {'customer_id'},
    'returns.csv': {'return_id', 'refunded_amount'},
    'return_items.csv': {'return_id', 'refunded_amount', 'quantity_returned'},
    'order_items.csv': {'order_id', 'unit_price', 'quantity'},
}

def has_messiness(val):
    if pd.isna(val):
        return True
    if isinstance(val, str):
        if val != val.strip():
            return True
        if val.lower() != val and val.upper() != val:
            return True
    return False

def audit_file(filepath):
    filename = os.path.basename(filepath)
    print(f"\nAuditing {filename}...")
    df = pd.read_csv(filepath)
    print(f"Columns in {filename}: {df.columns.tolist()}")

    exclude_cols = EXCLUDE_COLS.get(filename, set())
    # Columns to check messiness on = all except excluded
    check_cols = [col for col in df.columns if col not in exclude_cols]

    messy_summary = {}

    for col in check_cols:
        messy_mask = df[col].apply(has_messiness)
        messy_count = messy_mask.sum()
        if messy_count > 0:
            messy_summary[col] = messy_count

    if not messy_summary:
        print("No messiness found in any audited columns.")
    else:
        print(f"Found messiness in {len(messy_summary)} columns:")
        for col, count in messy_summary.items():
            print(f"- Column '{col}': {count} messy rows")
            print(df.loc[df[col].apply(has_messiness), col].head(5))
            print()

def main() -> None:
    parser = argparse.ArgumentParser(description="Audit generated CSVs for messiness")
    parser.add_argument(
        "--data-dir",
        required=True,
        help="Directory containing generated CSV files",
    )
    args = parser.parse_args()

    for name in TABLE_NAMES:
        filepath = os.path.join(args.data_dir, name)
        if os.path.exists(filepath):
            audit_file(filepath)
        else:
            print(f"File not found: {filepath}")


if __name__ == "__main__":
    main()
