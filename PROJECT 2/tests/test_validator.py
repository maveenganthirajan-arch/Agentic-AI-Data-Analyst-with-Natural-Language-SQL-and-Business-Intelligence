"""
Tests for SQL Read-Only Security Validator.
"""

import pytest
from agent.validator import validate_sql

def test_valid_select_query():
    query = "SELECT category, SUM(total_revenue) FROM order_items GROUP BY category"
    res = validate_sql(query)
    assert res["is_valid"] is True
    assert res["error"] is None

def test_valid_join_query():
    query = """
    SELECT p.name, SUM(oi.quantity) as total_qty
    FROM products p
    JOIN order_items oi ON p.id = oi.product_id
    GROUP BY p.name
    ORDER BY total_qty DESC
    LIMIT 10
    """
    res = validate_sql(query)
    assert res["is_valid"] is True

def test_block_drop_table():
    res = validate_sql("DROP TABLE customers")
    assert res["is_valid"] is False
    assert "Forbidden keyword" in res["error"] or "Disallowed statement type" in res["error"]

def test_block_delete():
    res = validate_sql("DELETE FROM orders WHERE id = 1")
    assert res["is_valid"] is False

def test_block_update():
    res = validate_sql("UPDATE products SET unit_price = 0")
    assert res["is_valid"] is False

def test_block_stacked_injection():
    res = validate_sql("SELECT * FROM products; DROP TABLE customers;")
    assert res["is_valid"] is False
    assert "stacked" in res["error"].lower() or "forbidden" in res["error"].lower()

def test_block_sqlite_attach():
    res = validate_sql("ATTACH DATABASE 'malicious.db' AS mal")
    assert res["is_valid"] is False

def test_block_unauthorized_table():
    res = validate_sql("SELECT * FROM sqlite_master")
    assert res["is_valid"] is False
    assert "Unauthorized table access" in res["error"] or "sqlite_master" in res["error"]
