"""
Comprehensive tests for LangGraph Workflow Orchestration and Business Analytics Engine.
"""

import pytest
from agent.workflow import run_agent_workflow
from agent.engine import analytics_engine

def test_workflow_quarterly_decline_analysis():
    question = "Which product category contributed most to the revenue decline last quarter?"
    res = run_agent_workflow(question)

    assert res["sql_valid"] is True
    assert len(res["plan"]) > 0
    assert "SELECT" in res["sql_query"]
    assert res["calc_result"]["top_declining_category"] == "Electronics"
    assert res["calc_result"]["net_revenue_change"] < 0
    assert res["verification"]["status"] == "VERIFIED"
    assert res["chart_dict"] is not None
    assert "Electronics" in res["insights"]

def test_workflow_customer_segmentation():
    question = "Segment customers using K-Means RFM clustering"
    res = run_agent_workflow(question)

    assert res["sql_valid"] is True
    assert res["calc_result"]["success"] is True
    assert len(res["calc_result"]["cluster_profiles"]) == 4
    assert res["chart_dict"] is not None
    assert "Champions" in res["insights"] or "Loyal" in res["insights"]

def test_workflow_revenue_trend():
    question = "What is the overall revenue trend for this year?"
    res = run_agent_workflow(question)

    assert res["sql_valid"] is True
    assert len(res["sql_records"]) > 0
    assert res["chart_type"] == "line"

def test_workflow_top_products():
    question = "What are the best selling products?"
    res = run_agent_workflow(question)

    assert res["sql_valid"] is True
    assert len(res["sql_records"]) <= 10
    assert res["chart_type"] == "bar"

def test_intent_classification():
    q1 = "Which product category contributed most to the revenue decline last quarter?"
    assert analytics_engine.analyze_intent(q1)["intent"] == "quarterly_decline_analysis"

    q2 = "Can you show me the sales trends for the past two years?"
    assert analytics_engine.analyze_intent(q2)["intent"] == "revenue_trend"

    q3 = "Segment customers based on purchasing behavior"
    assert analytics_engine.analyze_intent(q3)["intent"] == "customer_segmentation"
