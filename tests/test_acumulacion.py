"""
HU-04 (REQ-FUNC-004): el consumo registrado en caja acredita puntos
automáticamente (1 punto por cada $1.000) y se refleja en el saldo del cliente.
"""


def test_acumulacion_se_refleja_en_el_saldo_del_cliente(client, nuevo_cliente, h_cajero):
    nombre, h = nuevo_cliente("acum1")
    r = client.post("/fidelidad/acumular", json={"cliente_id": nombre, "monto_gastado": 10000}, headers=h_cajero)
    assert r.status_code == 200
    assert r.json()["puntos_ganados"] == 10
    assert client.get(f"/fidelidad/puntos/{nombre}", headers=h).json()["puntos"] == 10


def test_acumulacion_tarda_menos_de_5_segundos(client, nuevo_cliente, h_cajero):
    import time

    nombre, _ = nuevo_cliente("acum2")
    inicio = time.time()
    r = client.post("/fidelidad/acumular", json={"cliente_id": nombre, "monto_gastado": 120000}, headers=h_cajero)
    assert r.status_code == 200 and time.time() - inicio < 5  # REQ-FUNC-004
