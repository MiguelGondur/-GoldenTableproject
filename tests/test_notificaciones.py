"""Tests de HU-09 (REQ-FUNC-009): notificaciones push."""


def enviar(client, headers, tipo, cliente="cliente1", **extra):
    return client.post(
        "/notificaciones/enviar", json={"cliente_id": cliente, "tipo": tipo, **extra}, headers=headers
    )


def reservar(client, headers, mesa, hora, fecha="2030-05-20"):
    return client.post("/reservas", json={"mesa_id": mesa, "fecha": fecha, "hora": hora}, headers=headers)


def test_envio_con_mensaje_por_defecto_y_personalizado(client, h_gerente):
    r = enviar(client, h_gerente, "promocion")
    assert r.status_code == 201 and "promoción" in r.json()["mensaje"]
    r = enviar(client, h_gerente, "vencimiento_puntos", mensaje="Vencen mañana")
    assert r.json()["mensaje"] == "Vencen mañana"
    assert r.json()["canal"] == "push"


def test_historial_mas_reciente_primero(client, h_gerente, h_cliente1):
    enviar(client, h_gerente, "promocion")
    enviar(client, h_gerente, "reserva_proxima")
    hist = client.get("/notificaciones/cliente1", headers=h_cliente1).json()
    assert [n["tipo"] for n in hist[:2]] == ["reserva_proxima", "promocion"]
    assert hist[-1]["tipo"] == "promocion"  # la de bienvenida del seed


def test_tipo_invalido_y_cliente_inexistente(client, h_gerente):
    assert enviar(client, h_gerente, "spam").status_code == 422
    assert enviar(client, h_gerente, "promocion", cliente="nadie").status_code == 404


def test_cliente_no_envia_ni_ve_notificaciones_ajenas(client, h_cliente1, h_cliente2):
    assert enviar(client, h_cliente1, "promocion").status_code == 403
    assert client.get("/notificaciones/cliente2", headers=h_cliente1).status_code == 403


def test_promocion_bloqueada_para_autoexcluido(client, h_gerente, h_cliente1):
    client.post("/fidelidad/autoexclusion", json={"dias": 30}, headers=h_cliente1)
    assert enviar(client, h_gerente, "promocion").status_code == 409
    assert enviar(client, h_gerente, "vencimiento_puntos").status_code == 201


def test_recordatorio_de_reservas_proximas(client, h_cliente1, h_cliente2, h_anfitrion):
    reservar(client, h_cliente1, 1, "18:00")
    reservar(client, h_cliente2, 4, "19:00")

    url = "/notificaciones/reservas-proximas?horas=2&ahora=2030-05-20T16:30:00"
    r = client.post(url, headers=h_anfitrion)
    assert r.status_code == 200
    assert [n["cliente_id"] for n in r.json()] == ["cliente1"]
    assert "18:00" in r.json()[0]["mensaje"]

    assert client.post(url, headers=h_anfitrion).json() == []  # no se repite
    r = client.post("/notificaciones/reservas-proximas?horas=2&ahora=2030-05-20T17:30:00", headers=h_anfitrion)
    assert [n["cliente_id"] for n in r.json()] == ["cliente2"]


def test_recordatorio_otro_dia_y_sin_checkin(client, h_cliente1, h_anfitrion):
    reservar(client, h_cliente1, 1, "18:00", fecha="2030-05-21")
    out = client.post("/notificaciones/reservas-proximas?horas=24&ahora=2030-05-20T19:00:00", headers=h_anfitrion).json()
    assert "2030-05-21" in out[0]["mensaje"]


def test_recordatorio_excluye_reservas_con_checkin(client, h_cliente1, h_anfitrion):
    codigo = reservar(client, h_cliente1, 1, "18:00").json()["codigo_confirmacion"]
    client.post("/reservas/checkin", json={"codigo_confirmacion": codigo}, headers=h_anfitrion)
    out = client.post("/notificaciones/reservas-proximas?horas=3&ahora=2030-05-20T16:30:00", headers=h_anfitrion)
    assert out.json() == []


def test_recordatorio_solo_personal(client, h_cliente1):
    assert client.post("/notificaciones/reservas-proximas", headers=h_cliente1).status_code == 403
    assert client.post("/notificaciones/reservas-proximas?horas=0", headers=h_cliente1).status_code in (403, 422)


def test_recordatorio_sin_parametro_ahora(client, h_anfitrion):
    assert client.post("/notificaciones/reservas-proximas", headers=h_anfitrion).status_code == 200
