"""Tests de HU-02 (REQ-FUNC-002): reserva de mesa con confirmación inmediata."""

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)
FECHA = "2030-05-20"


def reservar(mesa_id=1, hora="18:00", fecha=FECHA, cliente="ana"):
    return client.post(
        "/reservas",
        json={"cliente_id": cliente, "mesa_id": mesa_id, "fecha": fecha, "hora": hora},
    )


def test_reserva_exitosa_devuelve_codigo():
    r = reservar()
    assert r.status_code == 201
    data = r.json()
    assert len(data["codigo_confirmacion"]) == 8
    assert data["estado"] == "confirmada"


def test_reserva_quita_mesa_de_disponibilidad_solo_ese_dia():
    reservar()
    ids = lambda f: [m["id"] for m in client.get(f"/disponibilidad?fecha={f}&hora=18:00").json()]
    assert 1 not in ids(FECHA)
    assert 1 in ids("2030-05-21")


def test_doble_reserva_misma_mesa_rechazada():
    assert reservar().status_code == 201
    assert reservar(cliente="beto").status_code == 409


def test_mesa_inexistente_404():
    assert reservar(mesa_id=999).status_code == 404


def test_mesa_no_disponible_o_hora_distinta_409():
    assert reservar(mesa_id=5, hora="20:00").status_code == 409  # ocupada
    assert reservar(mesa_id=1, hora="19:00").status_code == 409  # otra franja


def test_hora_invalida_422():
    assert reservar(hora="25:99").status_code == 422
    assert client.get("/disponibilidad?fecha=2030-01-01&hora=abc").status_code == 422


def test_listar_y_consultar_reserva():
    codigo = reservar().json()["codigo_confirmacion"]
    reservar(mesa_id=4, hora="19:00")
    lista = client.get(f"/reservas?fecha={FECHA}").json()
    assert [r["hora"] for r in lista] == ["18:00", "19:00"]
    assert client.get(f"/reservas/{codigo.lower()}").status_code == 200
    assert client.get("/reservas/NOEXISTE").status_code == 404
    assert len(client.get("/reservas").json()) == 2
