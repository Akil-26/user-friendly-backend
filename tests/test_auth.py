from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

with patch('sqlalchemy.sql.schema.MetaData.create_all', MagicMock()):
    from app.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "User Friendly API is running 🚀"

def test_invalid_token():
    response = client.get("/auth/me", headers={
        "Authorization": "Bearer invalidtoken"
    })
    assert response.status_code == 401

def test_unauthorized_news_feed():
    response = client.get("/news/feed")
    assert response.status_code == 401

def test_unauthorized_chat():
    response = client.post("/chat/ask", json={
        "article_url": "https://example.com",
        "question": "What is this about?"
    })
    assert response.status_code == 401

def test_get_topics():
    response = client.get("/news/topics")
    assert response.status_code == 200
    assert "topics" in response.json()