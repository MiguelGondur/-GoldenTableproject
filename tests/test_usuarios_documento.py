"""Tests de HU-10 (REQ-FUNC-010): verificación de identidad por documento."""

from datetime import date

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)
NAC = date(date.today().year - 30, 1, 1).isoformat()


def registrar(documento="123456789", nombre="Ana Pérez"):
    return client.post(
        "/usuarios/registro",
        json={"nombre": nombre, "documento": documento, "fecha_nacimiento": NAC},
    )


def test_documento_invalido_rechazado():
    for malo in ["abc123", "123", "12345678901", "12.345.678"]:
        assert registrar(documento=malo).status_code == 422


def test_nombre_muy_corto_rechazado():
    assert registrar(nombre="A").status_code == 422


def test_documento_duplicado_409():
    assert registrar().status_code == 200
    assert registrar().status_code == 409


def test_consultar_usuario():
    registrar()
    r = client.get("/usuarios/123456789")
    assert r.status_code == 200 and r.json()["cuenta_activa"] is True
    assert client.get("/usuarios/999999999").status_code == 404
