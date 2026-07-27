from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

def test_health_check():
    resonse = client.get("/health")
    assert resonse.status_code == 200
    assert resonse.json() == {"status": "ok"}