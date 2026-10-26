"""
Analytical Tools for Agentic Data Analyst:
- SQL query execution with security validation
- Python data transformation and statistical calculations
- Interactive Plotly chart generation
- Scikit-Learn RFM Customer Segmentation
"""

import json
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from database.schema import get_engine
from agent.validator import validate_sql
from agent.verifier import verifier

class DataAnalystTools:
    """
    Core analytical toolset invoked by the LangGraph agent.
    """

    def __init__(self, engine=None):
        self.engine = engine or get_engine()

    def execute_sql(self, query: str) -> Dict[str, Any]:
        """
        Validates read-only permissions and executes SQL query against the sales database.
        Returns tabular records, column metadata, and summary stats.
        """
        # 1. Security validation
        val_res = validate_sql(query)
        if not val_res["is_valid"]:
            return {
                "success": False,
                "error": f"Security Validation Failed: {val_res['error']}",
                "records": [],
                "row_count": 0,
                "columns": []
            }

        sanitized_query = val_res["sanitized_query"]

        # 2. Execution
        try:
            with self.engine.connect() as conn:
                df = pd.read_sql(sanitized_query, conn)

            # Handle datetime serialization
            for col in df.select_dtypes(include=["datetime64[ns]", "datetime64"]).columns:
                df[col] = df[col].astype(str)

            # Round numeric columns for clean presentation
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            df[numeric_cols] = df[numeric_cols].round(2)

            records = df.to_dict(orient="records")
            columns = list(df.columns)

            return {
                "success": True,
                "query": sanitized_query,
                "columns": columns,
                "row_count": len(df),
                "records": records,
                "data_preview": records[:10],
                "tables_accessed": val_res["tables_accessed"]
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Database Execution Error: {str(e)}",
                "records": [],
                "row_count": 0,
                "columns": []
            }

    def execute_python_calc(
        self,
        records: List[Dict[str, Any]],
        calculation_type: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Performs in-memory data manipulations, percentage changes, delta rankings,
        and statistical summaries using Pandas.
        """
        if not records:
            return {"success": False, "error": "No records provided for calculation."}

        df = pd.DataFrame(records)

        try:
            if calculation_type == "quarterly_decline_analysis":
                # Special analysis for quarterly category changes
                # Expected columns: quarter, category, revenue
                q_col = kwargs.get("quarter_col", "quarter")
                cat_col = kwargs.get("category_col", "category")
                val_col = kwargs.get("value_col", "revenue")

                piv = df.pivot(index=cat_col, columns=q_col, values=val_col).fillna(0)
                quarters = sorted(list(piv.columns))
                if len(quarters) < 2:
                    return {"success": False, "error": "Need at least two quarters to compute decline."}

                q_prev, q_last = quarters[-2], quarters[-1]
                piv["delta"] = piv[q_last] - piv[q_prev]
                piv["pct_change"] = ((piv["delta"] / piv[q_prev].replace(0, np.nan)) * 100).round(2)

                total_prev = float(piv[q_prev].sum())
                total_last = float(piv[q_last].sum())
                total_delta = total_last - total_prev
                total_pct = round(((total_delta / total_prev) * 100), 2) if total_prev > 0 else 0.0

                # Compute contribution to total decline (for negative categories)
                declining = piv[piv["delta"] < 0].copy()
                top_declining_cat = None
                max_decline_amt = 0.0

                if not declining.empty:
                    # The category with the most negative delta
                    top_declining_cat = declining["delta"].idxmin()
                    max_decline_amt = float(declining.loc[top_declining_cat, "delta"])

                breakdown = []
                for cat, row in piv.iterrows():
                    c_delta = float(row["delta"])
                    c_prev = float(row[q_prev])
                    c_last = float(row[q_last])
                    # If overall delta was negative, how much of that negative drop is explained by this category
                    contrib = round((c_delta / total_delta) * 100, 2) if total_delta < 0 and c_delta < 0 else 0.0
                    breakdown.append({
                        "category": cat,
                        f"{q_prev}_revenue": round(c_prev, 2),
                        f"{q_last}_revenue": round(c_last, 2),
                        "delta": round(c_delta, 2),
                        "pct_change": float(row["pct_change"]),
                        "contribution_to_net_change_pct": contrib
                    })

                breakdown = sorted(breakdown, key=lambda x: x["delta"])

                return {
                    "success": True,
                    "calculation_type": calculation_type,
                    "quarters_compared": [q_prev, q_last],
                    "total_previous_revenue": round(total_prev, 2),
                    "total_last_revenue": round(total_last, 2),
                    "net_revenue_change": round(total_delta, 2),
                    "net_pct_change": total_pct,
                    "top_declining_category": top_declining_cat,
                    "top_decline_amount": round(max_decline_amt, 2),
                    "category_breakdown": breakdown
                }

            elif calculation_type == "aggregate_summary":
                val_col = kwargs.get("value_col", df.columns[-1])
                group_col = kwargs.get("group_col", df.columns[0])

                grouped = df.groupby(group_col)[val_col].agg(["sum", "mean", "count"]).reset_index()
                grouped = grouped.sort_values(by="sum", ascending=False)
                grouped.columns = [group_col, "total_sum", "average", "count"]

                return {
                    "success": True,
                    "calculation_type": calculation_type,
                    "results": grouped.round(2).to_dict(orient="records")
                }

            elif calculation_type == "growth_rate":
                val_col = kwargs.get("value_col", df.columns[-1])
                df["growth_rate"] = df[val_col].pct_change() * 100
                return {
                    "success": True,
                    "calculation_type": calculation_type,
                    "results": df.round(2).to_dict(orient="records")
                }

            else:
                # Default generic descriptive statistics
                numeric_df = df.select_dtypes(include=[np.number])
                stats = numeric_df.describe().round(2).to_dict()
                return {
                    "success": True,
                    "calculation_type": "descriptive_stats",
                    "stats": stats
                }

        except Exception as e:
            return {"success": False, "error": f"Python Calculation Error: {str(e)}"}

    def generate_plotly_chart(
        self,
        chart_type: str,
        data: List[Dict[str, Any]],
        x: str,
        y: str,
        title: str,
        color: Optional[str] = None,
        barmode: str = "group"
    ) -> Dict[str, Any]:
        """
        Creates publication-grade interactive Plotly charts adhering to the UI design system.
        """
        if not data:
            return {"success": False, "error": "No data available for chart generation."}

        df = pd.DataFrame(data)
        if x not in df.columns or y not in df.columns:
            return {"success": False, "error": f"Columns '{x}' or '{y}' not found in data."}

        # Enterprise color palette matching the UI
        color_palette = ["#2563EB", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#06B6D4", "#EC4899"]

        try:
            fig = None
            if chart_type == "bar":
                fig = px.bar(
                    df,
                    x=x,
                    y=y,
                    color=color if color in df.columns else None,
                    barmode=barmode,
                    title=title,
                    color_discrete_sequence=color_palette,
                    text_auto=".2s"
                )
            elif chart_type == "line":
                fig = px.line(
                    df,
                    x=x,
                    y=y,
                    color=color if color in df.columns else None,
                    markers=True,
                    title=title,
                    color_discrete_sequence=color_palette
                )
                fig.update_traces(line_shape="spline", line_width=3)
            elif chart_type == "pie":
                fig = px.pie(
                    df,
                    names=x,
                    values=y,
                    title=title,
                    color_discrete_sequence=color_palette,
                    hole=0.45
                )
            elif chart_type == "waterfall":
                # Create waterfall breakdown
                measure = ["relative"] * len(df)
                fig = go.Figure(go.Waterfall(
                    name="Contribution",
                    orientation="v",
                    measure=measure,
                    x=df[x],
                    y=df[y],
                    connector={"line": {"color": "#94A3B8"}},
                    decreasing={"marker": {"color": "#EF4444"}},
                    increasing={"marker": {"color": "#10B981"}},
                ))
                fig.update_layout(title=title)
            else:
                fig = px.bar(df, x=x, y=y, title=title, color_discrete_sequence=color_palette)

            # Modern clean layout styling
            fig.update_layout(
                template="plotly_white",
                title={"text": title, "font": {"size": 16, "family": "Inter, sans-serif"}},
                xaxis_title=x.replace("_", " ").title(),
                yaxis_title=y.replace("_", " ").title(),
                margin=dict(l=40, r=40, t=50, b=40),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                hoverlabel=dict(bgcolor="white", font_size=12, font_family="Inter, sans-serif")
            )

            fig_json = fig.to_json()
            fig_dict = json.loads(fig_json)

            return {
                "success": True,
                "chart_type": chart_type,
                "title": title,
                "figure_dict": fig_dict,
                "figure_json": fig_json
            }

        except Exception as e:
            return {"success": False, "error": f"Plotly Generation Error: {str(e)}"}

    def run_customer_segmentation(self, n_clusters: int = 4) -> Dict[str, Any]:
        """
        Executes scikit-learn RFM (Recency, Frequency, Monetary) clustering on customers.
        Computes Recency (days since last order), Frequency (order count), and Monetary (total spend).
        """
        sql = """
        SELECT 
            c.id as customer_id,
            c.name as customer_name,
            c.segment as declared_segment,
            c.region,
            COUNT(o.id) as frequency,
            COALESCE(SUM(o.total_amount), 0.0) as monetary,
            ROUND(JULIANDAY('2026-01-01') - JULIANDAY(MAX(o.order_date))) as recency
        FROM customers c
        JOIN orders o ON c.id = o.customer_id
        GROUP BY c.id, c.name, c.segment, c.region
        """
        with self.engine.connect() as conn:
            df = pd.read_sql(sql, conn)

        if df.empty or len(df) < n_clusters:
            return {"success": False, "error": "Insufficient customer order data for RFM clustering."}

        # Fill any missing values
        df["recency"] = df["recency"].fillna(df["recency"].median())

        features = ["recency", "frequency", "monetary"]
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(df[features])

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        df["cluster"] = kmeans.fit_predict(X_scaled)

        # Profile clusters and label them intelligently
        cluster_summary = []
        cluster_labels = {}
        for c in range(n_clusters):
            c_df = df[df["cluster"] == c]
            avg_rec = float(c_df["recency"].mean())
            avg_freq = float(c_df["frequency"].mean())
            avg_mon = float(c_df["monetary"].mean())
            count = len(c_df)

            # Semantic naming based on RFM profile
            if avg_mon > df["monetary"].quantile(0.75):
                label = "Champions (High Spend & Frequent)"
            elif avg_rec > df["recency"].quantile(0.65):
                label = "At Risk / Inactive"
            elif avg_freq > df["frequency"].median():
                label = "Loyal Mid-Tier"
            else:
                label = "Occasional / Low Spend"

            cluster_labels[c] = label

            cluster_summary.append({
                "cluster_id": c,
                "label": label,
                "customer_count": count,
                "pct_of_customers": round((count / len(df)) * 100, 1),
                "avg_recency_days": round(avg_rec, 1),
                "avg_order_frequency": round(avg_freq, 1),
                "avg_monetary_spend": round(avg_mon, 2),
                "total_cluster_spend": round(float(c_df["monetary"].sum()), 2)
            })

        df["cluster_label"] = df["cluster"].map(cluster_labels)

        # Generate a scatter plot figure
        fig = px.scatter(
            df,
            x="frequency",
            y="monetary",
            size="monetary",
            color="cluster_label",
            hover_data=["customer_name", "recency", "declared_segment"],
            title="Customer RFM Segmentation Clusters (K-Means)",
            labels={"frequency": "Order Frequency (Count)", "monetary": "Total Spend ($)"},
            template="plotly_white"
        )

        fig_json = fig.to_json()
        return {
            "success": True,
            "n_clusters": n_clusters,
            "total_customers": len(df),
            "cluster_profiles": cluster_summary,
            "sample_segmented_customers": df[["customer_name", "declared_segment", "recency", "frequency", "monetary", "cluster_label"]].head(15).to_dict(orient="records"),
            "figure_json": fig_json,
            "figure_dict": json.loads(fig_json)
        }


# Singleton instance
analyst_tools = DataAnalystTools()
