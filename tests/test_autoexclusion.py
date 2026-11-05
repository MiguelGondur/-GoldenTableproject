"""
Tests de HU-11 (REQ-FUNC-011): un cliente autoexcluido queda bloqueado en
toda la plataforma durante el periodo definido y no puede acortarlo.
"""

from datetime import timedelta

from src.api import orm
from src.api.db import SessionLocal
from src.api.tiempo import hoy_casino


def excluir(client, headers, dias=30):
    return client.post("/fidelidad/autoexclusion", json={"dias": dias}, headers=headers)


def test_autoexclusion_bloquea_acumulacion(client, h_cliente1, h_cajero):
    assert excluir(client, h_cliente1).status_code == 200
    r = client.post("/fidelidad/acumular", json={"cliente_id": "cliente1", "monto_gastado": 10000}, headers=h_cajero)
    assert r.status_code == 403


def test_autoexclusion_bloquea_canje_gasto_recarga_y_reserva(client, h_cliente1):
    excluir(client, h_cliente1)
    assert client.post("/fidelidad/canjear", json={"beneficio": "bebida_gratis"}, headers=h_cliente1).status_code == 403
    assert client.post("/fidelidad/gasto", json={"monto": 10}, headers=h_cliente1).status_code == 403
    assert client.post("/billetera/recarga", json={"monto": 100, "metodo_pago": "tarjeta"}, headers=h_cliente1).status_code == 403
    r = client.post("/reservas", json={"mesa_id": 1, "fecha": "2030-01-01", "hora": "18:00"}, headers=h_cliente1)
    assert r.status_code == 403


def test_cliente_sin_autoexclusion_opera_normal(client, h_cliente2, h_cajero):
    r = client.post("/fidelidad/acumular", json={"cliente_id": "cliente2", "monto_gastado": 10000}, headers=h_cajero)
    assert r.status_code == 200
    assert client.post("/fidelidad/gasto", json={"monto": 10}, headers=h_cliente2).status_code == 200


def test_autoexclusion_no_se_puede_acortar(client, h_cliente1):
    primera = excluir(client, h_cliente1, dias=100).json()["bloqueado_hasta"]
    segunda = excluir(client, h_cliente1, dias=5).json()["bloqueado_hasta"]
    assert primera == segunda


def test_autoexclusion_puede_ampliarse(client, h_cliente1):
    excluir(client, h_cliente1, dias=10)
    nueva = excluir(client, h_cliente1, dias=60).json()["bloqueado_hasta"]
    assert nueva == (hoy_casino() + timedelta(days=60)).isoformat()


def test_consultar_estado_autoexclusion(client, h_cliente1, h_gerente):
    assert client.get("/fidelidad/autoexclusion/cliente1", headers=h_cliente1).json()["activa"] is False
    excluir(client, h_cliente1)
    estado = client.get("/fidelidad/autoexclusion/cliente1", headers=h_gerente).json()
    assert estado["activa"] is True and estado["bloqueado_hasta"] is not None


def test_autoexclusion_vencida_libera_al_cliente(client, h_cliente1, h_cajero):
    with SessionLocal() as db:
        db.add(orm.Autoexclusion(cliente_id="cliente1", fecha_fin=hoy_casino() - timedelta(days=1)))
        db.commit()
    r = client.post("/fidelidad/acumular", json={"cliente_id": "cliente1", "monto_gastado": 1000}, headers=h_cajero)
    assert r.status_code == 200
    assert client.get("/fidelidad/autoexclusion/cliente1", headers=h_cliente1).json()["activa"] is False


def test_dias_invalidos_rechazados(client, h_cliente1):
    assert excluir(client, h_cliente1, dias=0).status_code == 422
    assert excluir(client, h_cliente1, dias=4000).status_code == 422


def test_solo_el_cliente_se_autoexcluye(client, h_cajero, h_gerente):
    assert excluir(client, h_cajero).status_code == 403
    assert excluir(client, h_gerente).status_code == 403
