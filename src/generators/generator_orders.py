"""generator_orders.py

Responsible for generating orders and order_items data.
Includes order ID generation, guest and regular orders, addresses, and item generation.
"""

import random
from typing import List, Dict, Any
from datetime import datetime, date

from faker import Faker

from .generator_common_utils import assign_agent, generate_address, get_vocab, get_param
from utils.date_utils import safe_date_between


def generate_order_id(faker_instance: Faker) -> str:
    '''Generate a unique order ID.'''
    return faker_instance.unique.bothify(text="SO-########")


def _generate_orders_for_customer_list(
    num_orders_to_generate: int,
    faker_instance: Faker,
    config: Any,
    lookup_cache: Dict,
    customer_pool: List[Dict[str, Any]], # This pool can be regular_customers or guest_customers_list
    global_start_date: datetime.date,
    global_end_date: datetime.date,
) -> List[Dict[str, Any]]:
    '''Helper function to generate orders for a given list of customers (either regular or guest).'''
    orders = []
    
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

    customer_order_frequency_range = get_param(config, 'customer_order_frequency_range', [1, 3])

    if not customer_pool:
        return [] # No customers to generate orders for

    # Calculate how many unique customers we need to select to hit num_orders_to_generate
    # based on average orders per customer from the frequency range.
    avg_orders_per_customer = sum(customer_order_frequency_range) / 2
    num_unique_customers_for_orders = max(1, int(num_orders_to_generate / avg_orders_per_customer))

    # Ensure we don't pick more unique customers than available in the pool
    num_unique_customers_for_orders = min(num_unique_customers_for_orders, len(customer_pool))

    # --- Weighted Customer Selection for Realism ---
    # Give higher-tier customers a higher chance of placing an order.
    tier_weights = {"Platinum": 5, "Gold": 4, "Silver": 2, "Bronze": 1.5, None: 1}
    customer_weights = [tier_weights.get(c.get("loyalty_tier"), 1) for c in customer_pool]

    # Use random.choices with weights to select customers. This allows for replacement,
    # which is realistic (a customer can place multiple orders).
    if any(w > 0 for w in customer_weights):
        active_customers = random.choices(customer_pool, weights=customer_weights, k=num_unique_customers_for_orders)
    else: # Fallback if all weights are zero
        active_customers = random.sample(customer_pool, num_unique_customers_for_orders)

    order_count = 0
    customer_idx = 0

    # Distribute orders across active customers
    while order_count < num_orders_to_generate and active_customers: # Also check if active_customers is not empty
        customer = active_customers[customer_idx % len(active_customers)] # Use modulo for cycling through customers
        
        num_orders_for_this_customer = random.randint(
            customer_order_frequency_range[0], customer_order_frequency_range[1]
        )
        
        num_orders_for_this_customer = min(num_orders_for_this_customer, num_orders_to_generate - order_count)
        
        for _ in range(num_orders_for_this_customer):
            if order_count >= num_orders_to_generate: # Break if target is met during inner loop
                break

            order_id = generate_order_id(faker_instance)
            order_channel = random.choices(channels, weights=weights, k=1)[0]
            
            shipping_address = customer.get("mailing_address")
            billing_address = customer.get("billing_address")
            
            if not shipping_address: # Governance: ensure address is always present for an order
                shipping_address = generate_address(faker_instance)
            if not billing_address:
                billing_address = shipping_address

            order = {
                "order_id": order_id,
                "customer_id": customer["customer_id"],
                "order_channel": order_channel,
                "agent_id": assign_agent(order_channel, config),
                "shipping_address": shipping_address,
                "billing_address": billing_address,
                "email": customer["email"],
                "order_date": safe_date_between(global_start_date, global_end_date).isoformat(),
            }
            
            if customer.get("is_guest"):
                order["customer_tier"] = None
                order["clv_bucket"] = None
            else:
                order["customer_tier"] = customer.get("loyalty_tier", random.choice(customer_tiers))
                tier_to_clv = {
                    "Bronze": "Low", "Silver": "Medium", "Gold": "High", "Platinum": "High"
                }
                order["clv_bucket"] = tier_to_clv.get(order["customer_tier"], "Low")
                
            # --- NEW: Select payment method based on channel rules ---
            channel_specific_rules = config.channel_rules.get(order_channel, {})
            allowed_payments_for_channel = channel_specific_rules.get('allowed_payment_methods')

            if allowed_payments_for_channel:
                # If specific allowed methods are defined for this channel, use them.
                order["payment_method"] = random.choice(allowed_payments_for_channel)
            else:
                # Fallback: use global distribution if no specific rules for this channel's payment
                global_payment_dist = config.get_parameter('global_payment_method_distribution')
                if global_payment_dist:
                    methods = list(global_payment_dist.keys())
                    payment_weights = list(global_payment_dist.values())
                    order["payment_method"] = random.choices(methods, weights=payment_weights, k=1)[0]
                else:
                    # Final fallback: simple random choice from all defined payment methods
                    order["payment_method"] = random.choice(payment_methods)
            if shipping_weights:
                order["shipping_speed"] = random.choices(shipping_speeds, weights=shipping_weights, k=1)[0]
            else:
                order["shipping_speed"] = random.choice(shipping_speeds)
            order["is_expedited"] = order["shipping_speed"] != "Standard"
            
            orders.append(order)
            order_count += 1

        customer_idx += 1
        # If we cycled through all initially selected active customers, and still need more orders,
        # we will continue cycling through them.
        if customer_idx >= len(active_customers) and order_count < num_orders_to_generate:
            customer_idx = 0 # Reset index to reuse customers, if necessary, to hit target num_orders


    return orders


