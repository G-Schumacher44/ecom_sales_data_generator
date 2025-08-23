_recurrent_guest_contact_pool = []
"""Module for generating synthetic customer data with configurable attributes.

This module provides functions to generate lists of synthetic customer records with
various attributes such as age, gender, region, loyalty tier, and signup date.
The generation process is highly configurable via a config dictionary, allowing
customization of attribute ranges, options, and probabilities.

Functions:
- generate_customers: Generate a list of synthetic customer records.
- customer_lookup_generator: Retrieve pre-generated customer records from a cache.
"""

import random
from datetime import datetime, timedelta
from .generator_common_utils import get_vocab, get_param, generate_address
from utils.date_utils import safe_date_between

def generate_customers(num_customers=1000, faker=None, config=None, guest_shopper_pct=0.4, global_start_date: datetime.date = None, global_end_date: datetime.date = None):
    """
    Generate a list of synthetic customer records with enriched attributes.

    Args:
        num_customers (int): Number of customers to generate.
        faker (Faker, optional): Faker instance for generating emails, addresses, dates.
        config (dict, optional): Config dict for custom options and probabilities.
        guest_shopper_pct (float, optional): Fraction of customers to generate as guest shoppers.
        global_start_date (datetime.date, optional): Global start date for signup date range.
        global_end_date (datetime.date, optional): Global end date for signup date range.

    Returns:
        List[dict]: List of customer records with enriched data.
    """
    # The 'config' parameter is now the main Config object.
    # Get parameters from the config object for consistency.
    customer_lookup_params = config.lookup_config.get('customers', {})
    min_age = customer_lookup_params.get('min_age', 18)
    max_age = customer_lookup_params.get('max_age', 70)
    signup_years = get_param(config, 'signup_years', 1) # Default to 1 year, which can be overridden by YAML.
    customer_id_start = get_param(config, 'customer_id_start', None)

    # The passed global_end_date is the anchor for all date generation.
    # If not provided, default to today.
    if global_end_date is None:
        global_end_date = datetime.now().date()
    # Customer signups can happen over a longer history than orders.
    signup_start_date = global_end_date - timedelta(days=signup_years * 365)

    # Use get_vocab and get_param for vocab/constants with fallbacks
    genders = get_vocab(config, 'genders', ['Male', 'Female', 'Unknown'])
    loyalty_tiers = get_vocab(config, 'loyalty_tiers', ['Bronze', 'Silver', 'Gold', 'Platinum'])
    signup_channel_options = get_vocab(config, 'signup_channels', ['Website', 'Phone'])
    # NEW: Get signup channel distribution from parameters to model acquisition funnel.
    signup_channel_dist_config = get_param(config, 'signup_channel_distribution')

    clv_map = config.raw_config.get('clv_map', {
        # NEW: Add default mapping for None tier
        None: 'Low',
        'Bronze': 'Low',
        'Silver': 'Medium',
        'Gold': 'High',
        'Platinum': 'High'
    })
    gender_unknown_prob = customer_lookup_params.get('gender_unknown_prob', 0.05)

    # NEW: Parameters for biased loyalty tier assignment
    loyalty_dist_by_channel = get_param(config, 'loyalty_distribution_by_channel', {})
    default_loyalty_dist = loyalty_dist_by_channel.get('default') # Let it be None if not set
    no_tier_probability = get_param(config, 'no_tier_probability', 0.1)

    customer_status_options = get_vocab(config, 'customer_status_options', ["Active", "Inactive", "Dormant"])
    customer_status_probs = get_param(config, 'customer_status_probs', [0.7, 0.2, 0.1])
    email_verified_prob = get_param(config, 'email_verified_prob', 0.8)
    marketing_opt_in_prob = get_param(config, 'marketing_opt_in_prob', 0.5)

    # Determine counts for regular and guest customers
    num_regular_customers = int(num_customers * (1 - guest_shopper_pct))
    num_guest_customers = num_customers - num_regular_customers

    # Starting ID for regular customers
    if customer_id_start is None:
        start_id = random.randint(1000, 9999)
    else:
        start_id = customer_id_start

    if faker is None:
        try:
            from faker import Faker
            faker = Faker()
        except ImportError:
            raise ImportError("Faker is required for date/email/address generation.")

    customers = []

    for i in range(num_regular_customers):
        # Gender with unknown prob
        if random.random() < gender_unknown_prob:
            gender = 'Unknown'
        else:
            gender = random.choice(genders)

        # Basic fields
        customer_id_num = start_id + i
        signup_date_dt = safe_date_between(start_date=signup_start_date, end_date=global_end_date)

        # NEW: Assign signup channel based on configured distribution.
        if signup_channel_dist_config:
            channels = list(signup_channel_dist_config.keys())
            weights = list(signup_channel_dist_config.values())
            signup_channel = random.choices(channels, weights=weights, k=1)[0]
        else: # Fallback to uniform distribution if not configured.
            signup_channel = random.choice(signup_channel_options)

        # NEW: Assign loyalty tier based on channel-specific distribution
        loyalty_tier = None
        if random.random() > no_tier_probability:
            # This customer will be assigned a tier
            channel_dist = loyalty_dist_by_channel.get(signup_channel, default_loyalty_dist)
            if channel_dist and len(channel_dist) == len(loyalty_tiers):
                # Use the configured distribution
                loyalty_tier = random.choices(loyalty_tiers, weights=channel_dist, k=1)[0]
            else:
                # Fallback to random choice if config is missing or invalid
                loyalty_tier = random.choice(loyalty_tiers)

        # Conditional loyalty enrollment date
        if loyalty_tier:
            loyalty_enroll_date = safe_date_between(start_date=signup_date_dt, end_date=global_end_date).isoformat()
        else:
            loyalty_enroll_date = None
        # Per governance, address is required. For baseline, billing matches mailing.
        mailing_address = generate_address(faker)
        billing_address = mailing_address

        # CLV bucket based on loyalty tier (now handles None tier)
        clv_bucket = clv_map.get(loyalty_tier, None)

        first_name = faker.first_name()
        last_name = faker.last_name()

        customer = {
            'customer_id': f"CUST-{customer_id_num:04d}",
            'first_name': first_name,
            'last_name': last_name,
            'email': f"{first_name.lower()}.{last_name.lower()}@{faker.free_email_domain()}",
            'phone_number': faker.phone_number(),
            'age': random.randint(min_age, max_age),
            'gender': gender,
            'loyalty_tier': loyalty_tier,
            'signup_date': signup_date_dt.isoformat(),
            'customer_status': random.choices(customer_status_options, customer_status_probs)[0],
            'email_verified': random.random() < email_verified_prob,
            'marketing_opt_in': random.random() < marketing_opt_in_prob,
            'loyalty_enrollment_date': loyalty_enroll_date,
            'signup_channel': signup_channel,
            'mailing_address': mailing_address,
            'billing_address': billing_address,
            'clv_bucket': clv_bucket,
            'is_guest': False,
        }

        customers.append(customer)

    # Generate guest customers and append
    # Pass the main config object down to the guest generator.
    guest_customers = generate_guest_customers(num_guest_customers, faker=faker, config=config, start_guest_id=100000, global_start_date=global_start_date, global_end_date=global_end_date)
    customers.extend(guest_customers)

    return customers

