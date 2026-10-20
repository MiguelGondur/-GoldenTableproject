"""Tests de HU-09 (REQ-FUNC-009): notificaciones push."""

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def enviar(tipo, cliente="ana", **extra):
    return client.post("/notificaciones/enviar", json={"cliente_id": cliente, "tipo": tipo, **extra})


def test_envio_con_mensaje_por_defecto_y_personalizado():
    r = enviar("promocion")
    assert r.status_code == 201 and "promoción" in r.json()["mensaje"]
    r = enviar("vencimiento_puntos", mensaje="Vencen mañana")
    assert r.json()["mensaje"] == "Vencen mañana"
    assert r.json()["canal"] == "push"


def test_historial_mas_reciente_primero():
    enviar("promocion")
    enviar("reserva_proxima")
    hist = client.get("/notificaciones/ana").json()
    assert [n["tipo"] for n in hist] == ["reserva_proxima", "promocion"]
    assert client.get("/notificaciones/otro").json() == []


def test_tipo_invalido_422():
    assert enviar("spam").status_code == 422


def test_promocion_bloqueada_para_autoexcluido():
    client.post("/fidelidad/autoexclusion", json={"cliente_id": "ana", "dias": 30})
    assert enviar("promocion").status_code == 409
    assert enviar("vencimiento_puntos").status_code == 201


def test_recordatorio_de_reservas_proximas():
    client.post("/reservas", json={"cliente_id": "ana", "mesa_id": 1, "fecha": "2030-05-20", "hora": "18:00"})
    client.post("/reservas", json={"cliente_id": "beto", "mesa_id": 4, "fecha": "2030-05-20", "hora": "19:00"})

    r = client.post("/notificaciones/reservas-proximas?horas=2&ahora=2030-05-20T16:30:00")
    assert r.status_code == 200
    assert [n["cliente_id"] for n in r.json()] == ["ana"]
    assert "18:00" in r.json()[0]["mensaje"]

    # No se repite el recordatorio
    assert client.post("/notificaciones/reservas-proximas?horas=2&ahora=2030-05-20T16:30:00").json() == []
    # La reserva de las 19:00 entra en una ventana posterior
    r = client.post("/notificaciones/reservas-proximas?horas=2&ahora=2030-05-20T17:30:00")
    assert [n["cliente_id"] for n in r.json()] == ["beto"]


def test_recordatorio_dia_distinto_y_checkin_excluido():
    c = client.post("/reservas", json={"cliente_id": "ana", "mesa_id": 1, "fecha": "2030-05-21", "hora": "00:00"})
    # mesa 1 es de 18:00, así que esa reserva falla: usamos mesa válida
    r = client.post("/reservas", json={"cliente_id": "ana", "mesa_id": 1, "fecha": "2030-05-21", "hora": "18:00"})
    codigo = r.json()["codigo_confirmacion"]
    client.post("/reservas/checkin", json={"codigo_confirmacion": codigo})
    out = client.post("/notificaciones/reservas-proximas?horas=24&ahora=2030-05-20T19:00:00")
    assert out.json() == []  # ya hizo check-in
    assert c.status_code == 409


def test_recordatorio_mensaje_otro_dia():
    client.post("/reservas", json={"cliente_id": "ana", "mesa_id": 1, "fecha": "2030-05-21", "hora": "18:00"})
    out = client.post("/notificaciones/reservas-proximas?horas=24&ahora=2030-05-20T19:00:00").json()
    assert "2030-05-21" in out[0]["mensaje"]