def generate_orders(
    columns: List[str],
    num_rows: int, # num_rows is the *total* number of orders desired
    faker_instance: Faker,
    lookup_cache: Dict,
    config: Any,
    all_customers: List[Dict[str, Any]] = None, # Renamed from 'customers' to 'all_customers' to avoid keyword conflict
    global_start_date: datetime.date = None,
    global_end_date: datetime.date = None,
) -> List[Dict[str, Any]]:
    '''Main orders generator function. Generates orders allowing multiple orders per customer.'''
    
    if global_start_date is None or global_end_date is None:
        raise ValueError("global_start_date and global_end_date must be provided to generate_orders.")

    if all_customers is None or not all_customers:
        raise ValueError("Customer data must be provided to generate_orders.")

    # Split all_customers into regular and guest based on 'is_guest' flag
    regular_customers = [c for c in all_customers if not c.get('is_guest')]
    guest_customers_list = [c for c in all_customers if c.get('is_guest')]

    # Get overall order distribution for guests vs. regular from config
    guest_order_ratio = config.raw_config.get('guest_order_ratio', 0.1)
    
    num_guest_orders_target = int(num_rows * guest_order_ratio)
    num_regular_orders_target = num_rows - num_guest_orders_target
    
    all_generated_orders = []

    if num_guest_orders_target > 0 and guest_customers_list:
        generated_guest_orders = _generate_orders_for_customer_list(
            num_guest_orders_target, faker_instance, config, lookup_cache,
            guest_customers_list, global_start_date, global_end_date
        )
        all_generated_orders.extend(generated_guest_orders)
        
    if num_regular_orders_target > 0 and regular_customers:
        generated_regular_orders = _generate_orders_for_customer_list(
            num_regular_orders_target, faker_instance, config, lookup_cache,
            regular_customers, global_start_date, global_end_date
        )
        all_generated_orders.extend(generated_regular_orders)

    # If the exact num_rows is critical, and due to random frequency/pool size,
    # we might not hit it exactly, you might trim or extend here.
    # For now, it will produce approximately `num_rows`.
    # Let's add a simple check to enforce exact num_rows for consistency.
    if len(all_generated_orders) > num_rows:
        return random.sample(all_generated_orders, num_rows)
    elif len(all_generated_orders) < num_rows and all_customers:
        # If we didn't hit the target, we can try to add more by reusing from existing generated orders
        # This is a simple way to fill to target if needed, but the core logic
        # in _generate_orders_for_customer_list should try its best.
        # This case implies customer_pool is too small relative to num_rows and frequency.
        print(f"Warning: Generated fewer orders ({len(all_generated_orders)}) than requested ({num_rows}).")
        # You could duplicate random orders here, but it might mess with other stats.
        # For now, we accept slightly fewer if customers are exhausted.
    
    return all_generated_orders


def generate_order_items(columns: List[str], num_rows: int, faker_instance: Faker, lookup_cache: Dict, config: Any) -> (List[Dict[str, Any]], Dict[str, Dict[str, Any]]):
    '''Generate order items linked to orders.'''
    import pandas as pd
    
    if "orders" not in lookup_cache or not lookup_cache["orders"]:
        raise ValueError("Orders must be generated before order items.")

    if "product_catalog" not in lookup_cache or not lookup_cache["product_catalog"]:
        raise ValueError("Product catalog must be present in lookup_cache.")

    orders = lookup_cache["orders"]
    products = lookup_cache["product_catalog"]
    all_items = []
    order_updates = {}

    item_count_range = lookup_cache.get("item_count_range", [1, 3])

    for order in orders:
        items, total = _generate_items_for_single_order(order, products, item_count_range, faker_instance)
        all_items.extend(items)
        order_updates[order["order_id"]] = {"order_total": total}
        free_shipping_min_order = get_param(config, "free_shipping_min_order", 100.0)
        shipping_costs = get_param(config, "shipping_costs", {
            "Standard": 5.0,
            "Two-Day": 12.0,
            "Overnight": 20.0,
        })

        if order["shipping_speed"] == "Standard" and total >= free_shipping_min_order:
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

def _generate_items_for_single_order(order: Dict[str, Any], products: List[Dict[str, Any]], item_count_range: List[int], faker_instance: Faker) -> (List[Dict[str, Any]], float):
    '''Generate order items for a single order and compute total.'''
    items = []
    total = 0.0
    num_items = max(1, random.randint(item_count_range[0], item_count_range[1]))

    for _ in range(num_items):
        product = random.choice(products)
        quantity = random.randint(1, 5)

        item_total = product["unit_price"] * quantity
        item = {
            "order_id": order["order_id"],
            "product_id": product["product_id"],
            "product_name": product["product_name"],
            "category": product["category"],
            "quantity": quantity,
            "unit_price": product["unit_price"],
        }
        items.append(item)
        total += item_total

    return items, round(total, 2)