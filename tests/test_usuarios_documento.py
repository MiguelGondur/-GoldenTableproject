"""Tests de HU-10 (REQ-FUNC-010): verificación de identidad por documento."""

from tests.test_usuarios import registro


def test_documento_invalido_rechazado(client):
    for malo in ["abc123", "123", "12345678901", "12.345.678", "      "]:
        assert client.post("/usuarios/registro", json=registro(documento=malo)).status_code == 422


def test_nombre_usuario_y_clave_invalidos_rechazados(client):
    assert client.post("/usuarios/registro", json=registro(nombre="A")).status_code == 422
    assert client.post("/usuarios/registro", json=registro(usuario="Ab")).status_code == 422
    assert client.post("/usuarios/registro", json=registro(usuario="con espacio")).status_code == 422
    assert client.post("/usuarios/registro", json=registro(password="corta")).status_code == 422


def test_documento_o_usuario_duplicado_409(client):
    assert client.post("/usuarios/registro", json=registro()).status_code == 201
    assert client.post("/usuarios/registro", json=registro(usuario="otro", documento="1000000002")).status_code == 409
    assert client.post("/usuarios/registro", json=registro(usuario="nuevo1", documento="1000000003")).status_code == 409


def test_consultar_usuario(client, h_cliente1, h_gerente):
    r = client.get("/usuarios/cliente1", headers=h_cliente1)
    assert r.status_code == 200 and r.json()["cuenta_activa"] is True
    assert client.get("/usuarios/cliente2", headers=h_cliente1).status_code == 403
    assert client.get("/usuarios/cliente2", headers=h_gerente).status_code == 200
    assert client.get("/usuarios/nadie", headers=h_gerente).status_code == 404
