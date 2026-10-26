"""
FastAPI REST API Backend for Agentic AI Data Analyst.
Serves LangGraph workflow execution, KPI aggregates, data endpoints, and SQL security validation.
"""

from typing import Dict, Any, List, Optional
import numpy as np
from fastapi.responses import RedirectResponse, JSONResponse

def sanitize_for_json(obj: Any) -> Any:
    """Recursively converts numpy types and non-serializable objects into standard python types."""
    if isinstance(obj, dict):
        return {str(k): sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.floating, float)):
        return float(obj)
    elif isinstance(obj, (np.integer, int)):
        return int(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif pd.isna(obj):
        return None
    return obj
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pandas as pd
from sqlalchemy import text

from database.schema import get_engine
from agent.workflow import run_agent_workflow
from agent.validator import validate_sql
from agent.tools import analyst_tools

app = FastAPI(
    title="Agentic AI Data Analyst API",
    description="Enterprise Agentic AI REST Service powered by LangGraph, SQL, and Plotly",
    version="1.0.0"
)

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = get_engine()

@app.get("/")
def root():
    """Root landing endpoint: provides API overview and links to docs."""
    return {
        "service": "Agentic AI Data Analyst API",
        "status": "online",
        "docs_url": "/docs",
        "health_url": "/api/health",
        "endpoints": [
            {"method": "POST", "path": "/api/query", "desc": "Execute LangGraph analytical agent on questions"},
            {"method": "GET", "path": "/api/kpis", "desc": "Executive KPI aggregate cards"},
            {"method": "GET", "path": "/api/revenue-trend", "desc": "Filterable revenue time series"},
            {"method": "GET", "path": "/api/bestselling", "desc": "Best-selling products ranking"},
            {"method": "POST", "path": "/api/sql/validate", "desc": "Read-only SQL AST security validator"},
            {"method": "GET", "path": "/api/customer-segments", "desc": "K-Means RFM clustering profiles"},
            {"method": "GET", "path": "/api/workflow/mermaid", "desc": "LangGraph architecture diagram"}
        ]
    }

# Request & Response Models
class QueryRequest(BaseModel):
    question: str = Field(..., json_schema_extra={"example": "Which product category contributed most to the revenue decline last quarter?"})

class SQLValidateRequest(BaseModel):
    query: str = Field(..., json_schema_extra={"example": "SELECT category, SUM(total_revenue) FROM order_items GROUP BY category"})

class QueryResponse(BaseModel):
    question: str
    plan: List[str]
    sql_query: str
    sql_valid: bool
    sql_error: Optional[str]
    row_count: int
    calc_result: Dict[str, Any]
    verification: Dict[str, Any]
    chart_dict: Optional[Dict[str, Any]]
    insights: str


@app.get("/api/health")
def health_check():
    """Verify API and SQLite database health."""
    try:
        with engine.connect() as conn:
            orders_cnt = conn.execute(text("SELECT COUNT(*) FROM orders")).scalar()
            products_cnt = conn.execute(text("SELECT COUNT(*) FROM products")).scalar()
            customers_cnt = conn.execute(text("SELECT COUNT(*) FROM customers")).scalar()

        return {
            "status": "healthy",
            "database": "connected",
            "stats": {
                "orders": orders_cnt,
                "products": products_cnt,
                "customers": customers_cnt
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")


@app.post("/api/query", response_model=QueryResponse)
def execute_agent_query(req: QueryRequest):
    """
    Executes the full LangGraph Agent pipeline:
    1. Plan analytical steps
    2. Formulate SQL
    3. Validate read-only security
    4. Execute query
    5. Compute Python statistics
    6. Double-check numbers against DB ground truth
    7. Generate Plotly chart
    8. Synthesize executive business insights
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        result = run_agent_workflow(req.question)
        response_data = {
            "question": req.question,
            "plan": result.get("plan", []),
            "sql_query": result.get("sql_query", ""),
            "sql_valid": result.get("sql_valid", False),
            "sql_error": result.get("sql_error"),
            "row_count": len(result.get("sql_records", [])),
            "calc_result": result.get("calc_result", {}),
            "verification": result.get("verification", {}),
            "chart_dict": result.get("chart_dict"),
            "insights": result.get("insights", "")
        }
        return sanitize_for_json(response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent workflow error: {str(e)}")


@app.get("/api/kpis")
def get_dashboard_kpis():
    """
    Returns executive KPI cards matching the dashboard UI:
    - Sales (Order count & trajectory)
    - Total Revenue
    - Return / Refunds
    - Marketing Spend
    """
    with engine.connect() as conn:
        rev = conn.execute(text("SELECT ROUND(COALESCE(SUM(total_amount), 0), 2) FROM orders")).scalar() or 0.0
        orders_count = conn.execute(text("SELECT COUNT(*) FROM orders")).scalar() or 0
        refunds = conn.execute(text("SELECT ROUND(COALESCE(SUM(refund_amount), 0), 2) FROM returns")).scalar() or 0.0
        marketing = conn.execute(text("SELECT ROUND(COALESCE(SUM(spend_amount), 0), 2) FROM marketing_spend")).scalar() or 0.0

    return {
        "kpis": [
            {
                "title": "Sales",
                "value": f"{orders_count:,}",
                "display_value": f"${orders_count * 5.45:,.2f}",
                "change": "+12%",
                "trend": "up",
                "description": "Total order count across all channels"
            },
            {
                "title": "Total Revenue",
                "value": f"${rev:,.2f}",
                "display_value": f"${rev:,.2f}",
                "change": "+35%",
                "trend": "up",
                "description": "Gross completed merchandise value"
            },
            {
                "title": "Return",
                "value": f"${refunds:,.2f}",
                "display_value": f"${refunds:,.2f}",
                "change": "-5%",
                "trend": "down",
                "description": "Processed returns & defect refunds"
            },
            {
                "title": "Marketing",
                "value": f"${marketing:,.2f}",
                "display_value": f"${marketing:,.2f}",
                "change": "+15%",
                "trend": "up",
                "description": "Multi-channel advertising expenditure"
            }
        ]
    }


@app.get("/api/revenue-trend")
def get_revenue_trend(timeframe: str = Query("all", pattern="^(all|2025|2024|quarterly)$")):
    """Retrieves monthly or quarterly revenue trends for line charting."""
    if timeframe == "quarterly":
        sql = """
        SELECT 
            strftime('%Y-Q', o.order_date) || ((strftime('%m', o.order_date) - 1) / 3 + 1) AS period,
            ROUND(SUM(o.total_amount), 2) as revenue
        FROM orders o
        GROUP BY period
        ORDER BY period ASC
        """
    elif timeframe in ("2025", "2024"):
        sql = f"""
        SELECT 
            strftime('%Y-%m', o.order_date) as period,
            ROUND(SUM(o.total_amount), 2) as revenue
        FROM orders o
        WHERE strftime('%Y', o.order_date) = '{timeframe}'
        GROUP BY period
        ORDER BY period ASC
        """
    else:
        sql = """
        SELECT 
            strftime('%Y-%m', o.order_date) as period,
            ROUND(SUM(o.total_amount), 2) as revenue
        FROM orders o
        GROUP BY period
        ORDER BY period ASC
        """

    with engine.connect() as conn:
        df = pd.read_sql(sql, conn)

    return {"timeframe": timeframe, "records": df.to_dict(orient="records")}


@app.get("/api/bestselling")
def get_best_selling(limit: int = 10):
    """Retrieves best-selling products table matching the dashboard UI."""
    sql = """
    SELECT 
        p.id,
        p.name as product_name,
        p.brand,
        p.category,
        p.stock_quantity as stock,
        SUM(oi.quantity) as sales_units,
        ROUND(SUM(oi.total_revenue), 2) as total_sales,
        ROUND(p.unit_price, 2) as price
    FROM products p
    JOIN order_items oi ON p.id = oi.product_id
    GROUP BY p.id, p.name, p.brand, p.category, p.stock_quantity, p.unit_price
    ORDER BY total_sales DESC
    LIMIT :limit
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn, params={"limit": limit})

    return {"limit": limit, "products": df.to_dict(orient="records")}


@app.post("/api/sql/validate")
def validate_custom_sql(req: SQLValidateRequest):
    """Sandbox endpoint for verifying SQL read-only constraints and safety."""
    result = validate_sql(req.query)
    return result


@app.get("/api/customer-segments")
def get_customer_segments(clusters: int = 4):
    """Executes RFM K-Means clustering and returns customer segment profiles."""
    result = analyst_tools.run_customer_segmentation(n_clusters=clusters)
    return result


@app.get("/api/workflow/mermaid")
def get_workflow_mermaid():
    """Returns Mermaid diagram code for visualizing the LangGraph Agent architecture."""
    mermaid = """
    flowchart TD
        Start([User Business Question]) --> Planner[Planner Node<br/>Decomposes into Analytical Steps]
        Planner --> SQLGen[SQL Generator Node<br/>Formulates SQLite Query]
        SQLGen --> Validator{SQL Security Validator<br/>Read-Only & AST Check}
        
        Validator -- Invalid Query --> ErrorRecovery[Error Recovery Node<br/>Refines Query]
        ErrorRecovery --> Validator
        
        Validator -- Valid Query --> Executor[SQL Executor Node<br/>Queries SQLite Database]
        Executor --> Analyst[Data Analyst Node<br/>Pandas Stats & ML Clustering]
        Analyst --> Verifier[Numerical Verifier<br/>Audits against DB Ground Truth]
        Verifier --> ChartGen[Chart Generator Node<br/>Creates Interactive Plotly Visuals]
        ChartGen --> Synthesizer[Executive Synthesizer<br/>Generates Evidence-Based Insights]
        Synthesizer --> End([Evidence-Based Executive Report])

        classDef valid fill:#10B981,stroke:#059669,stroke-width:2px,color:#fff;
        classDef danger fill:#EF4444,stroke:#DC2626,stroke-width:2px,color:#fff;
        classDef node fill:#2563EB,stroke:#1D4ED8,stroke-width:2px,color:#fff;
        class Planner,SQLGen,Executor,Analyst,Verifier,ChartGen,Synthesizer,ErrorRecovery node;
    """
    return {"mermaid": mermaid.strip()}
