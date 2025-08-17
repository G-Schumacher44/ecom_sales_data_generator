"""generator_returns.py

Responsible for generating returns and return_items data.
Includes return generation, return item generation, and management of returned quantities.
"""

import random
from typing import List, Dict, Any
from faker import Faker
from collections import defaultdict
from datetime import datetime, timedelta

from generators.generator_common_utils import assign_agent, get_vocab, get_param

class ReturnItemGenerationHelper:
    def __init__(self, order_items: List[Dict[str, Any]]):
        self.returned_so_far = defaultdict(int)
        self.product_details_in_orders = defaultdict(lambda: {'original_quantity': 0})
        self.products_per_order = defaultdict(list)

        for item in order_items:
            order_id = item.get("order_id")
            product_id = item.get("product_id")
            key = (order_id, product_id)

            if None in key or not isinstance(item.get("quantity"), int) or not isinstance(item.get("unit_price"), (int, float)):
                continue

            self.product_details_in_orders[key]['original_quantity'] += item.get("quantity")
            self.product_details_in_orders[key]['unit_price'] = item.get("unit_price")
            self.product_details_in_orders[key]['product_name'] = item.get("product_name", "")
            self.product_details_in_orders[key]['category'] = item.get("category", "")

            if product_id not in self.products_per_order[order_id]:
                self.products_per_order[order_id].append(product_id)

    def _determine_products_to_return(self, order_id: str, return_type: str) -> List[int]:
        original_products = self.products_per_order.get(order_id, [])
        if not original_products:
            raise ValueError(f"No order items found for order_id {order_id}")

        if return_type == "Full":
            return list(original_products)
        elif return_type == "Partial":
            subset_size = random.randint(1, max(1, len(original_products)))
            return random.sample(original_products, k=subset_size)
        else:
            raise ValueError(f"Invalid return_type {return_type}")

    def process_single_return(self, return_entry: Dict[str, Any], return_item_id_start: int) -> (List[Dict[str, Any]], float, int):
        order_id = return_entry.get("order_id")
        return_id = return_entry.get("return_id")
        return_type = return_entry.get("return_type")

        if not all([isinstance(order_id, str) and order_id.startswith("SO-"),
                    isinstance(return_id, str) and return_id.startswith("RET-"),
                    return_type in ("Partial", "Full")]):
            raise ValueError(f"Invalid return entry: {return_entry}")

        product_ids = self._determine_products_to_return(order_id, return_type)

        items = []
        total_refund = 0.0
        next_return_item_id = return_item_id_start

        for product_id in product_ids:
            key = (order_id, product_id)
            details = self.product_details_in_orders.get(key)

            if not details or details['original_quantity'] == 0:
                continue

            original_qty = details['original_quantity']
            unit_price = details['unit_price']
            product_name = details['product_name']
            category = details['category']

            already_returned = self.returned_so_far.get(key, 0)
            qty_available = original_qty - already_returned
            if qty_available <= 0:
                continue

            if return_type == "Partial":
                requested_qty = max(1, round(original_qty * random.uniform(0.3, 0.8)))
                qty_to_return = min(requested_qty, qty_available)
            else:
                qty_to_return = qty_available

            refunded_amount = round(qty_to_return * float(unit_price), 2)

            item = {
                "return_item_id": next_return_item_id,
                "return_id": return_id,
                "order_id": order_id,
                "product_id": product_id,
                "product_name": product_name,
                "category": category,
                "quantity_returned": qty_to_return,
                "unit_price": unit_price,
                "refunded_amount": refunded_amount,
            }

            items.append(item)
            self.returned_so_far[key] += qty_to_return
            total_refund += refunded_amount
            next_return_item_id += 1

        return items, round(total_refund, 2), next_return_item_id


