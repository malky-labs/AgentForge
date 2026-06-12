import pytest
from fastapi import status

@pytest.fixture
def auth_headers(client):
    # Register & Login to get token
    client.post(
        "/api/v1/auth/register",
        json={"email": "foundation_tester@example.com", "password": "password123", "full_name": "Foundation Tester"}
    )
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "foundation_tester@example.com", "password": "password123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_health_check_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "database" in data["components"]

def test_metrics_endpoint(client):
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "metrics" in data
    assert "users_total" in data["metrics"]

def test_rate_limiter_throttling(client, auth_headers):
    from app.core.config import settings
    original_limit = settings.RATE_LIMIT_LIMIT
    settings.RATE_LIMIT_LIMIT = 3
    
    headers = {**auth_headers, "x-force-rate-limit": "true"}
    
    # First 3 calls should pass successfully (authenticated)
    for _ in range(3):
         response = client.get("/api/v1/auth/me", headers=headers)
         assert response.status_code == 200
         
    # 4th call should trigger rate limiter (429)
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 429
    data = response.json()
    assert data["type"] == "RateLimitExceeded"
    
    # Reset limit
    settings.RATE_LIMIT_LIMIT = original_limit

def test_global_exception_handler(client, auth_headers):
    # Access a route with invalid uuid parameter to trigger validation error
    response = client.get("/api/v1/agents/invalid-uuid", headers=auth_headers)
    assert response.status_code == 422
    data = response.json()
    assert data["type"] == "RequestValidationError"
    assert "detail" in data
