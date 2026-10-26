"""
Tests for Database Schema, Seeding, and Relational Integrity.
"""

import pytest
from sqlalchemy import text
from database.schema import get_engine, Customer, Product, Order, OrderItem, Return, MarketingSpend

def test_database_tables_exist():
    engine = get_engine()
    with engine.connect() as conn:
        tables = [row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()]
    
    expected = ["customers", "products", "orders", "order_items", "returns", "marketing_spend"]
    for t in expected:
        assert t in tables, f"Expected table '{t}' was not found in database."

def test_database_records_counts():
    engine = get_engine()
    with engine.connect() as conn:
        c_count = conn.execute(text("SELECT COUNT(*) FROM customers")).scalar()
        p_count = conn.execute(text("SELECT COUNT(*) FROM products")).scalar()
        o_count = conn.execute(text("SELECT COUNT(*) FROM orders")).scalar()
        oi_count = conn.execute(text("SELECT COUNT(*) FROM order_items")).scalar()
        r_count = conn.execute(text("SELECT COUNT(*) FROM returns")).scalar()
        m_count = conn.execute(text("SELECT COUNT(*) FROM marketing_spend")).scalar()

    assert c_count >= 100
    assert p_count >= 20
    assert o_count >= 1000
    assert oi_count >= o_count
    assert r_count > 0
    assert m_count > 0

def test_foreign_key_integrity():
    engine = get_engine()
    with engine.connect() as conn:
        # Check all order items point to valid products
        orphan_items = conn.execute(text("""
            SELECT COUNT(*) FROM order_items oi
            LEFT JOIN products p ON oi.product_id = p.id
            WHERE p.id IS NULL
        """)).scalar()
        assert orphan_items == 0

        # Check all orders point to valid customers
        orphan_orders = conn.execute(text("""
            SELECT COUNT(*) FROM orders o
            LEFT JOIN customers c ON o.customer_id = c.id
            WHERE c.id IS NULL
        """)).scalar()
        assert orphan_orders == 0
