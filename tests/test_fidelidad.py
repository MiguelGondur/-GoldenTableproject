"""
HU-04: se acumulan puntos según el monto de la transacción y se suman a los previos.
HU-05: canje de puntos por beneficios del catálogo.
HU-11: se respeta el límite diario de gasto.
"""


def acumular(client, headers, cliente, monto):
    return client.post("/fidelidad/acumular", json={"cliente_id": cliente, "monto_gastado": monto}, headers=headers)


def test_acumular_puntos_primera_vez(client, nuevo_cliente, h_cajero):
    nombre, _ = nuevo_cliente("fid1")
    response = acumular(client, h_cajero, nombre, 5000)
    assert response.status_code == 200
    data = response.json()
    assert data["puntos_ganados"] == 5 and data["puntos_totales"] == 5


def test_acumular_puntos_se_suman_a_los_anteriores(client, nuevo_cliente, h_cajero):
    nombre, _ = nuevo_cliente("fid2")
    acumular(client, h_cajero, nombre, 3000)
    response = acumular(client, h_cajero, nombre, 2000)
    assert response.status_code == 200
    assert response.json()["puntos_totales"] == 5


def test_acumular_rechaza_monto_cero_o_negativo(client, nuevo_cliente, h_cajero):
    nombre, _ = nuevo_cliente("fid3")
    assert acumular(client, h_cajero, nombre, 0).status_code == 422
    assert acumular(client, h_cajero, nombre, -5).status_code == 422


def test_acumular_cliente_inexistente_404(client, h_cajero):
    assert acumular(client, h_cajero, "nadie", 5000).status_code == 404
    assert acumular(client, h_cajero, "cajero", 5000).status_code == 404  # el personal no acumula


def test_acumular_menos_de_mil_pesos_no_da_puntos(client, nuevo_cliente, h_cajero):
    nombre, _ = nuevo_cliente("fid3b")
    assert acumular(client, h_cajero, nombre, 999).json()["puntos_ganados"] == 0


def test_solo_caja_acumula_puntos(client, nuevo_cliente, h_cliente1, h_anfitrion, h_gerente):
    nombre, _ = nuevo_cliente("fid3c")
    assert acumular(client, h_cliente1, nombre, 5000).status_code == 403  # no se auto-acredita
    assert acumular(client, h_anfitrion, nombre, 5000).status_code == 403
    assert acumular(client, h_gerente, nombre, 5000).status_code == 200


def test_consultar_puntos_y_beneficios(client, h_cliente1, h_cliente2, h_cajero):
    assert client.get("/fidelidad/puntos/cliente1", headers=h_cliente1).json()["puntos"] == 500
    assert client.get("/fidelidad/puntos/cliente1", headers=h_cajero).json()["puntos"] == 500
    assert client.get("/fidelidad/puntos/cliente1", headers=h_cliente2).status_code == 403
    assert client.get("/fidelidad/puntos/nadie", headers=h_cajero).status_code == 404
    beneficios = client.get("/fidelidad/beneficios", headers=h_cliente1).json()
    assert beneficios == {"bebida_gratis": 50, "entrada_evento": 150, "cena_vip": 300, "noche_hotel": 500}


def test_canjear_beneficio_con_puntos_suficientes(client, nuevo_cliente, h_cajero):
    nombre, h = nuevo_cliente("fid4")
    acumular(client, h_cajero, nombre, 100000)  # 100 puntos
    response = client.post("/fidelidad/canjear", json={"beneficio": "bebida_gratis"}, headers=h)  # cuesta 50
    assert response.status_code == 200
    data = response.json()
    assert data["puntos_usados"] == 50 and data["puntos_restantes"] == 50
    assert len(data["cupon"]) == 8


def test_cada_canje_genera_un_cupon_distinto(client, h_cliente1):
    c1 = client.post("/fidelidad/canjear", json={"beneficio": "bebida_gratis"}, headers=h_cliente1).json()["cupon"]
    c2 = client.post("/fidelidad/canjear", json={"beneficio": "bebida_gratis"}, headers=h_cliente1).json()["cupon"]
    assert c1 != c2
    assert client.get("/fidelidad/puntos/cliente1", headers=h_cliente1).json()["puntos"] == 400


def test_canjear_rechaza_puntos_insuficientes(client, nuevo_cliente, h_cajero):
    nombre, h = nuevo_cliente("fid5")
    acumular(client, h_cajero, nombre, 10000)  # 10 puntos
    response = client.post("/fidelidad/canjear", json={"beneficio": "cena_vip"}, headers=h)  # cuesta 300
    assert response.status_code == 402
    # el saldo no cambia tras un canje rechazado
    assert client.get(f"/fidelidad/puntos/{nombre}", headers=h).json()["puntos"] == 10


def test_canjear_beneficio_inexistente_da_404(client, h_cliente1):
    r = client.post("/fidelidad/canjear", json={"beneficio": "algo_que_no_existe"}, headers=h_cliente1)
    assert r.status_code == 404


def test_cliente_no_canjea_puntos_de_otro(client, h_cliente1):
    r = client.post("/fidelidad/canjear", json={"cliente_id": "cliente2", "beneficio": "bebida_gratis"}, headers=h_cliente1)
    assert r.status_code == 403


def test_personal_canjea_a_nombre_del_cliente(client, h_cajero):
    r = client.post("/fidelidad/canjear", json={"cliente_id": "cliente1", "beneficio": "bebida_gratis"}, headers=h_cajero)
    assert r.status_code == 200 and r.json()["puntos_restantes"] == 450


def test_definir_limite_diario(client, h_cliente1):
    response = client.post("/fidelidad/limite", json={"limite_diario": 50000}, headers=h_cliente1)
    assert response.status_code == 200
    assert response.json()["limite_diario"] == 50000
    # se puede actualizar
    assert client.post("/fidelidad/limite", json={"limite_diario": 70000}, headers=h_cliente1).json()["limite_diario"] == 70000
    assert client.post("/fidelidad/limite", json={"limite_diario": 0}, headers=h_cliente1).status_code == 422


def test_gasto_permitido_dentro_del_limite(client, h_cliente1):
    client.post("/fidelidad/limite", json={"limite_diario": 100000}, headers=h_cliente1)
    response = client.post("/fidelidad/gasto", json={"monto": 40000}, headers=h_cliente1)
    assert response.status_code == 200
    data = response.json()
    assert data["permitido"] is True and data["gastado_hoy"] == 40000


def test_gasto_rechazado_al_superar_el_limite(client, h_cliente1):
    client.post("/fidelidad/limite", json={"limite_diario": 50000}, headers=h_cliente1)
    client.post("/fidelidad/gasto", json={"monto": 40000}, headers=h_cliente1)
    response = client.post("/fidelidad/gasto", json={"monto": 30000}, headers=h_cliente1)
    assert response.status_code == 200
    data = response.json()
    assert data["permitido"] is False
    assert data["gastado_hoy"] == 40000  # el gasto rechazado no queda registrado
    # lo que sí cabe, se sigue aceptando
    assert client.post("/fidelidad/gasto", json={"monto": 10000}, headers=h_cliente1).json()["permitido"] is True


def test_gasto_sin_limite_definido_se_permite(client, h_cliente1):
    response = client.post("/fidelidad/gasto", json={"monto": 999999}, headers=h_cliente1)
    assert response.status_code == 200
    assert response.json()["permitido"] is True
    assert response.json()["limite_diario"] is None
