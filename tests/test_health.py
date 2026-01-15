"""Tests for health check endpoints."""
from fastapi.testclient import TestClient


def test_health_live(client: TestClient):
    """Test /health/live endpoint."""
    response = client.get("/health/live")
    
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_ready(client: TestClient):
    """Test /health/ready endpoint."""
    response = client.get("/health/ready")
    
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
