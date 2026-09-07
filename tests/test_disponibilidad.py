"""
Test unitario de HU-01: valida el formato de respuesta y el tiempo de
respuesta (< 2s), según lo exigido por REQ-FUNC-001.
"""

import time

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_disponibilidad_formato_respuesta():
    response = client.get("/disponibilidad", params={"fecha": "2026-09-20", "hora": "18:00"})
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    for mesa in data:
        assert "id" in mesa
        assert "capacidad" in mesa
        assert "estado" in mesa
        assert "horario" in mesa
        assert mesa["estado"] == "disponible"


def test_disponibilidad_tiempo_respuesta():
    inicio = time.time()
    response = client.get("/disponibilidad", params={"fecha": "2026-09-20", "hora": "18:00"})
    duracion = time.time() - inicio

    assert response.status_code == 200
    assert duracion < 2.0  # REQ-FUNC-001: tiempo de respuesta < 2 segundos
