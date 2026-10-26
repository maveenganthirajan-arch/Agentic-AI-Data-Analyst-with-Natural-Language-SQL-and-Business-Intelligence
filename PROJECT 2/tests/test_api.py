"""
Tests for FastAPI Backend Service.
"""

import pytest
from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "/docs" in data["docs_url"]

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["stats"]["orders"] > 0

def test_get_kpis():
    response = client.get("/api/kpis")
    assert response.status_code == 200
    data = response.json()
    assert len(data["kpis"]) == 4

def test_get_revenue_trend():
    response = client.get("/api/revenue-trend?timeframe=all")
    assert response.status_code == 200
    data = response.json()
    assert len(data["records"]) > 0

def test_get_bestselling():
    response = client.get("/api/bestselling?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["products"]) <= 5

def test_sql_validate_endpoint():
    # Valid
    resp = client.post("/api/sql/validate", json={"query": "SELECT * FROM orders LIMIT 5"})
    assert resp.status_code == 200
    assert resp.json()["is_valid"] is True

    # Invalid (DROP)
    resp = client.post("/api/sql/validate", json={"query": "DROP TABLE customers"})
    assert resp.status_code == 200
    assert resp.json()["is_valid"] is False

def test_agent_query_endpoint():
    payload = {"question": "Which product category contributed most to the revenue decline last quarter?"}
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["sql_valid"] is True
    assert "Electronics" in data["insights"]
    assert data["verification"]["status"] == "VERIFIED"