def generate_returns(columns: List[str], num_rows: int, faker_instance: Faker, lookup_cache: Dict, config: Any, global_end_date: datetime.date = None) -> List[Dict[str, Any]]:
    orders = lookup_cache.get('orders')
    order_items = lookup_cache.get('order_items')

    if not orders:
        raise ValueError("Orders must be generated before returns.")
    if not order_items:
        print("Warning: Order items not found. Cannot generate returns with category-specific rates.")
        return []

    # NEW: Calculate number of returns based on a rate, not a fixed number
    return_rate = config.get_parameter("return_rate", 0.20)
    num_returns_to_generate = int(len(orders) * return_rate)
    print(f"  Targeting {num_returns_to_generate} returns based on a {return_rate:.2%} return rate for {len(orders)} orders.")

    # Get vocab and parameterized values from config
    return_reasons = get_vocab(config, "return_reasons", ["Defective", "No longer needed", "Wrong item", "Other"])
    all_return_channels = get_vocab(config, "return_channels", ["Web", "Phone"])
    return_max_lag_days = get_param(config, "return_max_lag_days", 30)
    category_rates = get_param(config, 'category_return_rates', {})
    default_rate = category_rates.get('default', 0.20)
    reason_weights_config = get_param(config, 'baseline_return_reason_weights', {})
    default_reason_weights = reason_weights_config.get('default', {})

    # NEW: Create lookups for original order channel and payment method
    order_id_to_channel = {order['order_id']: order['order_channel'] for order in orders}
    order_id_to_payment_method = {order['order_id']: order['payment_method'] for order in orders}

    # Create a map of order_id to its product categories for efficient lookup
    order_id_to_categories = defaultdict(list)
    for item in order_items:
        order_id_to_categories[item['order_id']].append(item['category'].lower())

    returnable_orders = []
    for order in orders:
        categories_in_order = order_id_to_categories.get(order['order_id'], [])
        if not categories_in_order:
            continue  # Skip orders with no items

        # Determine return propensity based on the highest-risk category in the order
        propensity = max(
            (category_rates.get(cat, default_rate) for cat in set(categories_in_order)),
            default=default_rate
        )

        # Decide if this order will be returned based on its calculated propensity
        if random.random() < propensity:
            returnable_orders.append(order)

    # Instead of using all returnable_orders, sample from them to meet the target rate
    if len(returnable_orders) > num_returns_to_generate:
        orders_to_return = random.sample(returnable_orders, num_returns_to_generate)
    else:
        orders_to_return = returnable_orders # Return all possible if less than target

    if global_end_date is None:
        global_end_date = datetime.now().date()

    returns = []
    for order in orders_to_return:
        return_id = faker_instance.unique.bothify(text="RET-########")
        return_type = random.choice(["Partial", "Full"])
        order_date_str = order["order_date"]
        order_date = datetime.strptime(order_date_str, "%Y-%m-%d")

        # Determine a realistic return reason using weighted choice
        categories_in_order = order_id_to_categories.get(order['order_id'], [])
        primary_category = categories_in_order[0] if categories_in_order else 'default'
        reason_weights = reason_weights_config.get(primary_category, default_reason_weights)

        if reason_weights:
            reasons = list(reason_weights.keys())
            weights = list(reason_weights.values())
            chosen_reason = random.choices(reasons, weights=weights, k=1)[0]
        else: # Fallback to old method if no weights are configured
            chosen_reason = random.choice(return_reasons)

        now = datetime.combine(global_end_date, datetime.min.time())        
        # Calculate days_since_order, but cap by parameterized lag
        days_since_order = (now - order_date).days
        if days_since_order < 0:
            days_since_order = 0  # fallback
        # Use min(days_since_order, return_max_lag_days)
        max_lag = min(days_since_order, return_max_lag_days)
        return_date_obj = order_date + timedelta(days=random.randint(0, max_lag))
        if return_date_obj.date() > global_end_date:
            return_date_obj = datetime.combine(global_end_date, datetime.min.time())

        # NEW: Determine return_channel based on order_channel preference
        original_order_channel = order_id_to_channel.get(order["order_id"])
        channel_specific_rules = config.channel_rules.get(original_order_channel, {})
        preferred_return_channel = channel_specific_rules.get('return_channel_preference')

        # Use the configured probability to follow the preference
        if preferred_return_channel and random.random() < config.get_parameter('return_channel_preference_prob', 0.90):
            return_channel = preferred_return_channel
        else:
            # Fallback: if no preference or random roll fails, choose from general return_channels
            return_channel = random.choice(all_return_channels)

        ret = {
            "return_id": return_id,
            "order_id": order["order_id"],
            "customer_id": order["customer_id"],
            "return_type": return_type,
            "return_date": return_date_obj.date().isoformat(),
            "reason": chosen_reason,
            "refunded_amount": 0.0,  # to be updated by return_items generator
            "return_channel": return_channel,
            "agent_id": assign_agent(return_channel, config),
        }

        # NEW: Determine refund method based on original payment method
        original_payment_method = order_id_to_payment_method.get(order['order_id'])
        if original_payment_method == "PayPal":
            ret['refund_method'] = "PayPal"
        elif original_payment_method in ["Credit Card", "Apple Pay", "Google Pay"]:
            ret['refund_method'] = "Credit Card" # Refund to the card associated with these methods.
        elif original_payment_method == "ACH":
            ret['refund_method'] = "ACH"
        elif original_payment_method == "Cash": # For in-store payments
            ret['refund_method'] = "Cash"
        elif original_payment_method in ["Ebay", "NewEgg"]: # Specific platform payments
            ret['refund_method'] = original_payment_method # Refund through the platform.
        else:
            ret['refund_method'] = "Unknown" # Fallback

        matching_order = next((o for o in orders if o['order_id'] == ret['order_id']), None)
        if matching_order:
            # Assuming lookup_cache['customers'] is a list of dicts
            matching_customer = next((c for c in lookup_cache['customers'] if c['customer_id'] == matching_order['customer_id']), None)
            ret['email'] = matching_customer['email'] if matching_customer else None
        else:
            ret['email'] = None
        returns.append(ret)
    return returns


