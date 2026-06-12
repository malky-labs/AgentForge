import pytest
import json

@pytest.fixture
def auth_headers(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "wf_owner@example.com", "password": "password123", "full_name": "Workflow Architect"}
    )
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "wf_owner@example.com", "password": "password123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def active_agent(client, auth_headers):
    agent_data = {
        "name": "StoryForge",
        "description": "Writes interesting stories",
        "system_prompt": "You are a creative writer.",
        "model_provider": "ollama",
        "model_name": "llama3:8b",
        "temperature": 0.8
    }
    response = client.post("/api/v1/agents", json=agent_data, headers=auth_headers)
    return response.json()

def test_create_and_list_workflow(client, auth_headers, active_agent):
    agent_id = active_agent["id"]
    
    # Define a clean DAG graph structure with 1 node
    graph_data = {
        "nodes": [
            {
                "id": "node-1",
                "type": "agentNode",
                "data": {"name": "Writer", "agentId": agent_id, "prompt": "Write a 1-sentence tale about a galaxy."}
            }
        ],
        "edges": []
    }
    
    wf_payload = {
        "name": "Galaxy Story Generator",
        "description": "Streams a short sci-fi sentence",
        "graph_json": json.dumps(graph_data)
    }
    
    # Create workflow
    response = client.post("/api/v1/workflows", json=wf_payload, headers=auth_headers)
    assert response.status_code == 201
    created = response.json()
    assert created["name"] == "Galaxy Story Generator"
    assert "id" in created
    
    # List workflows
    list_response = client.get("/api/v1/workflows", headers=auth_headers)
    assert list_response.status_code == 200
    workflows = list_response.json()
    assert len(workflows) >= 1
    assert any(w["name"] == "Galaxy Story Generator" for w in workflows)

def test_execute_workflow_trigger(client, auth_headers, active_agent):
    agent_id = active_agent["id"]
    
    # Define simple DAG graph structure
    graph_data = {
        "nodes": [
            {
                "id": "writer-1",
                "type": "agentNode",
                "data": {"name": "Scifi Writer", "agentId": agent_id, "prompt": "Create a space tagline."}
            }
        ],
        "edges": []
    }
    
    # Save workflow blueprint
    wf_response = client.post(
        "/api/v1/workflows",
        json={
            "name": "Trigger Test",
            "graph_json": json.dumps(graph_data)
        },
        headers=auth_headers
    )
    wf_id = wf_response.json()["id"]
    
    # Trigger run
    run_response = client.post(f"/api/v1/workflows/{wf_id}/execute", headers=auth_headers)
    assert run_response.status_code == 202
    exec_data = run_response.json()
    assert exec_data["state"] in ["pending", "running", "completed"]
    assert exec_data["workflow_id"] == wf_id
    
    # Fetch executions history
    history_response = client.get(f"/api/v1/workflows/{wf_id}/executions", headers=auth_headers)
    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history) >= 1
    assert history[0]["id"] == exec_data["id"]
