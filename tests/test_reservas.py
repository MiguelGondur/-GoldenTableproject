"""
Test unitario de HU-02: valida que la reserva exitosa devuelva un
código de confirmación y que la mesa deje de aparecer disponible.
"""

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_reserva_exitosa_genera_codigo():
    response = client.post(
        "/reservas/",
        json={"mesa_id": 1, "fecha": "2026-09-20", "hora": "18:00", "cliente_id": "cliente-1"},
    )
    assert response.status_code == 200

    data = response.json()
    assert "codigo_confirmacion" in data
    assert len(data["codigo_confirmacion"]) == 8


def test_mesa_reservada_ya_no_aparece_disponible():
    client.post(
        "/reservas/",
        json={"mesa_id": 2, "fecha": "2026-09-20", "hora": "18:00", "cliente_id": "cliente-2"},
    )

    response = client.get("/disponibilidad", params={"fecha": "2026-09-20", "hora": "18:00"})
    mesas_disponibles_ids = [m["id"] for m in response.json()]
    assert 2 not in mesas_disponibles_ids


def test_reserva_mesa_no_disponible_falla():
    response = client.post(
        "/reservas/",
        json={"mesa_id": 3, "fecha": "2026-09-20", "hora": "18:00", "cliente_id": "cliente-3"},
    )
    # La mesa 3 está registrada en horario 19:00, no 18:00 → no coincide
    assert response.status_code == 409
