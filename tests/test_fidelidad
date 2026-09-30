"""
HU-04: valida que se acumulen puntos correctamente según el monto de la
transacción, y que se sumen a los puntos previos del cliente.

HU-05: valida el canje de puntos por beneficios del catálogo.

HU-11: valida que el límite diario de autoexclusión se respete.
"""

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_acumular_puntos_primera_vez():
    response = client.post(
        "/fidelidad/acumular",
        json={"cliente_id": "cliente-fid-1", "monto_gastado": 5000},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["puntos_ganados"] == 5
    assert data["puntos_totales"] == 5


def test_acumular_puntos_se_suman_a_los_anteriores():
    client.post(
        "/fidelidad/acumular",
        json={"cliente_id": "cliente-fid-2", "monto_gastado": 3000},
    )
    response = client.post(
        "/fidelidad/acumular",
        json={"cliente_id": "cliente-fid-2", "monto_gastado": 2000},
    )
    assert response.status_code == 200
    assert response.json()["puntos_totales"] == 5


def test_acumular_rechaza_monto_cero_o_negativo():
    response = client.post(
        "/fidelidad/acumular",
        json={"cliente_id": "cliente-fid-3", "monto_gastado": 0},
    )
    assert response.status_code == 422


def test_canjear_beneficio_con_puntos_suficientes():
    client.post(
        "/fidelidad/acumular",
        json={"cliente_id": "cliente-fid-4", "monto_gastado": 100000},  # 100 puntos
    )
    response = client.post(
        "/fidelidad/canjear",
        json={"cliente_id": "cliente-fid-4", "beneficio": "bebida_gratis"},  # cuesta 50
    )
    assert response.status_code == 200
    data = response.json()
    assert data["puntos_usados"] == 50
    assert data["puntos_restantes"] == 50


def test_canjear_rechaza_puntos_insuficientes():
    client.post(
        "/fidelidad/acumular",
        json={"cliente_id": "cliente-fid-5", "monto_gastado": 10000},  # 10 puntos
    )
    response = client.post(
        "/fidelidad/canjear",
        json={"cliente_id": "cliente-fid-5", "beneficio": "cena_vip"},  # cuesta 300
    )
    assert response.status_code == 402


def test_canjear_beneficio_inexistente_da_404():
    response = client.post(
        "/fidelidad/canjear",
        json={"cliente_id": "cliente-fid-6", "beneficio": "algo_que_no_existe"},
    )
    assert response.status_code == 404


def test_definir_limite_diario():
    response = client.post(
        "/fidelidad/limite",
        json={"cliente_id": "cliente-fid-7", "limite_diario": 50000},
    )
    assert response.status_code == 200
    assert response.json()["limite_diario"] == 50000


def test_gasto_permitido_dentro_del_limite():
    client.post(
        "/fidelidad/limite",
        json={"cliente_id": "cliente-fid-8", "limite_diario": 100000},
    )
    response = client.post(
        "/fidelidad/gasto",
        json={"cliente_id": "cliente-fid-8", "monto": 40000},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["permitido"] is True
    assert data["gastado_hoy"] == 40000


def test_gasto_rechazado_al_superar_el_limite():
    client.post(
        "/fidelidad/limite",
        json={"cliente_id": "cliente-fid-9", "limite_diario": 50000},
    )
    client.post("/fidelidad/gasto", json={"cliente_id": "cliente-fid-9", "monto": 40000})

    # Este segundo gasto sumaría 70.000, supera el límite de 50.000
    response = client.post(
        "/fidelidad/gasto", json={"cliente_id": "cliente-fid-9", "monto": 30000}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["permitido"] is False
    # El gasto rechazado no debe quedar registrado
    assert data["gastado_hoy"] == 40000


def test_gasto_sin_limite_definido_se_permite():
    response = client.post(
        "/fidelidad/gasto", json={"cliente_id": "cliente-fid-sin-limite", "monto": 999999}
    )
    assert response.status_code == 200
    assert response.json()["permitido"] is True
