"""generator_orders.py

Responsible for converting shopping carts into orders and generating order items.
Includes logic for dynamic tier evolution.
"""

import random
from typing import List, Dict, Any
from datetime import datetime
from faker import Faker
from .generator_common_utils import get_param, get_vocab, assign_agent

def generate_order_id(faker_instance: Faker) -> str:
    """Generate a unique order ID."""
    return faker_instance.unique.bothify(text="ORD-########")

def generate_orders(columns: List[str], num_rows: int, faker_instance: Faker, lookup_cache: Dict, config: Any) -> List[Dict[str, Any]]:
    """
    Generates order records from converted shopping carts.
    Includes logic to evolve a customer's tier with each new order.
    """
    converted_carts = lookup_cache.get("converted_carts", [])
    customers_by_id = {c['customer_id']: c for c in lookup_cache.get('customers', [])}

    # --- Get parameters for dynamic order generation ---
    # Tier and CLV thresholds
    tier_thresholds = config.get_parameter('tier_spend_thresholds', {'Bronze': 0})
    clv_thresholds = config.get_parameter('clv_spend_thresholds', {'Low': 0})
    sorted_tiers = sorted(tier_thresholds.items(), key=lambda item: item[1], reverse=True)
    sorted_clv = sorted(clv_thresholds.items(), key=lambda item: item[1], reverse=True)

    # Channel and shipping distributions
    order_channel_dist = config.get_parameter('order_channel_distribution', {'Web': 1.0})
    shipping_speed_dist = config.get_parameter('shipping_speed_distribution', {'Standard': 1.0})
    shipping_costs = config.get_parameter('shipping_costs', {'Standard': 5.0})
    channel_rules = config.get_parameter('channel_rules', {})
    global_payment_methods = config.get_parameter('global_payment_method_distribution', {'Credit Card': 1.0})
    expedited_pct = config.get_parameter('expedited_pct', 20) / 100.0

    # Cache to track a customer's cumulative spend as it evolves
    customer_cumulative_spend = {}

    orders = []
    for cart in sorted(converted_carts, key=lambda x: x['created_at']):
        customer_id = cart["customer_id"]
        customer = customers_by_id.get(customer_id)
        if not customer:
            continue

        # Update cumulative spend for this customer
        previous_spend = customer_cumulative_spend.get(customer_id, 0)
        new_spend = previous_spend + cart["cart_total"]
        customer_cumulative_spend[customer_id] = new_spend

        # Determine the customer's earned tier and CLV bucket based on their new cumulative spend.
        earned_tier = None
        for tier, threshold in sorted_tiers:
            if new_spend >= threshold:
                earned_tier = tier
                break
        
        earned_clv_bucket = None
        for bucket, threshold in sorted_clv:
            if new_spend >= threshold:
                earned_clv_bucket = bucket
                break

        # Assign order channel dynamically based on configured distribution
        channels = list(order_channel_dist.keys())
        weights = list(order_channel_dist.values())
        order_channel = random.choices(channels, weights=weights, k=1)[0]

        # Assign payment method based on channel rules
        channel_specific_methods = channel_rules.get(order_channel, {}).get('allowed_payment_methods')
        if channel_specific_methods:
            payment_method = random.choice(channel_specific_methods)
        else:
            # Fallback to global distribution if no specific rule
            payment_method = random.choices(list(global_payment_methods.keys()), weights=list(global_payment_methods.values()), k=1)[0]

        # Assign shipping speed and cost
        shipping_speeds = list(shipping_speed_dist.keys())
        shipping_weights = list(shipping_speed_dist.values())
        shipping_speed = random.choices(shipping_speeds, weights=shipping_weights, k=1)[0]
        shipping_cost = shipping_costs.get(shipping_speed, 5.0)
        agent_id = assign_agent(order_channel, config)

        order = {
            "order_id": generate_order_id(faker_instance),
            "total_items": 0, # Will be patched
            "order_date": cart["created_at"],
            "customer_id": customer_id,
            "email": customer["email"],
            "order_channel": order_channel,
            "is_expedited": random.random() < expedited_pct,
            "customer_tier": earned_tier,
            "order_total": cart["cart_total"],
            "payment_method": payment_method,
            "shipping_speed": shipping_speed,
            "shipping_cost": shipping_cost,
            "agent_id": agent_id,
            "shipping_address": customer["mailing_address"],
            "billing_address": customer["billing_address"],
            "clv_bucket": earned_clv_bucket,
            "is_reactivated": cart.get("is_reactivation_cart", False)
        }
        orders.append(order)

    return orders

def generate_order_items(columns: List[str], num_rows: int, faker_instance: Faker, lookup_cache: Dict, config: Any) -> (List[Dict[str, Any]], Dict[str, Dict[str, Any]]):
    """
    Generates order items by transferring them from converted carts.
    """
    converted_carts = lookup_cache.get("converted_carts", [])
    cart_items = lookup_cache.get("cart_items", [])
    orders = lookup_cache.get("orders", [])

    if not converted_carts or not cart_items or not orders:
        return [], {}

    # Create mappings for quick lookup
    cart_id_to_order_id = {cart['cart_id']: order['order_id'] for cart, order in zip(sorted(converted_carts, key=lambda x: x['created_at']), orders)}
    
    all_order_items = []
    order_updates = {}

    # Group cart items by cart_id
    items_by_cart = {}
    for item in cart_items:
        cart_id = item['cart_id']
        if cart_id not in items_by_cart:
            items_by_cart[cart_id] = []
        items_by_cart[cart_id].append(item)

    for cart_id, order_id in cart_id_to_order_id.items():
        items_in_cart = items_by_cart.get(cart_id, [])
        for item in items_in_cart:
            order_item = item.copy()
            order_item.pop('cart_item_id', None)
            order_item.pop('cart_id', None)
            order_item['order_id'] = order_id
            all_order_items.append(order_item)
        order_updates[order_id] = {"total_items": len(items_in_cart)}

    return all_order_items, order_updates