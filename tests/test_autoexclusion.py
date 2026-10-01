"""
Test unitario de HU-11: valida que un cliente autoexcluido quede
bloqueado para seguir operando (acumulando puntos) durante el período
definido, según REQ-FUNC-011.
"""

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_autoexclusion_bloquea_acumulacion():
    client.post(
        "/fidelidad/autoexclusion",
        json={"cliente_id": "cliente-excluido-1", "dias": 30},
    )

    response = client.post(
        "/fidelidad/acumular",
        json={"cliente_id": "cliente-excluido-1", "monto_consumo": 10000},
    )
    assert response.status_code == 403


def test_cliente_sin_autoexclusion_opera_normal():
    response = client.post(
        "/fidelidad/acumular",
        json={"cliente_id": "cliente-libre-1", "monto_consumo": 10000},
    )
    assert response.status_code == 200
