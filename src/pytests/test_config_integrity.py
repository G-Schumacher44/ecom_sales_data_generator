

import pytest
import yaml
from pathlib import Path
import importlib
from utils.config import Config

def test_yaml_loads_without_error():
    path = Path("config/ecom_sales_gen_template.yaml")
    with open(path) as f:
        config = yaml.safe_load(f)
    assert isinstance(config, dict)

def test_generator_paths_are_importable():
    cfg = Config("config/ecom_sales_gen_template.yaml")
    for name, path in cfg.row_generators.items():
        module_path, fn_name = path.rsplit(".", 1)
        mod = importlib.import_module(module_path)
        assert hasattr(mod, fn_name), f"{fn_name} missing in {module_path}"

def test_customer_status_probs_sum_to_1():
    cfg = Config("config/ecom_sales_gen_template.yaml")
    customers = next(t for t in cfg.tables if t["name"] == "customers")
    status_col = next(c for c in customers["columns"] if c["name"] == "customer_status")
    total = sum(status_col.get("probabilities", []))
    assert round(total, 5) == 1.0

def test_return_reason_weights_sum_to_1():
    cfg = Config("config/ecom_sales_gen_template.yaml")
    rr_weights = cfg.parameters["baseline_return_reason_weights"]
    for category, reasons in rr_weights.items():
        total = sum(reasons.values())
        assert round(total, 5) == 1.0, f"{category} total={total}"


def test_order_channel_distribution_sums_to_1():
    cfg = Config("config/ecom_sales_gen_template.yaml")
    dist = cfg.parameters["order_channel_distribution"]
    assert round(sum(dist.values()), 5) == 1.0


def test_all_tables_have_columns():
    cfg = Config("config/ecom_sales_gen_template.yaml")
    for table in cfg.tables:
        assert "columns" in table or "link_to_orders" in table, f"{table['name']} is missing 'columns'"


def test_row_generators_are_callable():
    cfg = Config("config/ecom_sales_gen_template.yaml")
    for key, path in cfg.row_generators.items():
        mod_path, func_name = path.rsplit(".", 1)
        mod = importlib.import_module(mod_path)
        func = getattr(mod, func_name, None)
        assert callable(func), f"{path} is not callable"


def test_loyalty_tier_vocab_matches_column():
    cfg = Config("config/ecom_sales_gen_template.yaml")
    vocab_tiers = set(cfg.vocab["loyalty_tiers"])
    customer_table = next(t for t in cfg.tables if t["name"] == "customers")
    column = next(c for c in customer_table["columns"] if c["name"] == "loyalty_tier")
    if "options" in column:
        column_tiers = set(column["options"])
        assert column_tiers == vocab_tiers, f"Mismatch: {column_tiers ^ vocab_tiers}"