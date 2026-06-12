def test_register_user(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "password123", "full_name": "Test User"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "hashed_password" not in data

def test_register_duplicate_user(client):
    # Register first user
    client.post(
        "/api/v1/auth/register",
        json={"email": "duplicate@example.com", "password": "password123"}
    )
    # Register second user
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "duplicate@example.com", "password": "password456"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "A user with this email address already exists in the system."

def test_login_and_fetch_me(client):
    # Register
    client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "password123", "full_name": "Real User"}
    )
    # Login
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "user@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    
    # Get current user profile
    token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["email"] == "user@example.com"
    assert user_data["full_name"] == "Real User"

def test_invalid_login(client):
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "nonexistent@example.com", "password": "password123"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"
