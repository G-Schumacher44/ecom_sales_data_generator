import pandas as pd
import numpy as np
import os
import argparse
import random

from utils.config import Config

def inject_whitespace(df: pd.DataFrame, columns: list, prob: float):
    """Adds random leading/trailing whitespace to string columns."""
    for col in columns:
        if col in df.columns and pd.api.types.is_string_dtype(df[col]):
            # Filter to non-null strings to avoid errors
            mask = df[col].notna() & (df[col].apply(lambda x: isinstance(x, str) and random.random() < prob))
            df.loc[mask, col] = df.loc[mask, col].apply(lambda x: random.choice([' ', '  ']) + x.strip() + random.choice([' ', '  ']))
    return df

def inject_casing_variations(df: pd.DataFrame, columns: list, prob: float):
    """Changes casing (upper/lower/title) for string columns."""
    for col in columns:
        if col in df.columns and pd.api.types.is_string_dtype(df[col]):
            mask = df[col].notna() & (df[col].apply(lambda x: isinstance(x, str) and random.random() < prob))
            df.loc[mask, col] = df.loc[mask, col].apply(lambda x: random.choice([x.upper(), x.lower(), x.title()]))
    return df

def inject_random_nulls(df: pd.DataFrame, columns: list, prob: float):
    """Randomly replaces non-null values with NaN in specified columns."""
    for col in columns:
        if col in df.columns:
            # Only target non-nulls for injection
            mask = df[col].notna() & (df[col].apply(lambda x: random.random() < prob))
            df.loc[mask, col] = np.nan
    return df

def main():
    parser = argparse.ArgumentParser(description="Inject messiness into generated CSV data.")
    parser.add_argument("--data-dir", type=str, required=True, help="Directory containing CSV files.")
    parser.add_argument("--messiness-level", type=str, default="none",
                        choices=["none", "light_mess", "medium_mess", "heavy_mess"], help="Level of messiness to inject.")
    parser.add_argument('--config', type=str, default=None, help='Path to YAML config file for advanced injections.')
    args = parser.parse_args()

    data_dir = args.data_dir
    messiness_level = args.messiness_level

    if messiness_level == "none":
        print("Skipping messiness injection as level is 'none'.")
        return

    # Load config for advanced injections
    config = Config(yaml_path=args.config) if args.config else None

    print(f"Applying '{messiness_level}' messiness injection to data in: {data_dir}")

    # --- Configuration for Messiness Injection ---
    # Define columns to target for different types of messiness
    # These are general string columns where stylistic mess is common.

    string_cols_for_stylistic_mess = {
        "orders.csv": ["order_channel", "payment_method", "shipping_speed", "customer_tier", "clv_bucket"],
        "order_items.csv": ["product_name", "category"],
        "returns.csv": ["reason", "return_type", "return_channel"],
        "return_items.csv": ["product_name"],
        "product_catalog.csv": ["product_name", "category"],
        "customers.csv": ["gender", "customer_status", "signup_channel", "loyalty_tier"]
    }

    # Fields where random nulls might be introduced (optional data, non-critical FKs)
    # Note: Guest shopper specific nulls are handled in generator_customers.py directly.
    null_inject_cols = {
        "customers.csv": ["email_verified", "marketing_opt_in"],  # These are booleans, but can be NaN
        "orders.csv": ["agent_id"],  # For online orders, agent_id might be null/empty
        "returns.csv": ["agent_id"],  # For web returns, agent_id might be null/empty
    }

    # Probabilities for different messiness levels
    messiness_probs = {
        "light_mess": {
            "whitespace_prob": 0.05, # 5% chance
            "casing_prob": 0.05,     # 5% chance
            "null_prob": 0.02        # 2% chance
        },
        "medium_mess": {
            "whitespace_prob": 0.08,
            "casing_prob": 0.08,
            "null_prob": 0.04
        },
        "heavy_mess": {
            "whitespace_prob": 0.15, # 15% chance
            "casing_prob": 0.15,     # 15% chance
            "null_prob": 0.08        # 8% chance
        }
    }
    current_probs = messiness_probs.get(messiness_level, {})

    # Apply stylistic messiness (whitespace, casing)
    for filename, cols in string_cols_for_stylistic_mess.items():
        filepath = os.path.join(data_dir, filename)
        if os.path.exists(filepath):
            df = pd.read_csv(filepath, dtype=str) # Read as string to prevent type inference issues
            df = inject_whitespace(df.copy(), cols, current_probs.get("whitespace_prob", 0))
            df = inject_casing_variations(df.copy(), cols, current_probs.get("casing_prob", 0))
            df.to_csv(filepath, index=False)
            print(f"  Applied stylistic mess to {filename}")
        else:
            print(f"  Warning: {filename} not found for stylistic mess injection.")

    # Apply random null injection
    for filename, cols in null_inject_cols.items():
        filepath = os.path.join(data_dir, filename)
        if os.path.exists(filepath):
            df = pd.read_csv(filepath) # Read again, or pass the DataFrame if it was modified above
            df = inject_random_nulls(df.copy(), cols, current_probs.get("null_prob", 0))
            df.to_csv(filepath, index=False)
            print(f"  Applied random null mess to {filename}")
        else:
            print(f"  Warning: {filename} not found for random null injection.")


    # --- Advanced Injection (only applies to orders and returns) ---
    if messiness_level in ["medium_mess", "heavy_mess"]:
        intensity_map = {
            "medium_mess": "medium",
            "heavy_mess": "high"  # Map heavy_mess to 'high' intensity
        }
        intensity = intensity_map.get(messiness_level)

        for filename in ["orders.csv", "returns.csv"]:
            filepath = os.path.join(data_dir, filename)
            if os.path.exists(filepath) and intensity:
                df = pd.read_csv(filepath)
                if filename == "orders.csv":
                    df = inject_sales_spikes(df.copy(), intensity=intensity, config=config)
                elif filename == "returns.csv":
                    df = inject_return_reason_bias(df.copy(), intensity=intensity, config=config, data_dir=data_dir)
                df.to_csv(filepath, index=False)
                print(f"  Applied advanced injection to {filename} with '{intensity}' intensity.")

    print("Messiness injection complete.")


