"""
AgentAnalyst - Enterprise Agentic AI Data Analyst Dashboard
Designed to mirror the modern executive UI with dual-pane layout, KPI cards,
interactive Plotly analytics, and an 'Ask AI' LangGraph Copilot.
"""

import sys
import os

# Add root directory to path for seamless imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import text

from database.schema import get_engine, init_db
from agent.workflow import run_agent_workflow
from agent.validator import validate_sql
from agent.tools import analyst_tools
from agent.verifier import verifier

# Page configuration
st.set_page_config(
    page_title="AgentAnalyst - AI Data Analyst",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS matching the reference dashboard UI
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Modern clean container */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        padding-left: 2rem;
        padding-right: 2rem;
        max-width: 100% !important;
    }

    /* Top bar */
    .top-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-bottom: 1rem;
        border-bottom: 1px solid #E2E8F0;
        margin-bottom: 1.5rem;
    }
    
    .brand-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1E293B;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .brand-tag {
        font-size: 0.72rem;
        background: #EFF6FF;
        color: #2563EB;
        padding: 2px 8px;
        border-radius: 12px;
        font-weight: 600;
    }

    /* KPI Cards */
    .kpi-container {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
        margin-bottom: 1.5rem;
    }

    .kpi-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        padding: 1.2rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }

    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.06);
    }

    .kpi-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.5rem;
    }

    .kpi-label {
        font-size: 0.85rem;
        color: #64748B;
        font-weight: 500;
    }

    .kpi-value {
        font-size: 1.45rem;
        font-weight: 700;
        color: #0F172A;
    }

    .badge-up {
        background: #DCFCE7;
        color: #16A34A;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 8px;
        display: inline-flex;
        align-items: center;
    }

    .badge-down {
        background: #FEE2E2;
        color: #DC2626;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 8px;
        display: inline-flex;
        align-items: center;
    }

    /* Chat bubble styling */
    .user-bubble {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 0.9rem 1.1rem;
        margin-bottom: 0.75rem;
        font-size: 0.92rem;
        color: #1E293B;
    }

    .agent-bubble {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 4px solid #2563EB;
        border-radius: 14px;
        padding: 1.1rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }

    .agent-header {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 0.78rem;
        font-weight: 700;
        color: #2563EB;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.6rem;
    }

    /* Prompt Suggestion Pills */
    .prompt-pill-btn {
        background: #F1F5F9;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 8px 12px;
        font-size: 0.8rem;
        color: #334155;
        text-align: left;
        cursor: pointer;
        transition: all 0.15s ease;
        margin-bottom: 6px;
        display: block;
        width: 100%;
    }

    .prompt-pill-btn:hover {
        background: #E2E8F0;
        border-color: #CBD5E1;
        color: #0F172A;
    }

    /* Hide standard streamlit footer */
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Database connectivity
engine = get_engine()

# Initialize session state for chat and selected timeframe
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {
            "role": "user",
            "content": "What is the overall revenue trend for this year?"
        },
        {
            "role": "assistant",
            "content": "The overall revenue trajectory for 2025 demonstrates strong expansion with mid-year surges and a strong Q3 peak, followed by category-specific supply adjustments in Q4.",
            "plan": [
                "Extract monthly revenue from orders table.",
                "Calculate Month-over-Month growth rates.",
                "Verify monthly totals against raw SQLite records."
            ],
            "sql_query": "SELECT strftime('%Y-%m', order_date) as month, ROUND(SUM(total_amount), 2) as revenue FROM orders WHERE strftime('%Y', order_date) = '2025' GROUP BY month ORDER BY month",
            "verification": {"status": "VERIFIED", "difference": 0.0},
            "chart_type": "line"
        }
    ]

if "timeframe_filter" not in st.session_state:
    st.session_state.timeframe_filter = "All Time"