# The function is extensible: to add more fields, simply add new keys to the config/default_config
# and update the customer dict creation logic.

def customer_lookup_generator(columns, num_rows, faker, lookup_cache):
    """
    Lookup-based generator for customers table to be used by the runner.

    Args:
        columns (list): List of column names requested (not used in this function).
        num_rows (int): Number of rows requested (not used, returns all cached).
        faker (Faker): Faker instance for data generation (not used here).
        lookup_cache (dict): Cache dictionary holding pre-generated lookup data.

    Returns:
        list: List of pre-generated customer records stored in lookup_cache under key "customers".
    """
    return lookup_cache.get("customers", [])


# New function: generate_guest_customers
def generate_guest_customers(num_guest_customers, faker=None, config=None, start_guest_id=100000, global_start_date: datetime.date = None, global_end_date: datetime.date = None):
    """
    Generate fully populated guest customer records with unique guest customer IDs.

    Args:
        num_guest_customers (int): Number of guest customers to generate.
        faker (Faker, optional): Faker instance for data generation.
        config (dict, optional): Config dict for region options, etc.
        start_guest_id (int, optional): Starting number for guest customer IDs to avoid collision.
        global_start_date (datetime.date, optional): Global start date for signup date range.
        global_end_date (datetime.date, optional): Global end date for signup date range.

    Returns:
        list: List of guest customer dicts with full attributes.
    """

    if faker is None:
        try:
            from faker import Faker
            faker = Faker()
        except ImportError:
            raise ImportError("Faker is required for guest customer generation.")

    # The 'config' parameter is now the main Config object.
    # Get parameters directly from the config object.
    guest_contact_pool_size = get_param(config, 'guest_contact_pool_size', 50)
    guest_contact_reuse_prob = get_param(config, 'guest_contact_reuse_prob', 0.2)

    # These vocabs are loaded but not used for guests, but we keep the logic for consistency
    # in case guest generation is enhanced later.
    genders = get_vocab(config, 'genders', ['Male', 'Female', 'Other', 'Prefer not to say'])
    loyalty_tiers = get_vocab(config, 'loyalty_tiers', ['Bronze', 'Silver', 'Gold', 'Platinum'])
    signup_channel_options = get_vocab(config, 'signup_channels', ['Website', 'Phone'])
    clv_map = config.raw_config.get('clv_map', {
        'Bronze': 'Low',
        'Silver': 'Medium',
        'Gold': 'High',
        'Platinum': 'High'
    })

    customer_status = 'Guest'

    guest_customers = []
    # guest_incomplete_data_prob = get_param(merged_config, 'guest_incomplete_data_prob', 0.3)

    global _recurrent_guest_contact_pool
    if len(_recurrent_guest_contact_pool) < guest_contact_pool_size:
        needed = guest_contact_pool_size - len(_recurrent_guest_contact_pool)
        for _ in range(needed):
            _recurrent_guest_contact_pool.append({
                'email': faker.email(),
                'mailing_address': generate_address(faker),
                'billing_address': None
            })
            _recurrent_guest_contact_pool[-1]['billing_address'] = _recurrent_guest_contact_pool[-1]['mailing_address']

    for i in range(num_guest_customers):
        customer_id_num = start_guest_id + i
        customer_id = f"GUEST-{customer_id_num:05d}"

        # Randomly assign age, gender, loyalty, signup_date for guests to have full baseline
        age = None
        gender = None
        loyalty_tier = None
        signup_date_dt = None
        loyalty_enroll_date = None
        signup_channel = None
        clv_bucket = None

        reused_contact_info = None
        if _recurrent_guest_contact_pool and random.random() < guest_contact_reuse_prob:
            reused_contact_info = random.choice(_recurrent_guest_contact_pool)

        if reused_contact_info:
            email = reused_contact_info['email']
            mailing_address = reused_contact_info['mailing_address']
            billing_address = reused_contact_info['billing_address']
        else:
            email = faker.email()
            mailing_address = generate_address(faker)
            billing_address = mailing_address
            new_contact = {
                'email': email,
                'mailing_address': mailing_address,
                'billing_address': billing_address
            }
            _recurrent_guest_contact_pool.append(new_contact)
            if len(_recurrent_guest_contact_pool) > guest_contact_pool_size:
                _recurrent_guest_contact_pool.pop(0)

        email_verified = False
        marketing_opt_in = False

        customer = {
            'customer_id': customer_id,
            'first_name': None,
            'last_name': None,
            'phone_number': None,
            'age': age,
            'gender': gender,
            'loyalty_tier': loyalty_tier,
            'signup_date': signup_date_dt,
            'customer_status': customer_status,
            'email': email,
            'email_verified': email_verified,
            'marketing_opt_in': marketing_opt_in,
            'loyalty_enrollment_date': loyalty_enroll_date,
            'signup_channel': signup_channel,
            'mailing_address': mailing_address,
            'billing_address': billing_address,
            'clv_bucket': clv_bucket,
            'is_guest': True,
        }
        guest_customers.append(customer)

    # Removed block that attempted to call .isoformat() on 'signup_date' for guests,
    # since it is always None for guest customers.

    return guest_customers
