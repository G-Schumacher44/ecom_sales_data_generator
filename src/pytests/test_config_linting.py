from utils.config import Config
import pytest

def test_table_names_are_unique():
    cfg = Config("config/ecom_sales_gen_template.yaml")
    table_names = [t["name"] for t in cfg.tables]
    assert len(table_names) == len(set(table_names)), "Duplicate table names found"

def test_columns_exist_and_have_types():
    cfg = Config("config/ecom_sales_gen_template.yaml")
    for table in cfg.tables:
        if "columns" in table:
            assert isinstance(table["columns"], list) and len(table["columns"]) > 0, f"{table['name']} has no columns"
            for col in table["columns"]:
                assert "name" in col, f"{table['name']} has column without a name"
                assert "type" in col, f"{table['name']}:{col.get('name')} is missing type"

def test_no_duplicate_column_names():
    cfg = Config("config/ecom_sales_gen_template.yaml")
    for table in cfg.tables:
        if "columns" in table:
            names = [c["name"] for c in table["columns"]]
            duplicates = set(n for n in names if names.count(n) > 1)
            assert not duplicates, f"{table['name']} has duplicate columns: {duplicates}"