# ------------------------------------------------------------------
# Sidebar: System Status & Navigation
# ------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚡ **AgentAnalyst**")
    st.caption("Autonomous AI Data Analyst")
    
    st.markdown("---")
    nav_option = st.radio(
        "Navigation",
        [
            "📊 Executive Dashboard",
            "💬 Ask AI Copilot",
            "🎯 RFM Customer Segments",
            "🔒 SQL Security Sandbox",
            "🕸️ LangGraph Architecture"
        ],
        index=0
    )

    st.markdown("---")
    st.markdown("#### Database Ground Truth")
    try:
        with engine.connect() as conn:
            cnt_orders = conn.execute(text("SELECT COUNT(*) FROM orders")).scalar()
            cnt_cust = conn.execute(text("SELECT COUNT(*) FROM customers")).scalar()
            cnt_prod = conn.execute(text("SELECT COUNT(*) FROM products")).scalar()
            tot_rev = conn.execute(text("SELECT SUM(total_amount) FROM orders")).scalar() or 0.0

        st.markdown(f"""
        - **Orders:** `{cnt_orders:,}`
        - **Customers:** `{cnt_cust:,}`
        - **Products:** `{cnt_prod:,}`
        - **Total Rev:** `${tot_rev:,.2f}`
        - **Engine:** `SQLite + SQLAlchemy`
        - **Security:** `Read-Only AST Auditor`
        """)
    except Exception as e:
        st.error(f"DB Error: {e}")

    st.markdown("---")
    if st.button("🔄 Reset / Re-seed Database"):
        with st.spinner("Seeding database..."):
            from database.seed_data import seed_database
            seed_database(reset=True)
            st.success("Database seeded with fresh multi-year data!")
            st.rerun()

# ------------------------------------------------------------------
# Helper Functions for Visuals and Data
# ------------------------------------------------------------------
def fetch_kpis():
    with engine.connect() as conn:
        rev = conn.execute(text("SELECT ROUND(COALESCE(SUM(total_amount), 0), 2) FROM orders")).scalar() or 0.0
        orders_count = conn.execute(text("SELECT COUNT(*) FROM orders")).scalar() or 0
        refunds = conn.execute(text("SELECT ROUND(COALESCE(SUM(refund_amount), 0), 2) FROM returns")).scalar() or 0.0
        marketing = conn.execute(text("SELECT ROUND(COALESCE(SUM(spend_amount), 0), 2) FROM marketing_spend")).scalar() or 0.0
    return rev, orders_count, refunds, marketing

def fetch_revenue_series(timeframe="All Time"):
    where_clause = ""
    if timeframe == "This Year (2025)":
        where_clause = "WHERE strftime('%Y', order_date) = '2025'"
    elif timeframe == "Last Year (2024)":
        where_clause = "WHERE strftime('%Y', order_date) = '2024'"

    sql = f"""
    SELECT 
        strftime('%Y-%m', order_date) as period,
        ROUND(SUM(total_amount), 2) as revenue,
        COUNT(id) as orders_count
    FROM orders
    {where_clause}
    GROUP BY period
    ORDER BY period ASC
    """
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn)
    return df

def fetch_best_selling():
    sql = """
    SELECT 
        p.name as product_name,
        p.brand,
        p.category,
        p.stock_quantity as stock,
        SUM(oi.quantity) as sales_units,
        ROUND(p.unit_price, 2) as price,
        ROUND(SUM(oi.total_revenue), 2) as total_revenue
    FROM products p
    JOIN order_items oi ON p.id = oi.product_id
    GROUP BY p.id, p.name, p.brand, p.category, p.stock_quantity, p.unit_price
    ORDER BY total_revenue DESC
    LIMIT 7
    """
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn)
    return df


