"""
Test de HU-10: verifica que el registro sea rechazado si el usuario es
menor de edad, y aceptado si es mayor, según REQ-FUNC-010.
"""

from datetime import date

from src.api.tiempo import hoy_casino


def registro(usuario="nuevo1", documento="1000000002", anios=25, password="Clave12345", nombre="Usuario Nuevo"):
    hoy = hoy_casino()
    return {
        "nombre": nombre,
        "usuario": usuario,
        "password": password,
        "documento": documento,
        "fecha_nacimiento": date(hoy.year - anios, hoy.month, min(hoy.day, 28)).isoformat(),
    }


def test_registro_rechazado_menor_de_edad(client):
    response = client.post("/usuarios/registro", json=registro(anios=15, documento="1000000001"))
    assert response.status_code == 403
    assert client.post("/auth/login", json={"usuario": "nuevo1", "password": "Clave12345"}).status_code == 401


def test_registro_aceptado_mayor_de_edad(client):
    response = client.post("/usuarios/registro", json=registro())
    assert response.status_code == 201
    data = response.json()
    assert data["cuenta_activa"] is True and data["edad"] == 25 and data["rol"] == "cliente"
    # ya puede iniciar sesión, y arranca con billetera y puntos en cero
    token = client.post("/auth/login", json={"usuario": "nuevo1", "password": "Clave12345"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    assert client.get("/billetera/nuevo1", headers=h).json()["saldo"] == 0
    assert client.get("/fidelidad/puntos/nuevo1", headers=h).json()["puntos"] == 0


def test_justo_18_anios_es_aceptado(client):
    assert client.post("/usuarios/registro", json=registro(anios=18)).status_code == 201


def test_registro_publico_siempre_crea_rol_cliente(client):
    body = registro()
    body["rol"] = "gerente"  # campo extra: se ignora
    assert client.post("/usuarios/registro", json=body).json()["rol"] == "cliente"


def test_calcular_edad_antes_y_despues_del_cumpleanos():
    from src.api.routers.usuarios import calcular_edad

    nac = date(2000, 6, 15)
    assert calcular_edad(nac, hoy=date(2026, 6, 14)) == 25
    assert calcular_edad(nac, hoy=date(2026, 6, 15)) == 26
