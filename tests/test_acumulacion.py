"""
Test unitario de HU-04: valida que el consumo registrado acredite
puntos automáticamente al cliente (1 punto por $1.000), según REQ-FUNC-004.
"""

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_acumulacion_acredita_puntos():
    response = client.post(
        "/fidelidad/acumular",
        json={"cliente_id": "cliente-acumula-1", "monto_gastado": 10000},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["puntos_ganados"] == 10
    assert data["puntos_totales"] == 10


def test_acumulacion_suma_sobre_puntos_existentes():
    for _ in range(2):
        response = client.post(
            "/fidelidad/acumular",
            json={"cliente_id": "cliente-acumula-2", "monto_gastado": 5000},
        )
    assert response.json()["puntos_totales"] == 10


def test_acumulacion_monto_invalido_rechazado():
    response = client.post(
        "/fidelidad/acumular", json={"cliente_id": "x", "monto_gastado": 0}
    )
    assert response.status_code == 422


def test_consultar_puntos_y_beneficios():
    assert client.get("/fidelidad/puntos/cliente-nuevo").json()["puntos"] == 0
    beneficios = client.get("/fidelidad/beneficios").json()
    assert beneficios["bebida_gratis"] == 50
