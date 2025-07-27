import argparse
import os
import pandas as pd


def load_csv(name: str, data_dir: str) -> pd.DataFrame:
    """Read ``name`` from ``data_dir`` and return a DataFrame."""
    return pd.read_csv(os.path.join(data_dir, name))

def main() -> None:
    parser = argparse.ArgumentParser(description="Run big audit checks on CSV data")
    parser.add_argument(
        "--data-dir",
        required=True,
        help="Directory containing generated CSV files",
    )
    parser.add_argument(
        "--messiness",
        type=str,
        choices=["baseline", "light_mess", "medium_mess", "heavy_mess"],
        default="baseline",
        help="Level of messiness tolerance (not actively used in all checks, but accepted).",
    )
    args = parser.parse_args()

    data_dir = args.data_dir
    messiness = args.messiness

    # Load CSV files from the provided directory
    orders = load_csv("orders.csv", data_dir)
    order_items = load_csv("order_items.csv", data_dir)
    returns = load_csv("returns.csv", data_dir)
    return_items = load_csv("return_items.csv", data_dir)
    product_catalog = load_csv("product_catalog.csv", data_dir)
    customers = load_csv("customers.csv", data_dir)


    # 1. Schema Validation - check columns and null counts
    print("Orders columns:", orders.columns.tolist())
    print("Orders nulls:\n", orders.isnull().sum())

    print("Order Items columns:", order_items.columns.tolist())
    print("Order Items nulls:\n", order_items.isnull().sum())

    print("Returns columns:", returns.columns.tolist())
    print("Returns nulls:\n", returns.isnull().sum())

    print("Return Items columns:", return_items.columns.tolist())
    print("Return Items nulls:\n", return_items.isnull().sum())

    print("Product Catalog columns:", product_catalog.columns.tolist())
    print("Product Catalog nulls:\n", product_catalog.isnull().sum())

    print("Customers columns:", customers.columns.tolist())
    print("Customers nulls:\n", customers.isnull().sum())


    # 2. Referential Integrity
    print("\nReferential Integrity Checks:")

    # orders.customer_id in customers.customer_id
    invalid_cust_in_orders = orders[~orders['customer_id'].isin(customers['customer_id'])]
    print(f"Orders with invalid customer_id count: {len(invalid_cust_in_orders)}")

    # order_items.order_id in orders.order_id
    invalid_orderid_in_order_items = order_items[~order_items['order_id'].isin(orders['order_id'])]
    print(f"Order items with invalid order_id count: {len(invalid_orderid_in_order_items)}")

    # returns.order_id in orders.order_id
    invalid_orderid_in_returns = returns[~returns['order_id'].isin(orders['order_id'])]
    print(f"Returns with invalid order_id count: {len(invalid_orderid_in_returns)}")

    # return_items.return_id in returns.return_id
    invalid_returnid_in_return_items = return_items[~return_items['return_id'].isin(returns['return_id'])]
    print(f"Return items with invalid return_id count: {len(invalid_returnid_in_return_items)}")

    # return_items.order_id in orders.order_id
    invalid_orderid_in_return_items = return_items[~return_items['order_id'].isin(orders['order_id'])]
    print(f"Return items with invalid order_id count: {len(invalid_orderid_in_return_items)}")

    # product references
    invalid_product_in_order_items = order_items[~order_items['product_id'].isin(product_catalog['product_id'])]
    print(f"Order items with invalid product_id count: {len(invalid_product_in_order_items)}")

    invalid_product_in_return_items = return_items[~return_items['product_id'].isin(product_catalog['product_id'])]
    print(f"Return items with invalid product_id count: {len(invalid_product_in_return_items)}")

    # 3. Business logic checks

    # order_total equals sum of order_items per order
    order_items['item_total'] = order_items['quantity'] * order_items['unit_price']
    order_totals_calc = order_items.groupby('order_id')['item_total'].sum().reset_index()
    merged_orders = orders.merge(order_totals_calc, on='order_id', how='left')
    merged_orders['order_total_diff'] = abs(merged_orders['order_total'] - merged_orders['item_total'])
    order_total_mismatches = merged_orders[merged_orders['order_total_diff'] > 0.01]
    print(f"Orders with mismatched order_total: {len(order_total_mismatches)}")

    # refunded_amount equals sum of return_items per return
    return_items['refund_total'] = return_items['refunded_amount']
    return_totals_calc = return_items.groupby('return_id')['refund_total'].sum().reset_index()
    merged_returns = returns.merge(return_totals_calc, on='return_id', how='left')
    merged_returns['refund_diff'] = abs(merged_returns['refunded_amount'] - merged_returns['refund_total'])
    return_total_mismatches = merged_returns[merged_returns['refund_diff'] > 0.01]
    print(f"Returns with mismatched refunded_amount: {len(return_total_mismatches)}")

    # Return dates >= order dates
    returns_with_order_dates = returns.merge(orders[['order_id', 'order_date']], on='order_id', how='left')
    returns_with_order_dates['order_date'] = pd.to_datetime(returns_with_order_dates['order_date'])
    returns_with_order_dates['return_date'] = pd.to_datetime(returns_with_order_dates['return_date'])
    invalid_dates = returns_with_order_dates[
        returns_with_order_dates['return_date'] < returns_with_order_dates['order_date']
    ]
    print(f"Returns with return_date before order_date: {len(invalid_dates)}")

    # Agent assignment check summary (basic)
    orders_agents = orders.groupby(['order_channel', 'agent_id']).size()
    returns_agents = returns.groupby(['return_channel', 'agent_id']).size()
    print("\nOrders agent assignment counts:\n", orders_agents)
    print("\nReturns agent assignment counts:\n", returns_agents)

    # 4. Distribution summary for key numeric columns
    print("\nNumeric summaries:")
    print("Orders order_total stats:\n", orders['order_total'].describe())
    print("Returns refunded_amount stats:\n", returns['refunded_amount'].describe())
    print("Order Items quantity stats:\n", order_items['quantity'].describe())
    print("Return Items quantity_returned stats:\n", return_items['quantity_returned'].describe())


if __name__ == "__main__":
    main()
