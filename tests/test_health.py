"""
Prueba unitaria de ejemplo para el endpoint de salud.
Sirve como base para la cobertura de pruebas exigida en REQ-NFUNC-006 (> 80%).
"""

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
