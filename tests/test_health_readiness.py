"""
Tests for Workstream 11: Health, Liveness, and Readiness Endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_detailed_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["ok", "healthy"]
    assert "components" in data
    assert data["components"]["database"] == "healthy"


def test_liveness_endpoint():
    res = client.get("/health/live")
    assert res.status_code == 200
    assert res.json()["status"] == "alive"

def test_readiness_endpoint():
    res = client.get("/health/ready")
    assert res.status_code == 200
    assert res.json()["status"] == "ready"
