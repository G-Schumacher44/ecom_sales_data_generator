# src/utils/shared_utils.py
import random
import string

def sample_from_lookup(lookup_cache, table_name, key="id"):
    """
    Sample a value from a lookup table stored in a cache.
    """
    if table_name not in lookup_cache or not lookup_cache[table_name]:
        raise ValueError(f"Lookup table '{table_name}' is empty or missing from cache.")
    return random.choice(lookup_cache[table_name])[key]
