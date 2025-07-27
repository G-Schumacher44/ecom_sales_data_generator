"""
Module for loading and accessing configuration from a YAML file for SQL story generation.
"""

import yaml
from pathlib import Path
import os

class Config:
    def __init__(self, yaml_path=None):
        # Default path to YAML config
        default_path = Path(__file__).parent.parent.parent / 'config' / 'ecom_sales_gen_template.yaml'
        self.yaml_path = Path(
            yaml_path
            or os.getenv("CONFIG", str(default_path))
        )
        self._load_yaml()

    def _load_yaml(self):
        with open(self.yaml_path, 'r') as f:
            self.raw_config = yaml.safe_load(f)
        # Parse main sections
        self.row_generators = self.raw_config.get('row_generators', {})
        self.tables = self.raw_config.get('tables', [])
        self.faker_seed = self.raw_config.get('faker_seed', None)
        self.category_vocab = self.raw_config.get('category_vocab', {})
        self.lookup_config = self.raw_config.get('lookup_config', {})
        self.date_settings = self.raw_config.get('date_settings', {})
        self.agent_pool = self.raw_config.get('agent_pool', {'enabled': False, 'agents': []})
        self.customer_enrichment = self.raw_config.get('customer_enrichment', {})
        self.channel_rules = self.raw_config.get('channel_rules', {})
        self.config = self.raw_config

    # Example getter for table by name
    def get_table_config(self, table_name):
        for table in self.tables:
            if table.get('name') == table_name:
                return table
        return None

    # Example to get generation count for a table
    def get_generation_count(self, table_name):
        table = self.get_table_config(table_name)
        if table:
            return table.get('generate', None)
        return None

    @property
    def agents(self):
        return self.agent_pool.get('agents', []) if self.agent_pool.get('enabled', False) else []

    def get_agent_ids(self):
        return [agent.get('id') for agent in self.agents if 'id' in agent]

    @property
    def customer_enrichment_config(self):
        return self.customer_enrichment

    @property
    def guest_order_ratio(self):
        return self.raw_config.get('guest_order_ratio', 0.1)

    @property
    def guest_order_channel(self):
        return self.raw_config.get('guest_order_channel', 'Online')

    @property
    def vocab(self):
        return self.raw_config.get('vocab', {})

    @property
    def parameters(self):
        return self.raw_config.get('parameters', {})

    def get_vocab_list(self, key, default=None):
        return self.vocab.get(key, default or [])

    def get_parameter(self, key, default=None):
        return self.parameters.get(key, default)

    @property
    def regions(self):
        return self.get_vocab_list('regions', ["North", "South", "East", "West", "Central"])

    @property
    def payment_methods(self):
        return self.get_vocab_list('payment_methods', ["Credit Card", "PayPal", "Apple Pay"])

    @property
    def expedited_pct(self):
        return self.get_parameter('expedited_pct', 20)


if __name__ == '__main__':
    # Quick test print
    config = Config()
    print('Row Generators:', config.row_generators)
    print('Tables:', [t['name'] for t in config.tables])
    print('Faker Seed:', config.faker_seed)
    print('Date Settings:', config.date_settings)
