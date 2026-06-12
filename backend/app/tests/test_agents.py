import pytest

@pytest.fixture
def auth_headers(client):
    # Register & Login to get token
    client.post(
        "/api/v1/auth/register",
        json={"email": "agent_owner@example.com", "password": "password123", "full_name": "Agent Master"}
    )
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "agent_owner@example.com", "password": "password123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_create_and_list_agent(client, auth_headers):
    agent_data = {
        "name": "SearchForge",
        "description": "Custom research persona",
        "system_prompt": "You are a professional crawler and summarizer.",
        "model_provider": "ollama",
        "model_name": "llama3:8b",
        "temperature": 0.3
    }
    
    # Create agent
    response = client.post("/api/v1/agents", json=agent_data, headers=auth_headers)
    assert response.status_code == 201
    created = response.json()
    assert created["name"] == "SearchForge"
    assert created["temperature"] == 0.3
    assert "id" in created
    
    # List agents
    list_response = client.get("/api/v1/agents", headers=auth_headers)
    assert list_response.status_code == 200
    agents_list = list_response.json()
    assert len(agents_list) >= 1
    assert any(a["name"] == "SearchForge" for a in agents_list)

def test_update_agent(client, auth_headers):
    # Create first
    agent_data = {
        "name": "CodeForge",
        "system_prompt": "You write Python code.",
        "model_name": "deepseek-coder:6.7b"
    }
    response = client.post("/api/v1/agents", json=agent_data, headers=auth_headers)
    agent_id = response.json()["id"]
    
    # Update temperature and name
    updated_data = {
        "name": "CodeForge v2",
        "system_prompt": "You write clean Python and JS.",
        "model_name": "deepseek-coder:6.7b",
        "temperature": 0.5
    }
    update_response = client.put(f"/api/v1/agents/{agent_id}", json=updated_data, headers=auth_headers)
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["name"] == "CodeForge v2"
    assert updated["temperature"] == 0.5

def test_delete_agent(client, auth_headers):
    # Create
    agent_data = {
        "name": "TempAgent",
        "system_prompt": "Delete me.",
        "model_name": "llama3:8b"
    }
    response = client.post("/api/v1/agents", json=agent_data, headers=auth_headers)
    agent_id = response.json()["id"]
    
    # Delete
    del_response = client.delete(f"/api/v1/agents/{agent_id}", headers=auth_headers)
    assert del_response.status_code == 204
    
    # Get details (should fail)
    get_response = client.get(f"/api/v1/agents/{agent_id}", headers=auth_headers)
    assert get_response.status_code == 404
