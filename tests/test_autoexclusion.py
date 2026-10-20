"""
Tests de HU-11 (REQ-FUNC-011): un cliente autoexcluido queda bloqueado en
toda la plataforma durante el periodo definido y no puede acortarlo.
"""

from datetime import date, timedelta

from fastapi.testclient import TestClient

from src.api.main import app
from src.api.store import AUTOEXCLUSION_DB

client = TestClient(app)
CLIENTE = "cliente-excluido-1"


def excluir(dias=30, cliente=CLIENTE):
    return client.post("/fidelidad/autoexclusion", json={"cliente_id": cliente, "dias": dias})


def test_autoexclusion_bloquea_acumulacion():
    assert excluir().status_code == 200
    r = client.post("/fidelidad/acumular", json={"cliente_id": CLIENTE, "monto_gastado": 10000})
    assert r.status_code == 403


def test_autoexclusion_bloquea_canje_gasto_y_recarga():
    excluir()
    assert client.post("/fidelidad/canjear", json={"cliente_id": CLIENTE, "beneficio": "bebida_gratis"}).status_code == 403
    assert client.post("/fidelidad/gasto", json={"cliente_id": CLIENTE, "monto": 10}).status_code == 403
    assert client.post("/billetera/recarga", json={"cliente_id": CLIENTE, "monto": 100, "metodo_pago": "tarjeta"}).status_code == 403


def test_cliente_sin_autoexclusion_opera_normal():
    r = client.post("/fidelidad/acumular", json={"cliente_id": "cliente-libre-1", "monto_gastado": 10000})
    assert r.status_code == 200


def test_autoexclusion_no_se_puede_acortar():
    primera = excluir(dias=100).json()["bloqueado_hasta"]
    segunda = excluir(dias=5).json()["bloqueado_hasta"]
    assert primera == segunda


def test_autoexclusion_puede_ampliarse():
    excluir(dias=10)
    nueva = excluir(dias=60).json()["bloqueado_hasta"]
    assert nueva == (date.today() + timedelta(days=60)).isoformat()


def test_consultar_estado_autoexclusion():
    assert client.get(f"/fidelidad/autoexclusion/{CLIENTE}").json()["activa"] is False
    excluir()
    estado = client.get(f"/fidelidad/autoexclusion/{CLIENTE}").json()
    assert estado["activa"] is True and estado["bloqueado_hasta"] is not None


def test_autoexclusion_vencida_libera_al_cliente():
    AUTOEXCLUSION_DB[CLIENTE] = date.today() - timedelta(days=1)
    r = client.post("/fidelidad/acumular", json={"cliente_id": CLIENTE, "monto_gastado": 1000})
    assert r.status_code == 200
    assert client.get(f"/fidelidad/autoexclusion/{CLIENTE}").json()["activa"] is False


def test_dias_invalidos_rechazados():
    assert excluir(dias=0).status_code == 422
