"""
Test unitario de HU-10: verifica que el registro sea rechazado si el
usuario es menor de edad, y aceptado si es mayor, según REQ-FUNC-010.
"""

from datetime import date

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_registro_rechazado_menor_de_edad():
    hoy = date.today()
    fecha_nacimiento_menor = date(hoy.year - 15, hoy.month, hoy.day)

    response = client.post(
        "/usuarios/registro",
        json={
            "nombre": "Usuario Menor",
            "documento": "1000000001",
            "fecha_nacimiento": fecha_nacimiento_menor.isoformat(),
        },
    )
    assert response.status_code == 403


def test_registro_aceptado_mayor_de_edad():
    hoy = date.today()
    fecha_nacimiento_mayor = date(hoy.year - 25, hoy.month, hoy.day)

    response = client.post(
        "/usuarios/registro",
        json={
            "nombre": "Usuario Mayor",
            "documento": "1000000002",
            "fecha_nacimiento": fecha_nacimiento_mayor.isoformat(),
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["cuenta_activa"] is True
    assert data["edad"] == 25
