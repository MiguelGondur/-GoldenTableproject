"""
HU-06: valida que el saldo se actualice correctamente tras una recarga y
que se rechacen montos negativos o en cero.

HU-07: valida que se pueda consultar el saldo actual y el historial de
transacciones de un cliente.

HU-08: valida que la validación de saldo en caja responda correctamente
si el cliente tiene o no fondos suficientes para una operación.

HU-12: valida que el reporte de transacciones se genere en CSV y que el
filtro por fechas funcione correctamente.
"""

import csv
import io

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_recarga_actualiza_saldo():
    response = client.post(
        "/billetera/recarga",
        json={"cliente_id": "cliente-test-1", "monto": 50000, "metodo_pago": "tarjeta"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["cliente_id"] == "cliente-test-1"
    assert data["saldo"] == 50000


def test_recarga_rechaza_monto_negativo():
    response = client.post(
        "/billetera/recarga",
        json={"cliente_id": "cliente-test-2", "monto": -100, "metodo_pago": "tarjeta"},
    )
    assert response.status_code == 422


def test_recarga_rechaza_monto_cero():
    response = client.post(
        "/billetera/recarga",
        json={"cliente_id": "cliente-test-3", "monto": 0, "metodo_pago": "tarjeta"},
    )
    assert response.status_code == 422


def test_historial_muestra_saldo_y_transacciones():
    client.post(
        "/billetera/recarga",
        json={"cliente_id": "cliente-test-6", "monto": 20000, "metodo_pago": "tarjeta"},
    )
    client.post(
        "/billetera/recarga",
        json={"cliente_id": "cliente-test-6", "monto": 30000, "metodo_pago": "efectivo"},
    )

    response = client.get("/billetera/cliente-test-6")
    assert response.status_code == 200

    data = response.json()
    assert data["saldo"] == 50000
    assert len(data["transacciones"]) == 2
    # La más reciente va primero
    assert data["transacciones"][0]["monto"] == 30000
    assert data["transacciones"][1]["monto"] == 20000


def test_historial_limita_a_20_transacciones():
    cliente_id = "cliente-test-muchas-recargas"
    for _ in range(25):
        client.post(
            "/billetera/recarga",
            json={"cliente_id": cliente_id, "monto": 1000, "metodo_pago": "tarjeta"},
        )

    response = client.get(f"/billetera/{cliente_id}")
    assert response.status_code == 200
    assert len(response.json()["transacciones"]) == 20


def test_historial_cliente_sin_billetera_da_404():
    response = client.get("/billetera/cliente-que-no-existe")
    assert response.status_code == 404


def test_validar_saldo_suficiente():
    # Primero recargamos para tener saldo real
    client.post(
        "/billetera/recarga",
        json={"cliente_id": "cliente-test-4", "monto": 100000, "metodo_pago": "efectivo"},
    )
    response = client.get(
        "/billetera/validar",
        params={"cliente_id": "cliente-test-4", "monto_requerido": 50000},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valido"] is True
    assert data["saldo_disponible"] == 100000


def test_validar_saldo_insuficiente():
    client.post(
        "/billetera/recarga",
        json={"cliente_id": "cliente-test-5", "monto": 10000, "metodo_pago": "efectivo"},
    )
    response = client.get(
        "/billetera/validar",
        params={"cliente_id": "cliente-test-5", "monto_requerido": 50000},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valido"] is False


def test_validar_cliente_sin_registro_no_falla():
    # Un cliente que nunca ha recargado debe dar saldo 0, no un error 404/500
    response = client.get(
        "/billetera/validar",
        params={"cliente_id": "cliente-inexistente", "monto_requerido": 1000},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["saldo_disponible"] == 0
    assert data["valido"] is False


def test_reporte_se_genera_en_csv():
    client.post(
        "/billetera/recarga",
        json={"cliente_id": "cliente-reporte-1", "monto": 15000, "metodo_pago": "tarjeta"},
    )

    response = client.get("/billetera/reportes")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]

    filas = list(csv.reader(io.StringIO(response.text)))
    encabezado = filas[0]
    assert encabezado == ["cliente_id", "tipo", "monto", "saldo_resultante", "fecha"]

    # Debe existir al menos una fila con la recarga que acabamos de hacer
    clientes_en_reporte = [fila[0] for fila in filas[1:]]
    assert "cliente-reporte-1" in clientes_en_reporte


def test_reporte_filtra_por_fecha_futura_da_vacio():
    client.post(
        "/billetera/recarga",
        json={"cliente_id": "cliente-reporte-2", "monto": 5000, "metodo_pago": "tarjeta"},
    )

    # Una fecha de inicio en el futuro no debe traer ninguna transacción
    response = client.get(
        "/billetera/reportes", params={"fecha_inicio": "2099-01-01"}
    )
    assert response.status_code == 200
    filas = list(csv.reader(io.StringIO(response.text)))
    assert len(filas) == 1  # solo queda el encabezado, sin filas de datos