def inject_sales_spikes(df, intensity="low", config=None):
    """
    Injects sales spikes in 'total_items'.
    If a seasonal schema is in the config, it's used. Otherwise, a random month is spiked.
    """
    if "order_date" not in df.columns:
        return df

    df['order_date'] = pd.to_datetime(df['order_date'])
    seasonal_factors = config.get_parameter("seasonal_spike_factors", {}).get(intensity) if config else None

    if seasonal_factors:
        print(f"    Applying seasonal sales spikes for '{intensity}' level...")
        for month, factor in seasonal_factors.items():
            mask = df['order_date'].dt.month == int(month)
            affected_rows = mask.sum()
            if affected_rows > 0:
                df.loc[mask, "total_items"] = (df.loc[mask, "total_items"] * factor).astype(int)
                print(f"      - Spiked {affected_rows} orders in month {month} by {factor}x")
    else:
        print("    Applying random monthly sales spike (fallback)...")
        spike_factor = {"low": 1.2, "medium": 1.5, "high": 2.0}.get(intensity, 1.2)
        spike_month = random.choice(df["order_date"].dt.month.unique())
        mask = df["order_date"].dt.month == spike_month
        df.loc[mask, "total_items"] = (df.loc[mask, "total_items"] * spike_factor).astype(int)
        print(f"      - Spiked {mask.sum()} orders in month {spike_month} by {spike_factor}x")

    return df


def inject_return_reason_bias(df, intensity="low", config=None, data_dir=None):
    """
    Overwrites a portion of return reasons using a contextual, weighted probability schema
    defined in the YAML config file. This makes the bias configurable and realistic.
    """
    if "reason" not in df.columns:
        return df
    if not config or not data_dir:
        print("  Warning: No config or data_dir provided for contextual return reason bias. Skipping.")
        return df

    # Load order_items to get product categories for contextual bias
    order_items_path = os.path.join(data_dir, "order_items.csv")
    if not os.path.exists(order_items_path):
        print("  Warning: order_items.csv not found. Cannot apply contextual return bias.")
        return df
    order_items_df = pd.read_csv(order_items_path)
    # Create a lookup from order_id to the first category in that order.
    order_to_category = order_items_df.drop_duplicates(subset=["order_id"]).set_index("order_id")["category"].str.lower().to_dict()

    # Get schemas from config, now expected to be nested by category
    bias_schemas = config.get_parameter("return_reason_bias_schemas", {}).get(intensity, {})
    if not bias_schemas:
        print(f"  Warning: No return reason bias schemas found for intensity '{intensity}'. Skipping.")
        return df

    # Define what percentage of rows to overwrite based on intensity
    overwrite_prob = {"medium": 0.25, "high": 0.50}.get(intensity, 0.1)

    mask = df["reason"].notna() & (np.random.rand(len(df)) < overwrite_prob)
    idx_to_modify = df[mask].index

    if len(idx_to_modify) > 0:
        final_reasons = df.loc[idx_to_modify, "reason"].copy()
        modified_count = 0
        for idx in idx_to_modify:
            order_id = df.loc[idx, "order_id"]
            category = order_to_category.get(order_id)
            schema = bias_schemas.get(category, bias_schemas.get("default"))
            if schema:
                reasons = list(schema.keys())
                probs = np.array(list(schema.values()), dtype=float)
                probs /= probs.sum()
                final_reasons.loc[idx] = np.random.choice(reasons, p=probs)
                modified_count += 1
        df.loc[idx_to_modify, "reason"] = final_reasons
        print(f"    Overwrote {modified_count} return reasons using '{intensity}' contextual schemas.")

    return df

if __name__ == "__main__":
    main()