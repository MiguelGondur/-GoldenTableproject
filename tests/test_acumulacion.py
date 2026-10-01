"""
Test unitario de HU-04: valida que el consumo registrado acredite
puntos automáticamente al cliente, según REQ-FUNC-004.
"""

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_acumulacion_acredita_puntos():
    response = client.post(
        "/fidelidad/acumular",
        json={"cliente_id": "cliente-acumula-1", "monto_consumo": 10000},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["puntos_acreditados"] == 100  # 10000 * 0.01
    assert data["puntos_totales"] == 100


def test_acumulacion_suma_sobre_puntos_existentes():
    client.post(
        "/fidelidad/acumular",
        json={"cliente_id": "cliente-acumula-2", "monto_consumo": 5000},
    )
    response = client.post(
        "/fidelidad/acumular",
        json={"cliente_id": "cliente-acumula-2", "monto_consumo": 5000},
    )

    data = response.json()
    assert data["puntos_totales"] == 100  # 50 + 50
