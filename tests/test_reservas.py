"""Tests de HU-02 (REQ-FUNC-002): reserva de mesa con código de confirmación único."""

FECHA = "2030-05-20"


def reservar(client, headers, mesa_id=1, hora="18:00", fecha=FECHA, **extra):
    return client.post(
        "/reservas",
        json={"mesa_id": mesa_id, "fecha": fecha, "hora": hora, **extra},
        headers=headers,
    )


def test_reserva_exitosa_devuelve_codigo(client, h_cliente1):
    r = reservar(client, h_cliente1)
    assert r.status_code == 201
    data = r.json()
    assert len(data["codigo_confirmacion"]) == 8
    assert data["estado"] == "confirmada"
    assert data["cliente_id"] == "cliente1"


def test_codigos_son_unicos(client, h_cliente1):
    codigos = {reservar(client, h_cliente1, mesa_id=m, hora=h).json()["codigo_confirmacion"]
               for m, h in [(1, "18:00"), (2, "18:00"), (4, "19:00"), (6, "20:00")]}
    assert len(codigos) == 4


def test_reserva_bloquea_mesa_solo_ese_dia(client, h_cliente1):
    reservar(client, h_cliente1)
    ids = lambda f: [m["id"] for m in client.get(f"/disponibilidad?fecha={f}&hora=18:00", headers=h_cliente1).json()]
    assert 1 not in ids(FECHA)
    assert 1 in ids("2030-05-21")


def test_doble_reserva_misma_mesa_rechazada(client, h_cliente1, h_cliente2):
    assert reservar(client, h_cliente1).status_code == 201
    r = reservar(client, h_cliente2)
    assert r.status_code == 409
    assert "reservada" in r.json()["detail"]


def test_mesa_inexistente_404(client, h_cliente1):
    assert reservar(client, h_cliente1, mesa_id=999).status_code == 404


def test_mesa_no_disponible_o_hora_distinta_409(client, h_cliente1):
    assert reservar(client, h_cliente1, mesa_id=5, hora="20:00").status_code == 409  # ocupada
    assert reservar(client, h_cliente1, mesa_id=3, hora="19:00").status_code == 409  # reservada
    assert reservar(client, h_cliente1, mesa_id=1, hora="19:00").status_code == 409  # otra franja


def test_hora_y_fecha_invalidas_422(client, h_cliente1):
    assert reservar(client, h_cliente1, hora="25:99").status_code == 422
    assert reservar(client, h_cliente1, fecha="2001-01-01").status_code == 422  # fecha pasada
    assert reservar(client, h_cliente1, fecha="no-es-fecha").status_code == 422


def test_cliente_no_puede_reservar_a_nombre_de_otro(client, h_cliente1):
    assert reservar(client, h_cliente1, cliente_id="cliente2").status_code == 403
    assert reservar(client, h_cliente1, cliente_id="cliente1").status_code == 201


def test_personal_reserva_para_un_cliente(client, h_anfitrion):
    r = reservar(client, h_anfitrion, cliente_id="cliente2")
    assert r.status_code == 201 and r.json()["cliente_id"] == "cliente2"
    assert reservar(client, h_anfitrion, mesa_id=2).status_code == 422  # falta cliente_id
    assert reservar(client, h_anfitrion, mesa_id=2, cliente_id="nadie").status_code == 404


def test_listar_reservas_del_dia_ordenadas_por_hora(client, h_cliente1, h_anfitrion):
    reservar(client, h_cliente1, mesa_id=4, hora="19:00")
    reservar(client, h_cliente1)
    lista = client.get(f"/reservas?fecha={FECHA}", headers=h_anfitrion).json()
    assert [r["hora"] for r in lista] == ["18:00", "19:00"]
    assert len(client.get("/reservas", headers=h_anfitrion).json()) >= 2
    assert client.get("/reservas?fecha=2031-01-01", headers=h_anfitrion).json() == []


def test_cliente_no_ve_la_lista_del_anfitrion(client, h_cliente1):
    assert client.get("/reservas", headers=h_cliente1).status_code == 403


def test_mis_reservas_y_consulta_por_codigo(client, h_cliente1, h_cliente2, h_anfitrion):
    codigo = reservar(client, h_cliente1).json()["codigo_confirmacion"]
    mias = client.get("/reservas/mias", headers=h_cliente1).json()
    assert [r["codigo_confirmacion"] for r in mias] == [codigo]
    # cliente2 solo tiene la reserva de ejemplo
    assert [r["codigo_confirmacion"] for r in client.get("/reservas/mias", headers=h_cliente2).json()] == ["DEMO0001"]
    assert client.get(f"/reservas/{codigo.lower()}", headers=h_cliente1).status_code == 200
    assert client.get(f"/reservas/{codigo}", headers=h_anfitrion).status_code == 200
    assert client.get(f"/reservas/{codigo}", headers=h_cliente2).status_code == 403
    assert client.get("/reservas/NOEXISTE", headers=h_cliente1).status_code == 404
    assert client.get("/reservas/mias", headers=h_anfitrion).status_code == 403
