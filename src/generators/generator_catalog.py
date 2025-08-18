"""generator_catalog.py

Contains functions to generate and validate a product catalog for synthetic data generation.

Functions:
- generate_product_catalog: Creates a list of fake product entries using optional category vocabulary and Faker for realistic product names.
- validate_catalog_schema: Validates product catalog entries against expected schema and types, raising errors on mismatch.

This module is part of the story_generators package and supports modular, realistic synthetic data pipelines.
"""
import random
from .generator_common_utils import get_vocab, get_param

def generate_product_catalog(n=100, faker=None, config=None):
    """
    Generate a list of fake products for catalog simulations.
    Returns a list of dicts with standardized schema:
    {
        "product_id": int,
        "product_name": str,
        "category": str,
        "unit_price": float,
        "inventory_quantity": int
    }
    """
    faker = faker or __import__('faker').Faker()
    # Get product-specific parameters from lookup_config for better encapsulation
    product_lookup_params = config.lookup_config.get('product_catalog', {})
    min_price = product_lookup_params.get("min_price", 5.0)
    max_price = product_lookup_params.get("max_price", 500.0)
    min_inventory = product_lookup_params.get("min_inventory_quantity", 0)
    max_inventory = product_lookup_params.get("max_inventory_quantity", 1000)

    # Use category_vocab for generating names, but vocab.categories for the actual category list
    category_vocab = get_vocab(config, "category_vocab", {})
    categories = get_vocab(config, "categories", [])

    catalog = []
    for i in range(1, n + 1):
        category = random.choice(categories) if categories else faker.word().capitalize()
        
        if category_vocab:
            vocab = category_vocab.get(category.lower(), {}) # Use lowercase for name-gen lookup
            adjectives = vocab.get("adjectives", [])
            nouns = vocab.get("nouns", [])
            if adjectives and nouns:
                adj = random.choice(adjectives)
                noun = random.choice(nouns)
                product_name = f"{adj} {noun}"
            else:
                product_name = f"{faker.word().capitalize()} {faker.word()}"
        else:
            product_name = f"{faker.word().capitalize()} {faker.word()}"
        product = {
            "product_id": i,
            "product_name": product_name,
            "category": category,
            "unit_price": round(random.uniform(min_price, max_price), 2),
            "inventory_quantity": random.randint(min_inventory, max_inventory)
        }
        catalog.append(product)
    return catalog


def validate_catalog_schema(catalog):
    """
    Validate that each product in the catalog matches the expected schema.
    Raises ValueError if schema is violated.
    """
    required_fields = {
        "product_id": int,
        "product_name": str,
        "category": str,
        "unit_price": float,
        "inventory_quantity": int
    }
    for idx, product in enumerate(catalog):
        for field, expected_type in required_fields.items():
            if field not in product:
                raise ValueError(f"Missing field '{field}' in product at index {idx}")
            if not isinstance(product[field], expected_type):
                # Allow int for float fields as well (Python quirk)
                if expected_type is float and isinstance(product[field], int):
                    continue
                raise ValueError(
                    f"Field '{field}' in product at index {idx} is not of type {expected_type.__name__}"
                )

def product_catalog_lookup_generator(columns, num_rows, faker, lookup_cache, config=None):
    """
    Lookup-based generator for product_catalog table to be used by the runner.
    Returns the pre-generated product catalog from the lookup_cache.
    The other arguments are for compatibility with the runner's generator signature.
    """
    return lookup_cache.get("product_catalog", [])
