"""generator_carts.py

Responsible for generating shopping cart and cart_items data, representing
pre-purchase user sessions.
"""

import random
from typing import List, Dict, Any, Tuple
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
    # `num_rows` determines the number of unique customers who will have an initial session.
    # We sample customers *without replacement* to ensure each customer gets at most one initial cart.
    # This prevents unintended repeaters from being created at this stage.
    num_initial_shoppers = min(num_rows, len(customers))
    initial_shoppers = random.sample(customers, k=num_initial_shoppers)
    
    # Keep track of the last cart date for each customer to chain repeat visits correctly.
    customer_last_cart_info = {}

    for customer in initial_shoppers:
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

        random_time = faker_instance.time_object()
        initial_cart_datetime = datetime.combine(initial_cart_date, random_time)
        carts.append({
            "cart_id": generate_cart_id(faker_instance),
            "customer_id": customer['customer_id'],
            "created_at": initial_cart_datetime.isoformat(),
            "updated_at": initial_cart_datetime.isoformat(), # Initially same as created_at
            "status": "open",
            "cart_total": 0.0
        })

        # Store the latest cart date for this customer
        cust_id = customer['customer_id']
        if cust_id not in customer_last_cart_info or initial_cart_date > customer_last_cart_info[cust_id]['last_date']:
             customer_last_cart_info[cust_id] = {'customer_data': customer, 'last_date': initial_cart_datetime.date()}

    # --- 2. Simulate Repeat Visits for Customers with Initial Carts ---
    for customer_id, info in customer_last_cart_info.items():
        customer = info['customer_data']
        last_cart_date = info['last_date']
        initial_cart_date_anchor = info['last_date'] # Use this for independent event calculations
        
        # Use `or 'default'` to safely handle cases where a key's value is None,
        # which `get()` with a default parameter does not handle.
        tier = customer.get('initial_loyalty_tier') or 'default'
        signup_channel = customer.get('signup_channel') or 'default'
        signup_date_str = customer.get('signup_date')

        # --- Organic Repeat Visits (Poisson Process) ---
        # Get the configured average number of repeat visits (lambda) for the customer's segment.
        # This aligns with the comment in the config and the logic in the QA test.
        channel_propensities = propensity_config.get(signup_channel, propensity_config.get('default', {}))
        avg_repeat_visits_lambda = channel_propensities.get(tier, channel_propensities.get('default', 0.1))

        # Apply cohort-based retention shocks, which directly modify the visit propensity (lambda).
        if signup_date_str:
            cohort_month_key = signup_date_str[:7] # 'YYYY-MM'
            if cohort_month_key in retention_shocks:
                avg_repeat_visits_lambda *= retention_shocks[cohort_month_key]

        # Get time delay settings for this segment.
        channel_delays = time_delay_config.get(signup_channel, time_delay_config.get('default', {}))
        delay_config = channel_delays.get(tier, channel_delays.get('default', {}))
        delay_range = delay_config.get('range', default_delay_range)
        sigma = delay_config.get('sigma', 0.6)
 
        # Generate the number of organic repeat visits from the Poisson distribution.
        num_repeat_visits = np.random.poisson(lam=avg_repeat_visits_lambda)

        for i in range(num_repeat_visits):
            mean_delay = (delay_range[0] + delay_range[1]) / 2
            mu = np.log(mean_delay) - (sigma**2 / 2)
            delay = int(np.random.lognormal(mean=mu, sigma=sigma))
            delay = max(delay_range[0], delay) # Ensure delay is at least the minimum
            next_cart_date = last_cart_date + timedelta(days=delay)

            if next_cart_date > global_end_date:
                # BUG FIX: The original 'continue' would truncate visits that should occur,
                # causing the actual repeat rate to be lower than the configured propensity.
                # This was especially true for customers who signed up later in the year.
                # To fix this, if a visit would fall out of bounds, we instead place it
                # within the remaining time window to ensure the Poisson-generated number
                # of visits is respected.
                time_left_days = (global_end_date - last_cart_date).days
                if time_left_days > 0:
                    next_cart_date = last_cart_date + timedelta(days=random.randint(1, time_left_days))
                else:
                    # No time left, so we can't place this or any subsequent visits.
                    break

            random_time = faker_instance.time_object()
            next_cart_datetime = datetime.combine(next_cart_date, random_time)
            carts.append({
                "cart_id": generate_cart_id(faker_instance),
                "customer_id": customer['customer_id'],
                "created_at": next_cart_datetime.isoformat(),
                "updated_at": next_cart_datetime.isoformat(),
                "status": "open",
                "cart_total": 0.0
            })
            last_cart_date = next_cart_datetime.date()

        # --- Independent Reactivation Process ---
        # This is a separate Bernoulli trial, independent of the organic repeat visits.
        reactivation_prob = reactivation_settings.get('probability', 0)
        if random.random() < reactivation_prob:
            delay_range = reactivation_settings.get('delay_days_range', [180, 365])
            reactivation_delay = timedelta(days=random.randint(delay_range[0], delay_range[1]))
            reactivation_date = initial_cart_date_anchor + reactivation_delay

            if reactivation_date <= global_end_date:
                random_time = faker_instance.time_object()
                reactivation_datetime = datetime.combine(reactivation_date, random_time)
                carts.append({
                    "cart_id": generate_cart_id(faker_instance),
                    "customer_id": customer['customer_id'],
                    "created_at": reactivation_datetime.isoformat(),
                    "updated_at": reactivation_datetime.isoformat(),
                    "status": "open",
                    "cart_total": 0.0,
                    "is_reactivation_cart": True
                })

    # --- 3. Apply Seasonal Spikes ---
    # This logic increases cart volume in certain months.
    # BUG FIX: The previous logic applied to all carts, which could turn a single-cart
    # customer into a repeat customer, artificially inflating the repeat rate and
    # breaking the propensity QA test.
    # The corrected logic only applies seasonal spikes to customers who are ALREADY
    # repeat shoppers, modeling seasonality as an increase in frequency for engaged
    # customers, not the creation of new ones.
    if seasonal_factors:
        # Create a pristine copy of the carts generated by the propensity models
        # before any seasonal modifications are made.
        base_carts = list(carts)

        # Identify repeaters from the BASE carts, before any seasonal additions.
        # This is the critical step to prevent creating "artificial" repeaters.
        carts_per_customer = defaultdict(int)
        for cart in base_carts:
            carts_per_customer[cart['customer_id']] += 1
        
        repeater_customer_ids = {
            cid for cid, count in carts_per_customer.items() if count > 1
        }

        additional_carts = []
        # Iterate over the BASE carts to decide where to add seasonal spikes.
        # This prevents a cart added by seasonality from itself generating more carts.
        for cart in base_carts:
            # Only apply seasonal spikes to carts belonging to existing repeaters.
            if cart['customer_id'] not in repeater_customer_ids:
                continue

            try:
                cart_dt = datetime.fromisoformat(cart['created_at'])
                cart_month = cart_dt.month
            except (ValueError, TypeError):
                continue

            multiplier = seasonal_factors.get(str(cart_month), seasonal_factors.get(cart_month, 1.0))

            # For each existing cart, the multiplier determines the chance of adding more carts.
            # A multiplier of 1.6 means a 60% chance of adding one extra cart,
            # and a smaller chance of adding more. We model this by treating the
            # fractional part of the multiplier as a probability.
            if multiplier > 1.0:
                # The number of extra carts to consider adding is the integer part of the multiplier - 1
                num_extra_carts_base = int(multiplier - 1)
                # The fractional part is the probability of adding one more
                prob_extra_cart_rand = multiplier - (num_extra_carts_base + 1)

                num_to_add = num_extra_carts_base
                if random.random() < prob_extra_cart_rand:
                    num_to_add += 1

                for _ in range(num_to_add):
                    # Create a new cart for the SAME customer
                    new_cart = cart.copy()
                    new_cart['customer_id'] = cart['customer_id'] # Explicitly ensure it's the same customer
                    new_cart['cart_id'] = generate_cart_id(faker_instance)

                    # Add a small random offset to the date to avoid exact duplicates
                    # and keep it within the same month.
                    offset = timedelta(days=random.uniform(0, 3), hours=random.uniform(-12, 12))
                    new_cart_dt = cart_dt + offset

                    # Ensure the new date is still in the same month and within bounds
                    if new_cart_dt.month == cart_month and new_cart_dt.date() <= global_end_date:
                        new_cart['created_at'] = new_cart_dt.isoformat()
                        new_cart['updated_at'] = new_cart_dt.isoformat() # Reset updated_at
                        new_cart.pop("is_reactivation_cart", None)
                        additional_carts.append(new_cart)
        carts.extend(additional_carts)
    return carts

