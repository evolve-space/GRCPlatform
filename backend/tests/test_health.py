from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_responde_ok():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["servicio"] == "GRCPlatform"


def test_health_responde_200():
    response = client.get("/health")
    assert response.status_code == 200
    assert "estado" in response.json()
