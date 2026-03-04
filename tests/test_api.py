import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_summarize_invalid_url():
    response = client.post("/summarize", json={"github_url": "not-a-url"})
    assert response.status_code == 422
    data = response.json()
    assert data["status"] == "error"

def test_summarize_missing_key():
    # Will fail 500 without a real API key configured in env
    response = client.post("/summarize", json={"github_url": "https://github.com/psf/requests"})
    assert response.status_code == 500
    data = response.json()
    assert data["status"] == "error"
    assert "Neither NEBIUS_API_KEY nor OPENAI_API_KEY" in data["message"]
