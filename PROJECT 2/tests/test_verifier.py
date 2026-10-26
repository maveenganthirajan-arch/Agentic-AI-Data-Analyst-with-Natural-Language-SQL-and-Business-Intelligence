"""
Tests for Numerical Verifier.
"""

import pytest
from agent.verifier import verifier

def test_verify_category_quarterly_change():
    # In our seeded DB, Electronics dropped from 250001.00 in 2025-Q3 to 96677.00 in 2025-Q4 (delta: -153324.00)
    result = verifier.verify_category_quarterly_change(
        category="Electronics",
        q_start="2025-Q3",
        q_end="2025-Q4",
        claimed_start_rev=250001.00,
        claimed_end_rev=96677.00,
        claimed_delta=-153324.00
    )

    assert result["status"] == "VERIFIED"
    assert result["db_truth"]["actual_delta"] == -153324.00

def test_verify_discrepancy_detection():
    # Intentionally false claim
    result = verifier.verify_category_quarterly_change(
        category="Electronics",
        q_start="2025-Q3",
        q_end="2025-Q4",
        claimed_start_rev=999999.00 # False
    )

    assert result["status"] == "DISCREPANCY"

def test_verify_sum():
    res = verifier.verify_sum(
        table="order_items",
        column="quantity",
        claimed_value=5000,
        tolerance=5000 # test connectivity and return structure
    )
    assert res["status"] in ("VERIFIED", "DISCREPANCY")
    assert "verification_sql" in res