def generate_return_items(columns: List[str], num_rows: int, faker_instance: Faker, lookup_cache: Dict, config: Any) -> (List[Dict[str, Any]], Dict[str, float]):
    if 'returns' not in lookup_cache or not lookup_cache['returns']:
        raise ValueError('Returns must be generated before return items.')
    if 'order_items' not in lookup_cache or not lookup_cache['order_items']:
        raise ValueError('Order items must be present before generating return items.')

    returns = lookup_cache['returns']
    order_items = lookup_cache['order_items']

    # Track max refund per order_id based on order_total
    order_total_map = {o['order_id']: o.get('order_total', 0.0) for o in lookup_cache['orders']}
    order_refunded_tracker = defaultdict(float)

    return_helper = ReturnItemGenerationHelper(order_items)

    all_return_items = []
    current_return_item_id = 1
    return_updates = {} # Changed from refund_totals to be more descriptive

    for ret in returns:
        try:
            order_id = ret.get("order_id")
            items, total_refund, next_id = return_helper.process_single_return(ret, current_return_item_id)
            filtered_items = []
            total_refund_capped = 0.0
            for item in items:
                remaining_refundable = order_total_map.get(order_id, 0.0) - order_refunded_tracker[order_id]
                if remaining_refundable <= 0:
                    continue
                max_quantity = int(remaining_refundable // item["unit_price"])
                if max_quantity <= 0:
                    continue
                item["quantity_returned"] = min(item["quantity_returned"], max_quantity)
                item["refunded_amount"] = round(item["quantity_returned"] * item["unit_price"], 2)
                filtered_items.append(item)
                order_refunded_tracker[order_id] += item["refunded_amount"]
                total_refund_capped += item["refunded_amount"]

            all_return_items.extend(filtered_items)
            return_updates[ret["return_id"]] = round(total_refund_capped, 2)
            current_return_item_id = next_id
        except ValueError as e:
            print(f"Warning: Skipping return {ret.get('return_id')} due to error: {e}")
            return_updates[ret["return_id"]] = 0.0

    return all_return_items, return_updates
