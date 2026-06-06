from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "User Friendly API is running 🚀"

def test_register():
    response = client.post("/auth/register", json={
        "name": "Test User",
        "email": "testjenkins@example.com",
        "password": "test123",
        "interests": ["tech"]
    })
    # 201 = created, 400 = already exists (both are fine)
    assert response.status_code in [201, 400]

def test_login_wrong_password():
    response = client.post("/auth/login", json={
        "email": "testjenkins@example.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401

def test_invalid_token():
    response = client.get("/auth/me", headers={
        "Authorization": "Bearer invalidtoken"
    })
    assert response.status_code == 401

def test_get_topics():
    response = client.get("/news/topics")
    assert response.status_code == 200
    assert "topics" in response.json()