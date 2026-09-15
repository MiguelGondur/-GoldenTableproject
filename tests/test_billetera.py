"""
Test unitario de HU-06: valida que el saldo se actualice correctamente
tras una recarga y que se rechacen montos negativos o en cero.
"""

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_recarga_actualiza_saldo():
    response = client.post(
        "/billetera/recarga",
        json={"cliente_id": "cliente-test-1", "monto": 50000, "metodo_pago": "tarjeta"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["cliente_id"] == "cliente-test-1"
    assert data["saldo"] == 50000


def test_recarga_rechaza_monto_negativo():
    response = client.post(
        "/billetera/recarga",
        json={"cliente_id": "cliente-test-2", "monto": -100, "metodo_pago": "tarjeta"},
    )
    assert response.status_code == 422


def test_recarga_rechaza_monto_cero():
    response = client.post(
        "/billetera/recarga",
        json={"cliente_id": "cliente-test-3", "monto": 0, "metodo_pago": "tarjeta"},
    )
    assert response.status_code == 422
