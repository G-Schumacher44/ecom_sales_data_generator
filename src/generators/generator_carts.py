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
from .generator_common_utils import get_param, get_vocab
from utils.date_utils import safe_date_between

def generate_cart_id(faker_instance: Faker) -> str:
    """Generate a unique cart ID."""
    return faker_instance.unique.bothify(text="CART-########")

def generate_shopping_carts(columns: List[str], num_rows: int, faker_instance: Faker, lookup_cache: Dict, config: Any) -> List[Dict[str, Any]]:
    """
    Generates shopping cart sessions. The process is two-fold:
    1. It creates a base number of initial shopping sessions (`num_rows`), assigning
       them randomly to the pool of customers. This simulates initial traffic.
    2. For each customer who had at least one initial session, it simulates a
       realistic lifecycle of repeat visits based on their attributes.
    """
    customers = lookup_cache.get('customers')
    if not customers:
        raise ValueError("Customers must be generated before shopping carts.")

    global_start_date = lookup_cache.get("global_start_date")
    global_end_date = lookup_cache.get("global_end_date")

    time_to_first_cart_range = config.get_parameter('time_to_first_cart_days_range', [1, 30])
    repeat_settings = config.get_parameter('repeat_purchase_settings', {})
    propensity_config = repeat_settings.get('propensity_by_channel_and_tier', {})
    time_delay_config = repeat_settings.get('time_delay_by_channel_and_tier', {})
    default_delay_range = [30, 180] # A sensible default
    retention_shocks = config.get_parameter('retention_shocks', {})
    seasonal_factors = config.get_parameter('seasonal_factors', {})
    reactivation_settings = config.get_parameter('reactivation_settings', {})

    carts = []
    
    # --- 1. Generate Initial Shopping Sessions ---
    # `num_rows` represents the volume of initial traffic.
    # We sample customers *with replacement* to assign these initial sessions.
    initial_cart_assignments = random.choices(customers, k=num_rows)
    
    # Keep track of the last cart date for each customer to chain repeat visits correctly.
    customer_last_cart_info = {}

    for customer in initial_cart_assignments:
        signup_date_str = customer.get('signup_date')
        
        initial_cart_date = None
        if signup_date_str:
            try:
                signup_date = datetime.fromisoformat(signup_date_str).date()
                delay = timedelta(days=random.randint(time_to_first_cart_range[0], time_to_first_cart_range[1]))
                potential_date = signup_date + delay
                # Ensure the date is within the global simulation window
                if global_start_date <= potential_date <= global_end_date:
                    initial_cart_date = potential_date
            except (TypeError, ValueError):
                pass # Will fall through and be treated like a guest for this cart
        
        # If it's a guest or the registered customer's date was invalid/out of bounds
        if not initial_cart_date:
            initial_cart_date = safe_date_between(global_start_date, global_end_date)
        
        if not initial_cart_date: continue # Should not happen with safe_date_between

        carts.append({
            "cart_id": generate_cart_id(faker_instance),
            "customer_id": customer['customer_id'],
            "created_at": initial_cart_date.isoformat(),
            "status": "open",
            "cart_total": 0.0
        })

        # Store the latest cart date for this customer
        cust_id = customer['customer_id']
        if cust_id not in customer_last_cart_info or initial_cart_date > customer_last_cart_info[cust_id]['last_date']:
             customer_last_cart_info[cust_id] = {'customer_data': customer, 'last_date': initial_cart_date}

    # --- 2. Simulate Repeat Visits for Customers with Initial Carts ---
    for customer_id, info in customer_last_cart_info.items():
        customer = info['customer_data']
        last_cart_date = info['last_date']
        
        tier = customer.get('loyalty_tier', 'default')
        signup_channel = customer.get('signup_channel')
        signup_date_str = customer.get('signup_date')

        channel_propensities = propensity_config.get(signup_channel, propensity_config.get('default', {}))
        if isinstance(channel_propensities, dict):
            avg_repeat_visits = channel_propensities.get(tier, channel_propensities.get('default', 0.1))
        else:
            avg_repeat_visits = propensity_config.get(tier, propensity_config.get('default', 0.1))

        if signup_date_str:
            cohort_month_key = signup_date_str[:7] # 'YYYY-MM'
            if cohort_month_key in retention_shocks:
                avg_repeat_visits *= retention_shocks[cohort_month_key]
 
        channel_delays = time_delay_config.get(signup_channel, time_delay_config.get('default', {}))
        if isinstance(channel_delays, dict):
            delay_config = channel_delays.get(tier, {'range': default_delay_range, 'sigma': 0.6})
            delay_range = delay_config.get('range', default_delay_range)
            sigma = delay_config.get('sigma', 0.6)
        else:
            delay_range = time_delay_config.get(tier, default_delay_range)
            sigma = 0.6
 
        num_repeat_visits = np.random.poisson(lam=avg_repeat_visits)

        for _ in range(num_repeat_visits):
            mean_delay = (delay_range[0] + delay_range[1]) / 2
            mu = np.log(mean_delay) - (sigma**2 / 2)
            delay = int(np.random.lognormal(mean=mu, sigma=sigma))
            delay = max(delay_range[0], delay) # Ensure delay is at least the minimum
            next_cart_date = last_cart_date + timedelta(days=delay)

            if next_cart_date > global_end_date:
                continue

            carts.append({
                "cart_id": generate_cart_id(faker_instance),
                "customer_id": customer['customer_id'],
                "created_at": next_cart_date.isoformat(),
                "status": "open",
                "cart_total": 0.0
            })
            last_cart_date = next_cart_date

        # --- Simulate Customer Reactivation ---
        while True:
            reactivation_prob = reactivation_settings.get('probability', 0)
            if random.random() < reactivation_prob:
                delay_range = reactivation_settings.get('delay_days_range', [180, 365])
                reactivation_delay = timedelta(days=random.randint(delay_range[0], delay_range[1]))
                reactivation_date = last_cart_date + reactivation_delay
 
                if reactivation_date <= global_end_date:
                    carts.append({
                        "cart_id": generate_cart_id(faker_instance),
                        "customer_id": customer['customer_id'],
                        "created_at": reactivation_date.isoformat(),
                        "status": "open",
                        "cart_total": 0.0,
                        "is_reactivation_cart": True # Add the flag
                    })
                    last_cart_date = reactivation_date # Update for next potential reactivation
                else:
                    break # Stop if reactivation is outside the simulation window
            else:
                break

    if seasonal_factors:
        spiked_carts = []
        for cart in list(carts):
            try:
                cart_month = int(cart['created_at'][5:7])
                multiplier = seasonal_factors.get(str(cart_month), seasonal_factors.get(cart_month, 1.0))

                # For each cart in a spike month, probabilistically add new "clone" carts
                # to approach the desired volume multiplier.
                if multiplier > 1.0:
                    if random.random() < (multiplier - 1): # e.g., 1.6 multiplier gives 60% chance to clone
                        new_cart = cart.copy()
                        new_cart['cart_id'] = generate_cart_id(faker_instance)
                        spiked_carts.append(new_cart)
            except (ValueError, TypeError):
                continue # Skip if date is malformed
        carts.extend(spiked_carts)
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

    # NEW: Create a customer tier lookup for quick access
    customers_by_id = {c['customer_id']: c for c in lookup_cache.get('customers', [])}

    # NEW: Get category preference settings
    category_prefs_by_channel = config.get_parameter('category_preference_by_signup_channel', {})
    all_categories = get_vocab(config, 'categories', [])
    if not all_categories:
        # Fallback if vocab is missing, though this should be caught by a linter.
        all_categories = list(get_vocab(config, 'category_vocab', {}).keys())

    # NEW: Get tier-based cart behavior settings to stratify spending
    cart_behavior_by_tier = config.get_parameter('cart_behavior_by_tier', {})
    default_item_count_range = config.get_table_config("cart_items").get("item_count_range", [1, 8])
    default_quantity_range = [1, 3] # A sensible default

    all_items = []
    cart_updates = {}
    cart_item_id_counter = 1

    for cart in carts:
        customer = customers_by_id.get(cart['customer_id'])
        tier = customer.get('loyalty_tier', 'default') if customer else 'default'
        signup_channel = customer.get('signup_channel', 'default') if customer else 'default'

        # NEW: Determine cart size and item quantity based on tier
        tier_behavior = cart_behavior_by_tier.get(tier, {})
        item_count_range = tier_behavior.get('item_count_range', default_item_count_range)
        quantity_range = tier_behavior.get('quantity_range', default_quantity_range)

        num_items_in_cart = random.randint(item_count_range[0], item_count_range[1])
        cart_total = 0.0
        
        # Get category preferences for this customer's channel
        prefs = category_prefs_by_channel.get(signup_channel, {})
        # Build weights, ensuring all categories have a weight (default to 1.0).
        # The preference keys are lowercase in the config (e.g., 'electronics').
        category_weights = [prefs.get(cat.lower(), 1.0) for cat in all_categories]
        if not any(w > 1.0 for w in category_weights): # If no prefs, use uniform weights
            category_weights = None

        for _ in range(num_items_in_cart):
            # First, select a category based on channel preference
            chosen_category = random.choices(all_categories, weights=category_weights, k=1)[0]
            # Then, select a product from that category
            products_in_category = [p for p in products if p['category'] == chosen_category]
            if not products_in_category:
                product = random.choice(products) # Fallback to any product
            else:
                product = random.choice(products_in_category)

            # Use the tier-specific quantity range
            quantity = random.randint(quantity_range[0], quantity_range[1])
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