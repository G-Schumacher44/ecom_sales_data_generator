"""generator_common_utils.py

Shared utility functions for story_generators modules.
"""

import random
from typing import Any
from faker import Faker


def assign_agent(order_channel: str, config: Any) -> str:
    """Assigns an agent ID for Phone orders/returns if agent pool enabled; otherwise 'ONLINE'."""
    if order_channel == "Phone":
        agents = get_vocab(config, "agent_pool", {}).get("agents", [])
        if not agents:
            raise ValueError(
                "Agent pool is empty or missing in config but order_channel is 'Phone'."
            )
        return random.choice([agent["id"] for agent in agents])
    return "ONLINE"


def generate_address(faker: Faker) -> str:
    """Generates a fake address string."""
    return faker.address().replace("\n", ", ")


def get_vocab(config, key: str, default=None):
    """Safely get a vocab list from config, falling back to default if missing."""
    if default is None:
        default = []
    return getattr(config, 'vocab', {}).get(key, default)


def get_param(config, key: str, default=None):
    """Safely get a parameter from config, falling back to default if missing."""
    return getattr(config, 'parameters', {}).get(key, default)
