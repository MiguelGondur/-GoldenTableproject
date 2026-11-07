"""
Test de HU-01: valida el formato de respuesta y el tiempo de respuesta
(< 2s), según lo exigido por REQ-FUNC-001 y REQ-NFUNC-001.
"""

import time


def test_disponibilidad_formato_respuesta(client, h_cliente1):
    response = client.get(
        "/disponibilidad", params={"fecha": "2030-09-20", "hora": "18:00"}, headers=h_cliente1
    )
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list) and data
    for mesa in data:
        assert {"id", "capacidad", "estado", "horario"} <= set(mesa)
        assert mesa["estado"] == "disponible"
        assert mesa["horario"] == "18:00"


def test_disponibilidad_tiempo_respuesta(client, h_cliente1):
    inicio = time.time()
    response = client.get(
        "/disponibilidad", params={"fecha": "2030-09-20", "hora": "18:00"}, headers=h_cliente1
    )
    duracion = time.time() - inicio

    assert response.status_code == 200
    assert duracion < 2.0  # REQ-FUNC-001: tiempo de respuesta < 2 segundos


def test_no_muestra_mesas_reservadas_ni_ocupadas(client, h_cliente1):
    ids_18 = {m["id"] for m in client.get("/disponibilidad", params={"fecha": "2030-09-20", "hora": "18:00"}, headers=h_cliente1).json()}
    assert {1, 2, 7} <= ids_18
    ids_19 = {m["id"] for m in client.get("/disponibilidad", params={"fecha": "2030-09-20", "hora": "19:00"}, headers=h_cliente1).json()}
    assert 3 not in ids_19 and 4 in ids_19  # la mesa 3 está reservada
    ids_20 = {m["id"] for m in client.get("/disponibilidad", params={"fecha": "2030-09-20", "hora": "20:00"}, headers=h_cliente1).json()}
    assert 5 not in ids_20 and 6 in ids_20  # la mesa 5 está ocupada


def test_hora_sin_mesas_devuelve_lista_vacia(client, h_cliente1):
    r = client.get("/disponibilidad", params={"fecha": "2030-09-20", "hora": "03:00"}, headers=h_cliente1)
    assert r.status_code == 200 and r.json() == []


def test_parametros_invalidos_422(client, h_cliente1):
    assert client.get("/disponibilidad", params={"fecha": "2030-09-20", "hora": "25:99"}, headers=h_cliente1).status_code == 422
    assert client.get("/disponibilidad", params={"fecha": "no-es-fecha", "hora": "18:00"}, headers=h_cliente1).status_code == 422
    assert client.get("/disponibilidad", headers=h_cliente1).status_code == 422
