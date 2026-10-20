"""Tests de HU-03 (REQ-FUNC-003): check-in del cliente con su código."""

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def crear():
    return client.post(
        "/reservas",
        json={"cliente_id": "ana", "mesa_id": 2, "fecha": "2030-05-20", "hora": "18:00"},
    ).json()["codigo_confirmacion"]


def test_checkin_exitoso():
    codigo = crear()
    r = client.post("/reservas/checkin", json={"codigo_confirmacion": codigo})
    assert r.status_code == 200
    assert r.json()["estado"] == "en_curso"
    assert r.json()["check_in_en"] is not None


def test_checkin_acepta_minusculas():
    codigo = crear()
    r = client.post("/reservas/checkin", json={"codigo_confirmacion": f" {codigo.lower()} "})
    assert r.status_code == 200


def test_checkin_codigo_inexistente_404():
    assert client.post("/reservas/checkin", json={"codigo_confirmacion": "ZZZZZZZZ"}).status_code == 404


def test_checkin_repetido_409():
    codigo = crear()
    client.post("/reservas/checkin", json={"codigo_confirmacion": codigo})
    assert client.post("/reservas/checkin", json={"codigo_confirmacion": codigo}).status_code == 409
