#in it!

# === 🔧 Shared Utilities ===

import random
from faker import Faker

def random_date_in_last_n_days(n=30):
    faker = Faker()
    return faker.date_between(start_date=f"-{n}d", end_date="today")

def sample_from_lookup(lookup_cache, table_name, key="id"):
    if table_name in lookup_cache:
        return random.choice(lookup_cache[table_name])
    raise ValueError(f"No data available in lookup cache for table '{table_name}'.")

def generate_product_catalog(n=100, faker=None):
    """Generates a product catalog with fake names and prices."""
    faker = faker or Faker()
    catalog = []
    for i in range(n):
        name = f"{faker.word().capitalize()} {faker.word().capitalize()}"
        catalog.append({
            "product_id": 1000 + i,
            "product_name": name,
            "unit_price": round(random.uniform(5.0, 100.0), 2)
        })
    return catalog