def generate_cart_items(columns: List[str], num_rows: int, faker_instance: Faker, lookup_cache: Dict, config: Any) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """
    Generates items for each shopping cart.
    """
    carts = lookup_cache.get("shopping_carts")
    if not carts:
        raise ValueError("Shopping carts must be generated before cart items.")

    products = lookup_cache.get("product_catalog")
    if not products:
        raise ValueError("Product catalog must be present in lookup_cache.")

    global_end_date = lookup_cache.get("global_end_date")
    if not global_end_date:
        # This is a critical piece of information for ensuring data consistency.
        raise ValueError("global_end_date not found in lookup_cache. It should be set in the main run script.")

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
        tier = customer.get('initial_loyalty_tier', 'default') if customer else 'default'
        signup_channel = customer.get('signup_channel', 'default') if customer else 'default'

        # Get created_at as a datetime object for direct use and comparison
        created_at_dt = datetime.fromisoformat(cart["created_at"])

        # NEW: Determine cart size and item quantity based on tier
        tier_behavior = cart_behavior_by_tier.get(tier, {})
        item_count_range = tier_behavior.get('item_count_range', default_item_count_range)
        quantity_range = tier_behavior.get('quantity_range', default_quantity_range)

        num_items_in_cart = random.randint(item_count_range[0], item_count_range[1])
        cart_total = 0.0
        last_item_added_at = created_at_dt
        
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

            # Item is added some time after the cart was created or the last item was added
            item_added_at = last_item_added_at + timedelta(seconds=random.randint(1, 300))
            if item_added_at.date() > global_end_date: # Ensure it doesn't go past the simulation end date
                item_added_at = datetime.combine(global_end_date, datetime.max.time())

            item = {
                "cart_item_id": cart_item_id_counter,
                "cart_id": cart["cart_id"],
                "product_id": product["product_id"],
                "product_name": product["product_name"],
                "category": product["category"],
                "added_at": item_added_at.isoformat(),
                "quantity": quantity,
                "unit_price": product["unit_price"],
            }
            all_items.append(item)
            cart_total += item_total
            cart_item_id_counter += 1
            last_item_added_at = item_added_at
        
        # Defensive check: Ensure updated_at is never before created_at.
        # This handles any edge cases where the item addition loop might not run
        # or if a negative timedelta was somehow introduced.
        if last_item_added_at < created_at_dt:
            last_item_added_at = created_at_dt

        cart_updates[cart["cart_id"]] = {
            "cart_total": round(cart_total, 2),
            "updated_at": last_item_added_at.isoformat()
        }

    return all_items, cart_updates