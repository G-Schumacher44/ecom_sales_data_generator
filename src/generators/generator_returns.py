"""generator_returns.py

Responsible for generating returns and their associated items, with logic
for multi-item and partial returns.
"""

import random
from typing import List, Dict, Any
from datetime import datetime, timedelta
from faker import Faker
from .generator_common_utils import get_param, get_vocab
from utils.date_utils import safe_date_between

def generate_return_id(faker_instance: Faker) -> str:
    """Generate a unique return ID."""
    return faker_instance.unique.bothify(text="RTN-########")

def _generate_single_return(order, faker_instance, config, global_end_date, timing_dist, after_date=None):
    """Helper to generate a single return record for a given order."""
    order_date = datetime.fromisoformat(order["order_date"]).date()
    
    # Determine return date based on timing distribution
    rand_val = random.random()
    min_delay = 1
    max_delay = 30
    for days, prob in timing_dist:
        if rand_val <= prob:
            max_delay = days
            break
        min_delay = days + 1

    # If this is a second return, ensure it happens after the first
    start_return_date = order_date
    if after_date:
        first_return_date = datetime.fromisoformat(after_date).date()
        start_return_date = max(order_date, first_return_date + timedelta(days=1))

    potential_return_date = start_return_date + timedelta(days=random.randint(min_delay, max_delay))
    if potential_return_date > global_end_date:
        return None # Return would happen outside the simulation window

    return_reasons = get_vocab(config, 'return_reasons', ['Defective'])
    return {
        "return_id": generate_return_id(faker_instance),
        "order_id": order["order_id"],
        "customer_id": order["customer_id"],
        "email": order["email"],
        "return_date": potential_return_date.isoformat(),
        "reason": random.choice(return_reasons),
        "return_type": "Refund",
        "refunded_amount": 0.0, # Will be patched later
        "return_channel": order.get("order_channel", "Web"),
        "agent_id": order.get("agent_id"),
        "refund_method": order.get("payment_method", "Credit Card")
    }

def generate_returns(columns: List[str], num_rows: int, faker_instance: Faker, lookup_cache: Dict, config: Any, global_end_date: datetime.date) -> List[Dict[str, Any]]:
    """
    Generates return records for existing orders, supporting multiple return events per order.
    """
    orders = lookup_cache.get("orders")
    if not orders:
        return []
    customers_by_id = {c['customer_id']: c for c in lookup_cache.get('customers', [])}

    # NEW: Use channel-specific return rates, with a global fallback
    return_rate_config = config.get_parameter("return_rate_by_signup_channel", {})
    default_return_rate = config.get_parameter("return_rate", 0.25)
    multi_return_prob = config.get_parameter("multi_return_probability", 0.1)
    timing_dist = config.get_parameter("return_timing_distribution", [[30, 1.0]])

    returns = []
    for order in orders:
        customer = customers_by_id.get(order['customer_id'])
        signup_channel = customer.get('signup_channel') if customer else 'default'

        # Use channel-specific return rate, or fallback to global rate
        effective_return_rate = return_rate_config.get(signup_channel, default_return_rate)

        if random.random() < effective_return_rate:
            first_return = _generate_single_return(order, faker_instance, config, global_end_date, timing_dist)
            if first_return:
                returns.append(first_return)
                if random.random() < multi_return_prob:
                    second_return = _generate_single_return(order, faker_instance, config, global_end_date, timing_dist, after_date=first_return['return_date'])
                    if second_return:
                        returns.append(second_return)
    return returns

def generate_return_items(columns: List[str], num_rows: int, faker_instance: Faker, lookup_cache: Dict, config: Any) -> (List[Dict[str, Any]], Dict[str, float]):
    """
    Generates items for each return, supporting multi-item and partial returns.
    """
    returns = lookup_cache.get("returns")
    if not returns:
        return [], {}

    order_items = lookup_cache.get("order_items")
    if not order_items:
        raise ValueError("Order items must be generated before return items.")

    # Group order items by order_id for efficient lookup
    order_items_by_order = {}
    for item in order_items:
        order_id = item["order_id"]
        if order_id not in order_items_by_order:
            order_items_by_order[order_id] = []
        order_items_by_order[order_id].append(item)

    # NEW: Get reason-driven refund behavior from config
    refund_behavior_by_reason = config.get_parameter('refund_behavior_by_reason', {})
    default_refund_behavior = refund_behavior_by_reason.get('default', {'full_return_prob': 0.5, 'partial_quantity_prob': 0.4})

    all_return_items = []
    return_updates = {}
    return_item_id_counter = 1
    # Use a shared cache to track returned items across multiple return events for the same order.
    # This prevents an item from being returned more than once.
    returned_item_keys = lookup_cache.setdefault('returned_item_keys', set())

    for ret in returns:
        order_id = ret["order_id"]
        original_items = order_items_by_order.get(order_id, [])
        if not original_items:
            continue
        
        # Filter out items that have already been returned for this order
        available_items_to_return = [
            item for item in original_items 
            if (order_id, item['product_id']) not in returned_item_keys
        ]
        if not available_items_to_return:
            continue # All items for this order have been returned in a previous event

        # NEW: Determine refund behavior based on the return reason
        reason = ret.get('reason')
        behavior = refund_behavior_by_reason.get(reason, default_refund_behavior)
        full_return_prob = behavior.get('full_return_prob', 0.5)
        partial_quantity_prob = behavior.get('partial_quantity_prob', 0.4)

        # Decide which items to return
        if random.random() < full_return_prob:
            items_to_return = available_items_to_return # Return all remaining items
        else:
            # Partial return: select a random subset of items
            num_to_return = random.randint(1, len(available_items_to_return))
            items_to_return = random.sample(available_items_to_return, num_to_return)

        total_refunded_for_return = 0.0
        for item in items_to_return:
            # NEW: Allow for partial quantity returns on multi-quantity line items
            if item["quantity"] > 1 and random.random() < partial_quantity_prob:
                # Return a random quantity less than the original
                quantity_returned = random.randint(1, item["quantity"] - 1)
            else:
                quantity_returned = item["quantity"] # Return full quantity
            refunded_amount = item["unit_price"] * quantity_returned

            return_item = {
                "return_item_id": return_item_id_counter,
                "return_id": ret["return_id"],
                "order_id": order_id,
                "product_id": item["product_id"],
                "product_name": item["product_name"],
                "category": item["category"],
                "quantity_returned": quantity_returned,
                "unit_price": item["unit_price"],
                "cost_price": item["cost_price"],
                "refunded_amount": round(refunded_amount, 2)
            }
            all_return_items.append(return_item)
            total_refunded_for_return += refunded_amount
            return_item_id_counter += 1
            # Mark this item as returned for this order
            returned_item_keys.add((order_id, item['product_id']))

        # Prepare the update for the parent return record
        return_updates[ret["return_id"]] = round(total_refunded_for_return, 2)

    return all_return_items, return_updates