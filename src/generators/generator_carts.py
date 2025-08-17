"""generator_carts.py

Responsible for generating shopping cart and cart_items data, representing
pre-purchase user sessions.
"""

import random
from typing import List, Dict, Any
from collections import defaultdict
import numpy as np
from datetime import datetime, timedelta
from faker import Faker
from .generator_common_utils import get_param
from utils.date_utils import safe_date_between

def generate_cart_id(faker_instance: Faker) -> str:
    """Generate a unique cart ID."""
    return faker_instance.unique.bothify(text="CART-########")

def generate_shopping_carts(columns: List[str], num_rows: int, faker_instance: Faker, lookup_cache: Dict, config: Any) -> List[Dict[str, Any]]:
    """
    Generates shopping cart sessions by simulating a customer's lifecycle, including
    initial and repeat visits. This creates realistic data for cohort analysis.
    `num_rows` here is used to select the number of customers to simulate sessions for.
    It does not guarantee an exact number of output carts.
    """
    customers = lookup_cache.get('customers')
    if not customers:
        raise ValueError("Customers must be generated before shopping carts.")

    global_start_date = lookup_cache.get("global_start_date")
    global_end_date = lookup_cache.get("global_end_date")

    # Get repeat purchase settings from config
    repeat_settings = config.get_parameter('repeat_purchase_settings', {})
    propensity_by_tier = repeat_settings.get('propensity_by_tier', {})
    delay_range = repeat_settings.get('time_delay_days_range', [30, 180])

    carts = []
    # We will simulate sessions for a number of customers up to num_rows.
    # This determines the pool of customers who will have at least one cart.
    customers_to_simulate = random.sample(customers, min(num_rows, len(customers)))

    for customer in customers_to_simulate:
        # All customers get at least one initial cart session
        signup_date_str = customer.get('signup_date')

        first_cart_date = None
        if signup_date_str: # Registered customer
            try:
                signup_date = datetime.fromisoformat(signup_date_str).date()
                # The first cart is created sometime after signup
                first_cart_date = safe_date_between(signup_date, global_end_date)
            except (TypeError, ValueError):
                continue # Skip if signup_date is invalid
        else: # Guest customer
            # A guest's first cart can appear anytime in the global window
            first_cart_date = safe_date_between(global_start_date, global_end_date)

        # Generate the first cart
        last_cart_date = first_cart_date
        carts.append({
            "cart_id": generate_cart_id(faker_instance),
            "customer_id": customer['customer_id'],
            "created_at": first_cart_date.isoformat(),
            "status": "open",
            "cart_total": 0.0
        })

        # --- Simulate Repeat Visits ---
        # Determine propensity to return based on loyalty tier
        # NOTE: With the new Poisson model, propensity is interpreted as the average number of repeat visits (lambda).
        tier = customer.get('loyalty_tier')
        avg_repeat_visits = propensity_by_tier.get(tier, propensity_by_tier.get('default', 0.1))

        # Use a Poisson distribution to determine the number of repeat visits for this customer.
        # This is a more robust and intuitive model than the previous `while` loop.
        num_repeat_visits = np.random.poisson(lam=avg_repeat_visits)

        for _ in range(num_repeat_visits):
            delay = random.randint(delay_range[0], delay_range[1])
            next_cart_date = last_cart_date + timedelta(days=delay)

            if next_cart_date > global_end_date:
                continue # Skip this visit if it's out of bounds, but allow subsequent ones

            carts.append({
                "cart_id": generate_cart_id(faker_instance),
                "customer_id": customer['customer_id'],
                "created_at": next_cart_date.isoformat(),
                "status": "open",
                "cart_total": 0.0
            })
            last_cart_date = next_cart_date

    return carts

def generate_cart_items(columns: List[str], num_rows: int, faker_instance: Faker, lookup_cache: Dict, config: Any) -> (List[Dict[str, Any]], Dict[str, Dict[str, Any]]):
    """
    Generates items for each shopping cart.
    """
    carts = lookup_cache.get("shopping_carts")
    if not carts:
        raise ValueError("Shopping carts must be generated before cart items.")

    products = lookup_cache.get("product_catalog")
    if not products:
        raise ValueError("Product catalog must be present in lookup_cache.")

    cart_items_table_config = config.get_table_config("cart_items")
    item_count_range = cart_items_table_config.get("item_count_range", [1, 8])

    all_items = []
    cart_updates = {}
    cart_item_id_counter = 1

    for cart in carts:
        num_items_in_cart = random.randint(item_count_range[0], item_count_range[1])
        cart_total = 0.0
        
        for _ in range(num_items_in_cart):
            product = random.choice(products)
            quantity = random.randint(1, 5)
            item_total = product["unit_price"] * quantity

            item = {
                "cart_item_id": cart_item_id_counter,
                "cart_id": cart["cart_id"],
                "product_id": product["product_id"],
                "product_name": product["product_name"],
                "category": product["category"],
                "quantity": quantity,
                "unit_price": product["unit_price"],
            }
            all_items.append(item)
            cart_total += item_total
            cart_item_id_counter += 1
        
        cart_updates[cart["cart_id"]] = {"cart_total": round(cart_total, 2)}

    return all_items, cart_updates