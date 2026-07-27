from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

def test_health_check():
    resonse = client.get("/health")
    assert resonse.status_code == 200
    assert resonse.json() == {"status": "ok"}

def test_create_user_success():
    payload = {
        "username": "admin",
        "password": "123456",
    }

    res = client.post("/users", json=payload)
    assert res.status_code == 201

    data = res.json()
    assert data["username"] == "admin"
    assert data["password"] == "123456"
    assert "id" in data