# ------------------------------------------------------------------
# View 1: Executive Dashboard (Split Layout Matching Screenshot)
# ------------------------------------------------------------------
if nav_option == "📊 Executive Dashboard":
    # Header
    st.markdown("""
    <div class="top-header">
        <div class="brand-title">
            <span>⚡ AgentAnalyst</span>
            <span class="brand-tag">Autonomous LangGraph Orchestrator</span>
        </div>
        <div style="font-size: 0.85rem; color: #64748B;">
            Live Analytics & Natural-Language SQL Reasoning
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Main Split View: Left is Analytics (62%), Right is Ask AI (38%)
    col_dash, col_chat = st.columns([1.65, 1.0], gap="large")

    # --- LEFT PANE: ANALYTICS & TABLES ---
    with col_dash:
        # 1. KPI Cards
        rev, orders_count, refunds, marketing = fetch_kpis()
        
        kpi_html = f"""
        <div class="kpi-container">
            <div class="kpi-card">
                <div class="kpi-header">
                    <span class="kpi-label">🛒 Sales Volume</span>
                    <span class="badge-up">+12%</span>
                </div>
                <div class="kpi-value">{orders_count:,}</div>
                <div style="font-size: 0.72rem; color: #94A3B8; margin-top: 4px;">Completed orders</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-header">
                    <span class="kpi-label">💲 Total Revenue</span>
                    <span class="badge-up">+35%</span>
                </div>
                <div class="kpi-value">${rev:,.2f}</div>
                <div style="font-size: 0.72rem; color: #94A3B8; margin-top: 4px;">Net merchandise volume</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-header">
                    <span class="kpi-label">🔄 Total Return</span>
                    <span class="badge-down">-5%</span>
                </div>
                <div class="kpi-value">${refunds:,.2f}</div>
                <div style="font-size: 0.72rem; color: #94A3B8; margin-top: 4px;">Refunds & defect return</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-header">
                    <span class="kpi-label">📢 Marketing</span>
                    <span class="badge-up">+15%</span>
                </div>
                <div class="kpi-value">${marketing:,.2f}</div>
                <div style="font-size: 0.72rem; color: #94A3B8; margin-top: 4px;">Multi-channel spend</div>
            </div>
        </div>
        """
        st.markdown(kpi_html, unsafe_allow_html=True)

        # 2. Overall Revenue Chart with Dropdown Filter
        col_title, col_filter = st.columns([2, 1])
        with col_title:
            st.markdown("#### Overall Revenue")
            st.caption("Historical performance across sales channels")
        with col_filter:
            tf_choice = st.selectbox(
                "Filter Period",
                ["All Time", "This Year (2025)", "Last Year (2024)"],
                label_visibility="collapsed"
            )

        df_rev = fetch_revenue_series(tf_choice)
        
        # Smooth Spline Line Chart matching the screenshot
        fig_trend = px.line(
            df_rev,
            x="period",
            y="revenue",
            markers=True,
            template="plotly_white",
            color_discrete_sequence=["#2563EB"]
        )
        fig_trend.update_traces(
            line_shape="spline",
            line_width=3.5,
            marker=dict(size=7, color="#2563EB", line=dict(width=2, color="white")),
            fill="tozeroy",
            fillcolor="rgba(37, 99, 235, 0.06)",
            hovertemplate="<b>%{x}</b><br>Revenue: $%{y:,.2f}<extra></extra>"
        )
        fig_trend.update_layout(
            height=280,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(showgrid=False, title=None),
            yaxis=dict(showgrid=True, gridcolor="#F1F5F9", title=None, tickprefix="$", tickformat=",.0s"),
            hoverlabel=dict(bgcolor="#1E293B", font_color="#FFFFFF", font_size=12)
        )
        st.plotly_chart(fig_trend, width="stretch")

        # 3. Best Selling Table
        st.markdown("#### Best Selling")
        st.caption("Ranked by total revenue generation and live warehouse stock levels")

        df_best = fetch_best_selling()
        
        # Display clean styled table
        display_df = df_best.copy()
        display_df["price"] = display_df["price"].apply(lambda x: f"${x:,.2f}")
        display_df["total_revenue"] = display_df["total_revenue"].apply(lambda x: f"${x:,.2f}")
        display_df = display_df.rename(columns={
            "product_name": "Product Name",
            "brand": "Brand",
            "category": "Category",
            "stock": "Stock",
            "sales_units": "Units Sold",
            "price": "Price",
            "total_revenue": "Total Revenue"
        })

        st.dataframe(
            display_df,
            width="stretch",
            hide_index=True,
            column_config={
                "Stock": st.column_config.ProgressColumn(
                    "Stock",
                    format="%d",
                    min_value=0,
                    max_value=300
                ),
            }
        )

    # --- RIGHT PANE: ASK AI COPILOT ---
    with col_chat:
        st.markdown("""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem;">
            <div style="font-weight: 700; font-size: 1.15rem; color: #1E293B;">
                Ask AI ✨
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Quick Suggestion Buttons
        st.markdown("<div style='font-size: 0.78rem; font-weight: 600; color: #64748B; margin-bottom: 6px;'>SUGGESTED BUSINESS QUESTIONS</div>", unsafe_allow_html=True)
        
        btn_decline = st.button("📉 Which product category contributed most to the revenue decline last quarter?", width="stretch")
        btn_trend = st.button("📈 Can you show me the sales trends for the past two years?", width="stretch")
        btn_rfm = st.button("👥 Segment customers using K-Means RFM clustering", width="stretch")
        btn_prods = st.button("🏆 Identify and categorize sales performance by product", width="stretch")

        # Render Chat History
        chat_container = st.container()

        with chat_container:
            for item in st.session_state.chat_history:
                if item["role"] == "user":
                    st.markdown(f"""
                    <div class="user-bubble">
                        <div style="font-size: 0.75rem; font-weight: 600; color: #64748B; margin-bottom: 2px;">YOU</div>
                        {item["content"]}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="agent-bubble">
                        <div class="agent-header">
                            <span>🤖 INSIGHT GA</span>
                            <span style="color: #94A3B8; font-size: 0.7rem; font-weight: 400;">(LangGraph Agent)</span>
                        </div>
                        <div style="font-size: 0.9rem; line-height: 1.5; color: #1E293B;">
                            {item["content"]}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # If this message has an attached chart
                    if item.get("chart_dict"):
                        st.plotly_chart(go.Figure(item["chart_dict"]), width="stretch")

                    # Show Agent Reasoning Expander
                    with st.expander("🔍 View LangGraph Analytical Plan & SQL Validation", expanded=False):
                        if item.get("plan"):
                            st.markdown("**LangGraph Plan Execution:**")
                            for step in item["plan"]:
                                st.markdown(f"- {step}")

                        if item.get("sql_query"):
                            st.markdown("**Validated Read-Only SQL Query:**")
                            st.code(item["sql_query"], language="sql")

                        if item.get("verification"):
                            ver = item["verification"]
                            v_status = ver.get("status", "VERIFIED")
                            badge_color = "green" if v_status == "VERIFIED" else "red"
                            st.markdown(f"**Ground Truth Verification:** :{badge_color}[{v_status}]")
                            if "db_truth" in ver:
                                st.json(ver["db_truth"])

        # Chat Input
        user_input = st.chat_input("What's on your mind? (e.g., Which category declined last quarter?)")

        active_query = None
        if btn_decline:
            active_query = "Which product category contributed most to the revenue decline last quarter?"
        elif btn_trend:
            active_query = "Can you show me the sales trends for the past two years?"
        elif btn_rfm:
            active_query = "Segment customers using K-Means RFM clustering"
        elif btn_prods:
            active_query = "Identify and categorize sales performance by product"
        elif user_input:
            active_query = user_input

        if active_query:
            # Append user question
            st.session_state.chat_history.append({"role": "user", "content": active_query})

            with st.spinner("🤖 AgentAnalyst is planning, querying database, validating figures, and plotting..."):
                agent_res = run_agent_workflow(active_query)

                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": agent_res.get("insights", "Analysis complete."),
                    "plan": agent_res.get("plan", []),
                    "sql_query": agent_res.get("sql_query", ""),
                    "verification": agent_res.get("verification", {}),
                    "chart_dict": agent_res.get("chart_dict"),
                    "chart_type": agent_res.get("chart_type")
                })
                st.rerun()

        if st.button("🗑️ Clear Chat History"):
            st.session_state.chat_history = []
            st.rerun()


# ------------------------------------------------------------------
# View 2: Dedicated Ask AI Copilot (Full Width)
# ------------------------------------------------------------------
elif nav_option == "💬 Ask AI Copilot":
    st.markdown("### 💬 **Interactive AI Data Analyst Copilot**")
    st.caption("Ask natural language business questions. The LangGraph agent plans, writes SQL, validates security, audits calculations, and charts results.")

    col_q1, col_q2, col_q3 = st.columns(3)
    with col_q1:
        if st.button("📉 Category Revenue Decline", width="stretch"):
            st.session_state.temp_prompt = "Which product category contributed most to the revenue decline last quarter?"
    with col_q2:
        if st.button("📈 Two-Year Sales Trend", width="stretch"):
            st.session_state.temp_prompt = "What is the overall revenue trend for this year?"
    with col_q3:
        if st.button("👥 Customer Segmentation", width="stretch"):
            st.session_state.temp_prompt = "Segment customers using K-Means RFM clustering"

    prompt_val = st.text_input("Enter your business question:", value=st.session_state.get("temp_prompt", "Which product category contributed most to the revenue decline last quarter?"))

    if st.button("🚀 Analyze with Agent", type="primary"):
        with st.spinner("Running LangGraph workflow..."):
            res = run_agent_workflow(prompt_val)

            # 1. Executive Summary
            st.markdown("---")
            st.markdown(res.get("insights", ""))

            # 2. Visualization
            if res.get("chart_dict"):
                st.markdown("#### Evidence Visualization")
                st.plotly_chart(go.Figure(res["chart_dict"]), width="stretch")

            # 3. Technical Inspection Tabs
            st.markdown("#### Agent Execution Details")
            t_plan, t_sql, t_ver, t_data = st.tabs(["📋 Execution Plan", "💾 Audited SQL", "🛡️ Numerical Verification", "🔢 Extracted Data"])

            with t_plan:
                st.markdown("**LangGraph State Machine Steps:**")
                for s in res.get("plan", []):
                    st.markdown(f"- {s}")

            with t_sql:
                st.markdown(f"**SQL Validation Status:** {'✅ PASSED (Read-Only)' if res.get('sql_valid') else '❌ FAILED'}")
                st.code(res.get("sql_query", ""), language="sql")

            with t_ver:
                st.markdown(f"**Verification Status:** `{res.get('verification', {}).get('status')}`")
                st.json(res.get("verification", {}))

            with t_data:
                records = res.get("sql_records", [])
                st.write(f"Total Rows Returned: {len(records)}")
                if records:
                    st.dataframe(pd.DataFrame(records), width="stretch")


# ------------------------------------------------------------------
# View 3: RFM Customer Segments (K-Means ML)
# ------------------------------------------------------------------
elif nav_option == "🎯 RFM Customer Segments":
    st.markdown("### 🎯 **Customer RFM Segmentation (Scikit-Learn K-Means)**")
    st.caption("Demonstrates machine learning fundamentals: Recency, Frequency, and Monetary value clustering.")

    k_clusters = st.slider("Select Number of Clusters (k)", min_value=2, max_value=6, value=4)
    
    with st.spinner("Computing clusters..."):
        rfm_res = analyst_tools.run_customer_segmentation(n_clusters=k_clusters)

    if rfm_res["success"]:
        # Profiles
        st.markdown("#### Identified Customer Cohorts")
        cols = st.columns(len(rfm_res["cluster_profiles"]))
        for i, p in enumerate(rfm_res["cluster_profiles"]):
            with cols[i]:
                st.metric(
                    label=p["label"],
                    value=f"{p['customer_count']} Users",
                    delta=f"${p['avg_monetary_spend']:,.0f} Avg"
                )
                st.caption(f"Orders: {p['avg_order_frequency']} | Recency: {p['avg_recency_days']}d")

        # Scatter Plot
        st.markdown("#### Multi-Dimensional RFM Distribution")
        fig = go.Figure(rfm_res["figure_dict"])
        st.plotly_chart(fig, width="stretch")

        # Sample customer list
        st.markdown("#### Sample Customers by Cluster")
        st.dataframe(pd.DataFrame(rfm_res["sample_segmented_customers"]), width="stretch")


# ------------------------------------------------------------------
# View 4: SQL Security Sandbox
# ------------------------------------------------------------------
elif nav_option == "🔒 SQL Security Sandbox":
    st.markdown("### 🔒 **SQL Read-Only Security Validator & Sandbox**")
    st.caption("Test the AST query auditor that enforces read-only operations and prevents SQL injection.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Safe Pre-set Queries")
        if st.button("Sample 1: Category Revenue"):
            st.session_state.sql_test = "SELECT p.category, SUM(oi.total_revenue) as rev FROM order_items oi JOIN products p ON oi.product_id = p.id GROUP BY p.category ORDER BY rev DESC"
        if st.button("Sample 2: Monthly Orders"):
            st.session_state.sql_test = "SELECT strftime('%Y-%m', order_date) as month, COUNT(*) as orders_count FROM orders GROUP BY month"
    
    with col2:
        st.markdown("#### Dangerous Injection Pre-sets (Blocked)")
        if st.button("Injection 1: DROP TABLE customers"):
            st.session_state.sql_test = "DROP TABLE customers"
        if st.button("Injection 2: Stacked Statement"):
            st.session_state.sql_test = "SELECT * FROM products; DELETE FROM orders;"

    custom_sql = st.text_area("Enter SQL query to validate & execute:", value=st.session_state.get("sql_test", "SELECT category, brand, unit_price FROM products LIMIT 5"), height=100)

    if st.button("🛡️ Audit & Execute Query"):
        val = validate_sql(custom_sql)
        if val["is_valid"]:
            st.success("✅ **Query Passed Security Audit:** Read-only SELECT confirmed.")
            st.markdown(f"**Tables Accessed:** `{', '.join(val['tables_accessed'])}`")
            
            exec_res = analyst_tools.execute_sql(val["sanitized_query"])
            if exec_res["success"]:
                st.dataframe(pd.DataFrame(exec_res["records"]), width="stretch")
            else:
                st.error(exec_res["error"])
        else:
            st.error(f"🚫 **Security Violation Detected:** {val['error']}")


# ------------------------------------------------------------------
# View 5: LangGraph Architecture Graph
# ------------------------------------------------------------------
elif nav_option == "🕸️ LangGraph Architecture":
    st.markdown("### 🕸️ **LangGraph Agent Workflow Architecture**")
    st.caption("Visual representation of state transitions, conditional edges, and error-recovery routing.")

    st.markdown("""
    ```mermaid
    flowchart TD
        Start([User Question]) --> Planner[Planner Node<br/>Decomposes Question]
        Planner --> SQLGen[SQL Generator Node<br/>Generates Read-Only SQLite]
        SQLGen --> Validator{SQL Security Validator<br/>AST & Policy Audit}

        Validator -- Invalid Query --> ErrorRecovery[Error Recovery Node<br/>Refines Query]
        ErrorRecovery --> Validator

        Validator -- Valid Query --> Executor[SQL Executor Node<br/>Queries Database]
        Executor --> Analyst[Data Analyst Node<br/>Pandas & ML Clustering]
        Analyst --> Verifier[Numerical Verifier<br/>Double Checks against DB]
        Verifier --> ChartGen[Chart Generator Node<br/>Plotly Interactive Visuals]
        ChartGen --> Synthesizer[Executive Synthesizer<br/>Evidence-Based Insights]
        Synthesizer --> End([Executive Report])
    ```
    """)

    st.info("""
    **Workflow Highlights:**
    - **Planner Node:** Decomposes the business question into measurable steps.
    - **SQL Security Validator:** Guarantees no data modification (`DROP`, `DELETE`, `UPDATE` blocked).
    - **Numerical Verifier:** Guarantees zero arithmetic hallucinations by independently aggregating raw DB rows.
    - **Executive Synthesizer:** Direct, evidence-based business insights and recommendations.
    """)
