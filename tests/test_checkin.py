"""Tests de HU-03 (REQ-FUNC-003): check-in con el código de confirmación."""


def crear(client, headers):
    return client.post(
        "/reservas", json={"mesa_id": 2, "fecha": "2030-05-20", "hora": "18:00"}, headers=headers
    ).json()["codigo_confirmacion"]


def checkin(client, headers, codigo):
    return client.post("/reservas/checkin", json={"codigo_confirmacion": codigo}, headers=headers)


def test_checkin_exitoso(client, h_cliente1, h_anfitrion):
    codigo = crear(client, h_cliente1)
    r = checkin(client, h_anfitrion, codigo)
    assert r.status_code == 200
    assert r.json()["estado"] == "en_curso"
    assert r.json()["check_in_en"] is not None


def test_checkin_acepta_minusculas_y_espacios(client, h_cliente1, h_anfitrion):
    codigo = crear(client, h_cliente1)
    assert checkin(client, h_anfitrion, f" {codigo.lower()} ").status_code == 200


def test_checkin_codigo_inexistente_404(client, h_anfitrion):
    assert checkin(client, h_anfitrion, "ZZZZZZZZ").status_code == 404


def test_checkin_repetido_409(client, h_cliente1, h_anfitrion):
    codigo = crear(client, h_cliente1)
    checkin(client, h_anfitrion, codigo)
    assert checkin(client, h_anfitrion, codigo).status_code == 409


def test_solo_el_personal_hace_checkin(client, h_cliente1, h_cajero):
    codigo = crear(client, h_cliente1)
    assert checkin(client, h_cliente1, codigo).status_code == 403
    assert checkin(client, h_cajero, codigo).status_code == 403


def test_checkin_de_la_reserva_de_ejemplo(client, h_anfitrion):
    r = checkin(client, h_anfitrion, "DEMO0001")
    assert r.status_code == 200 and r.json()["cliente_id"] == "cliente2"
