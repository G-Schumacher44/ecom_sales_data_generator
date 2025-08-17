"""generator_orders.py

Responsible for generating orders and order_items data.
Includes order ID generation, guest and regular orders, addresses, and item generation.
"""

import random
from typing import List, Dict, Any, Tuple
from datetime import datetime, date
from collections import defaultdict

from faker import Faker

from .generator_common_utils import assign_agent, generate_address, get_vocab, get_param
from utils.date_utils import safe_date_between


def generate_order_id(faker_instance: Faker) -> str:
    '''Generate a unique order ID.'''
    return faker_instance.unique.bothify(text="SO-########")


def _populate_order_details(order: Dict, customer: Dict, config: Any, faker_instance: Faker) -> Dict:
    """Populates an order dictionary with additional details like channel, payment, and shipping."""
    expedited_pct = get_param(config, "expedited_pct", 0.2)
    customer_tiers = get_vocab(config, "customer_tiers", ["Bronze", "Silver", "Gold", "Platinum"])
    payment_methods = config.payment_methods
    shipping_speed_distribution = get_param(config, "shipping_speed_distribution", None)

    if shipping_speed_distribution:
        shipping_speeds = list(shipping_speed_distribution.keys())
        shipping_weights = list(shipping_speed_distribution.values())
    else:
        shipping_speeds = get_vocab(config, "shipping_speeds", ["Standard", "Two-Day", "Overnight"])
        shipping_weights = None

    order_channel_distribution = get_param(config, "order_channel_distribution", {"Web": 0.85, "Phone": 0.15})
    channels = list(order_channel_distribution.keys())
    weights = list(order_channel_distribution.values())
    order_channel = random.choices(channels, weights=weights, k=1)[0]

    shipping_address = customer.get("mailing_address")
    billing_address = customer.get("billing_address")

    if not shipping_address:
        shipping_address = generate_address(faker_instance)
    if not billing_address:
        billing_address = shipping_address

    order.update({
        "order_channel": order_channel,
        "agent_id": assign_agent(order_channel, config),
        "shipping_address": shipping_address,
        "billing_address": billing_address,
    })

    if customer.get("is_guest"):
        order["customer_tier"] = None
        order["clv_bucket"] = None
    else:
        order["customer_tier"] = customer.get("loyalty_tier", random.choice(customer_tiers))
        tier_to_clv = {"Bronze": "Low", "Silver": "Medium", "Gold": "High", "Platinum": "High"}
        order["clv_bucket"] = tier_to_clv.get(order["customer_tier"], "Low")

    channel_specific_rules = config.channel_rules.get(order_channel, {})
    allowed_payments_for_channel = channel_specific_rules.get('allowed_payment_methods')

    if allowed_payments_for_channel:
        order["payment_method"] = random.choice(allowed_payments_for_channel)
    else:
        global_payment_dist = config.get_parameter('global_payment_method_distribution')
        if global_payment_dist:
            methods = list(global_payment_dist.keys())
            payment_weights = list(global_payment_dist.values())
            order["payment_method"] = random.choices(methods, weights=payment_weights, k=1)[0]
        else:
            order["payment_method"] = random.choice(payment_methods)

    if shipping_weights:
        order["shipping_speed"] = random.choices(shipping_speeds, weights=shipping_weights, k=1)[0]
    else:
        order["shipping_speed"] = random.choice(shipping_speeds)
    order["is_expedited"] = order["shipping_speed"] != "Standard"

    return order


def generate_orders(
    columns: List[str],
    num_rows: int,
    faker_instance: Faker,
    lookup_cache: Dict,
    config: Any,
) -> List[Dict[str, Any]]:
    """
    Generates orders from a list of 'converted' shopping carts.
    The number of orders is determined by the number of converted carts, not num_rows.
    """
    converted_carts = lookup_cache.get('converted_carts')
    if not converted_carts:
        print("Warning: No converted carts found. No orders will be generated.")
        return []

    all_customers = lookup_cache.get('customers')
    if not all_customers:
        raise ValueError("Customer data must be in lookup_cache for generate_orders.")

    customers_dict = {c['customer_id']: c for c in all_customers}

    orders = []
    order_to_cart_map = {}
    for cart in converted_carts:
        customer = customers_dict.get(cart['customer_id'])
        if not customer:
            continue

        order_id = generate_order_id(faker_instance)
        order = {
            "order_id": order_id,
            "customer_id": customer["customer_id"],
            "order_date": cart['created_at'],
            "email": customer["email"],
        }
        # Store the link between the new order and the source cart for item generation
        order_to_cart_map[order_id] = cart['cart_id']

        order = _populate_order_details(order, customer, config, faker_instance)
        orders.append(order)

    lookup_cache['order_to_cart_map'] = order_to_cart_map
    return orders


def generate_order_items(columns: List[str], num_rows: int, faker_instance: Faker, lookup_cache: Dict, config: Any) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Generate order items by mapping them from cart items of converted carts."""
    import pandas as pd
    
    orders = lookup_cache["orders"]
    if not orders:
        print("Info: No orders found in cache. Skipping order_items generation.")
        return [], {}

    cart_items = lookup_cache.get("cart_items")
    if not cart_items:
        raise ValueError("Cart items must be present in lookup_cache to generate order items.")

    # Retrieve the mapping created by the orders generator
    order_to_cart_map = lookup_cache.get('order_to_cart_map', {})
    if not order_to_cart_map:
        print("Warning: 'order_to_cart_map' not found in cache. Order items cannot be generated from carts.")

    cart_items_by_cart_id = defaultdict(list)
    for item in cart_items:
        cart_items_by_cart_id[item['cart_id']].append(item)

    all_items = []
    order_updates = {}

    for order in orders:
        order_id = order['order_id']
        cart_id = order_to_cart_map.get(order_id)
        if not cart_id:
            continue

        source_cart_items = cart_items_by_cart_id.get(cart_id, [])
        order_total = 0.0

        for cart_item in source_cart_items:
            order_item = {
                "order_id": order_id,
                "product_id": cart_item["product_id"],
                "product_name": cart_item["product_name"],
                "category": cart_item["category"],
                "quantity": cart_item["quantity"],
                "unit_price": cart_item["unit_price"],
            }
            all_items.append(order_item)
            order_total += order_item['quantity'] * order_item['unit_price']

        order_updates[order_id] = {"order_total": round(order_total, 2)}

        free_shipping_min_order = get_param(config, "free_shipping_min_order", 100.0)
        shipping_costs = get_param(config, "shipping_costs", {"Standard": 5.0, "Two-Day": 45.0, "Overnight": 80.0})

        if order["shipping_speed"] == "Standard" and order_total >= free_shipping_min_order:
            order_updates[order["order_id"]]["shipping_cost"] = 0.0
        else:
            order_updates[order["order_id"]]["shipping_cost"] = float(shipping_costs.get(order["shipping_speed"], 0.0))

    if all_items:
        order_items_df = pd.DataFrame(all_items)
        qty_sum = order_items_df.groupby("order_id")["quantity"].sum().to_dict()
        for order_id, total_items in qty_sum.items():
            if order_id in order_updates:
                order_updates[order_id]["total_items"] = total_items

    return all_items, order_updates