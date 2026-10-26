"""
Numerical Verifier: Audits and cross-checks Python/Agent calculations
against raw database ground truth aggregations to eliminate hallucinations.
"""

from typing import Dict, Any, List, Optional
import math
import pandas as pd
from sqlalchemy import text
from database.schema import get_engine

class NumericalVerifier:
    """
    Independently verifies analytical calculations against direct database aggregations.
    """

    def __init__(self, engine=None):
        self.engine = engine or get_engine()

    def verify_sum(
        self,
        table: str,
        column: str,
        claimed_value: float,
        where_clause: str = "1=1",
        tolerance: float = 0.50
    ) -> Dict[str, Any]:
        """
        Runs an independent SELECT SUM(column) FROM table WHERE ...
        and compares with claimed_value.
        """
        sql = f"SELECT COALESCE(SUM({column}), 0.0) as total FROM {table} WHERE {where_clause}"
        with self.engine.connect() as conn:
            result = conn.execute(text(sql)).fetchone()
            db_total = float(result[0]) if result else 0.0

        delta = abs(claimed_value - db_total)
        is_match = delta <= tolerance

        return {
            "metric": f"SUM({table}.{column})",
            "where_clause": where_clause,
            "claimed_value": round(claimed_value, 2),
            "db_ground_truth": round(db_total, 2),
            "difference": round(delta, 2),
            "status": "VERIFIED" if is_match else "DISCREPANCY",
            "verification_sql": sql
        }

    def verify_count(
        self,
        table: str,
        claimed_count: int,
        where_clause: str = "1=1"
    ) -> Dict[str, Any]:
        """
        Runs an independent SELECT COUNT(*) FROM table WHERE ...
        """
        sql = f"SELECT COUNT(*) as cnt FROM {table} WHERE {where_clause}"
        with self.engine.connect() as conn:
            result = conn.execute(text(sql)).fetchone()
            db_count = int(result[0]) if result else 0

        is_match = (claimed_count == db_count)

        return {
            "metric": f"COUNT({table})",
            "where_clause": where_clause,
            "claimed_value": claimed_count,
            "db_ground_truth": db_count,
            "difference": abs(claimed_count - db_count),
            "status": "VERIFIED" if is_match else "DISCREPANCY",
            "verification_sql": sql
        }

    def verify_category_quarterly_change(
        self,
        category: str,
        q_start: str,  # e.g. "2025-Q3"
        q_end: str,    # e.g. "2025-Q4"
        claimed_start_rev: Optional[float] = None,
        claimed_end_rev: Optional[float] = None,
        claimed_delta: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Cross-checks quarterly category revenue and change directly from raw order_items and orders.
        """
        sql = """
        SELECT 
            strftime('%Y-Q', o.order_date) || ((strftime('%m', o.order_date) - 1) / 3 + 1) AS quarter,
            SUM(oi.total_revenue) as revenue
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.id
        JOIN products p ON oi.product_id = p.id
        WHERE p.category = :category
        GROUP BY quarter
        HAVING quarter IN (:q_start, :q_end)
        """
        with self.engine.connect() as conn:
            df = pd.read_sql(text(sql), conn, params={"category": category, "q_start": q_start, "q_end": q_end})

        rev_map = dict(zip(df["quarter"], df["revenue"]))
        true_start = float(rev_map.get(q_start, 0.0))
        true_end = float(rev_map.get(q_end, 0.0))
        true_delta = true_end - true_start

        checks = []
        all_passed = True

        if claimed_start_rev is not None:
            match = abs(claimed_start_rev - true_start) < 1.0
            all_passed = all_passed and match
            checks.append({
                "metric": f"{category} {q_start} Revenue",
                "claimed": claimed_start_rev,
                "truth": true_start,
                "passed": match
            })

        if claimed_end_rev is not None:
            match = abs(claimed_end_rev - true_end) < 1.0
            all_passed = all_passed and match
            checks.append({
                "metric": f"{category} {q_end} Revenue",
                "claimed": claimed_end_rev,
                "truth": true_end,
                "passed": match
            })

        if claimed_delta is not None:
            match = abs(claimed_delta - true_delta) < 1.0
            all_passed = all_passed and match
            checks.append({
                "metric": f"{category} Delta ({q_end} - {q_start})",
                "claimed": claimed_delta,
                "truth": true_delta,
                "passed": match
            })

        return {
            "category": category,
            "period": f"{q_start} to {q_end}",
            "db_truth": {
                f"{q_start}_revenue": round(true_start, 2),
                f"{q_end}_revenue": round(true_end, 2),
                "actual_delta": round(true_delta, 2)
            },
            "status": "VERIFIED" if all_passed else "DISCREPANCY",
            "checks": checks
        }

    def verify_dataframe_aggregates(
        self,
        df: pd.DataFrame,
        value_column: str,
        group_column: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Quick integrity check on computed DataFrame totals.
        """
        if df.empty or value_column not in df.columns:
            return {"status": "EMPTY", "details": "DataFrame empty or column missing"}

        computed_sum = float(df[value_column].sum())
        row_count = len(df)

        return {
            "status": "AUDITED",
            "row_count": row_count,
            "total_computed": round(computed_sum, 2),
            "min_val": round(float(df[value_column].min()), 2),
            "max_val": round(float(df[value_column].max()), 2),
            "mean_val": round(float(df[value_column].mean()), 2)
        }


# Singleton instance
verifier = NumericalVerifier()
