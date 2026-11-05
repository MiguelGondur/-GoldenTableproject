"""
HU-06: el saldo se actualiza tras una recarga y se rechazan montos inválidos.
HU-07: se consulta el saldo actual y el historial (últimas 20 transacciones).
HU-08: la validación de saldo en caja responde si hay fondos suficientes.
HU-12: el reporte de transacciones se genera en CSV y filtra por fechas.
"""

import csv
import io


def recargar(client, headers, monto, metodo="tarjeta", **extra):
    return client.post(
        "/billetera/recarga", json={"monto": monto, "metodo_pago": metodo, **extra}, headers=headers
    )


def test_recarga_actualiza_saldo(client, nuevo_cliente):
    nombre, h = nuevo_cliente("recarga1")
    response = recargar(client, h, 50000)
    assert response.status_code == 200
    assert response.json() == {"cliente_id": nombre, "saldo": 50000}
    assert recargar(client, h, 10000).json()["saldo"] == 60000


def test_recarga_rechaza_monto_negativo_cero_y_medio_invalido(client, nuevo_cliente):
    _, h = nuevo_cliente("recarga2")
    assert recargar(client, h, -100).status_code == 422
    assert recargar(client, h, 0).status_code == 422
    assert recargar(client, h, 1000, metodo="bitcoin").status_code == 422


def test_recarga_en_caja_por_el_personal(client, nuevo_cliente, h_cajero):
    nombre, h = nuevo_cliente("recarga3")
    r = recargar(client, h_cajero, 20000, metodo="efectivo", cliente_id=nombre)
    assert r.status_code == 200 and r.json()["saldo"] == 20000
    assert recargar(client, h_cajero, 1000).status_code == 422  # falta cliente_id
    assert recargar(client, h_cajero, 1000, cliente_id="nadie").status_code == 404


def test_cliente_no_recarga_a_otro(client, h_cliente1):
    assert recargar(client, h_cliente1, 1000, cliente_id="cliente2").status_code == 403


def test_historial_muestra_saldo_y_transacciones(client, nuevo_cliente):
    nombre, h = nuevo_cliente("hist1")
    recargar(client, h, 20000)
    recargar(client, h, 30000, metodo="efectivo")

    response = client.get(f"/billetera/{nombre}", headers=h)
    assert response.status_code == 200
    data = response.json()
    assert data["saldo"] == 50000
    assert len(data["transacciones"]) == 2
    assert data["transacciones"][0]["monto"] == 30000  # la más reciente primero
    assert data["transacciones"][1]["monto"] == 20000


def test_historial_limita_a_20_transacciones(client, nuevo_cliente):
    nombre, h = nuevo_cliente("hist2")
    for _ in range(25):
        recargar(client, h, 1000)
    data = client.get(f"/billetera/{nombre}", headers=h).json()
    assert len(data["transacciones"]) == 20
    assert data["saldo"] == 25000


def test_historial_de_cliente_inexistente_404_y_ajeno_403(client, h_cliente1, h_cajero):
    assert client.get("/billetera/nadie", headers=h_cajero).status_code == 404
    assert client.get("/billetera/cliente2", headers=h_cliente1).status_code == 403


def test_validar_saldo_suficiente_e_insuficiente(client, h_cajero):
    ok = client.get("/billetera/validar", params={"cliente_id": "cliente1", "monto_requerido": 50000}, headers=h_cajero)
    assert ok.status_code == 200
    assert ok.json()["valido"] is True and ok.json()["saldo_disponible"] == 150000
    no = client.get("/billetera/validar", params={"cliente_id": "cliente2", "monto_requerido": 90000}, headers=h_cajero)
    assert no.json()["valido"] is False


def test_validar_cliente_sin_movimientos_da_saldo_cero(client, nuevo_cliente, h_cajero):
    nombre, _ = nuevo_cliente("sinmov")
    r = client.get("/billetera/validar", params={"cliente_id": nombre, "monto_requerido": 1000}, headers=h_cajero)
    assert r.status_code == 200
    assert r.json()["saldo_disponible"] == 0 and r.json()["valido"] is False


def test_validar_permisos(client, h_cliente1, h_anfitrion, h_cajero, h_gerente):
    assert client.get("/billetera/validar", params={"cliente_id": "cliente1"}, headers=h_anfitrion).status_code == 403
    assert client.get("/billetera/validar", params={"cliente_id": "cliente1"}, headers=h_gerente).status_code == 200
    assert client.get("/billetera/validar", headers=h_cajero).status_code == 422  # falta cliente_id
    assert client.get("/billetera/validar", params={"cliente_id": "nadie"}, headers=h_cajero).status_code == 404
    assert client.get("/billetera/validar", params={"cliente_id": "cliente2"}, headers=h_cliente1).status_code == 403
    propio = client.get("/billetera/validar", params={"monto_requerido": 1}, headers=h_cliente1)
    assert propio.status_code == 200 and propio.json()["cliente_id"] == "cliente1"


def test_reporte_se_genera_en_csv(client, nuevo_cliente, h_gerente):
    nombre, h = nuevo_cliente("rep1")
    recargar(client, h, 15000)

    response = client.get("/billetera/reportes", headers=h_gerente)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]

    filas = list(csv.reader(io.StringIO(response.text)))
    assert filas[0] == ["cliente_id", "tipo", "monto", "saldo_resultante", "fecha"]
    assert nombre in [fila[0] for fila in filas[1:]]
    assert "cliente1" in [fila[0] for fila in filas[1:]]  # datos de ejemplo


def test_reporte_filtra_por_rango_de_fechas(client, nuevo_cliente, h_gerente):
    _, h = nuevo_cliente("rep2")
    recargar(client, h, 5000)
    futuro = client.get("/billetera/reportes", params={"fecha_inicio": "2099-01-01"}, headers=h_gerente)
    assert len(list(csv.reader(io.StringIO(futuro.text)))) == 1  # solo el encabezado
    pasado = client.get("/billetera/reportes", params={"fecha_fin": "2000-01-01"}, headers=h_gerente)
    assert len(list(csv.reader(io.StringIO(pasado.text)))) == 1
    rango = client.get("/billetera/reportes", params={"fecha_inicio": "2000-01-01", "fecha_fin": "2099-01-01"}, headers=h_gerente)
    assert len(list(csv.reader(io.StringIO(rango.text)))) > 1


def test_reporte_solo_para_el_gerente(client, h_cliente1, h_cajero, h_anfitrion):
    for h in (h_cliente1, h_cajero, h_anfitrion):
        assert client.get("/billetera/reportes", headers=h).status_code == 403
