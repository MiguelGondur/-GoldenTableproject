"""
Autenticación JWT y bloqueo de cuenta (REQ-NFUNC-003).

Bono de la entrega final: el API emite un token al iniciar sesión y responde
401 a cualquier petición sin token en un endpoint protegido.
"""

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from src.api import config, orm
from src.api.db import SessionLocal

ROLES = ["cliente1", "cliente2", "anfitrion", "cajero", "gerente"]


def login(client, usuario, password):
    return client.post("/auth/login", json={"usuario": usuario, "password": password})


@pytest.mark.parametrize("usuario", ROLES)
def test_login_exitoso_devuelve_token_y_rol(client, password_demo, usuario):
    r = login(client, usuario, password_demo)
    assert r.status_code == 200
    data = r.json()
    assert data["token_type"] == "bearer"
    assert data["usuario"] == usuario
    claims = jwt.decode(data["access_token"], config.JWT_SECRET, algorithms=["HS256"])
    assert claims["sub"] == usuario and claims["rol"] == data["rol"]


def test_me_con_token_valido(client, password_demo):
    token = login(client, "gerente", password_demo).json()["access_token"]
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["rol"] == "gerente"


def test_credenciales_incorrectas_401(client):
    assert login(client, "cliente1", "mala-clave").status_code == 401
    assert login(client, "no-existe", "lo-que-sea").status_code == 401


def test_bloqueo_tras_5_intentos_fallidos(client, password_demo):
    for _ in range(4):
        assert login(client, "cliente1", "mala-clave").status_code == 401
    assert login(client, "cliente1", "mala-clave").status_code == 423  # el 5.º bloquea
    # Incluso con la clave correcta sigue bloqueada
    assert login(client, "cliente1", password_demo).status_code == 423
    # Otros usuarios no se ven afectados
    assert login(client, "cliente2", password_demo).status_code == 200


def test_bloqueo_expira(client, password_demo):
    for _ in range(5):
        login(client, "cliente1", "mala-clave")
    with SessionLocal() as db:
        u = db.query(orm.Usuario).filter_by(usuario="cliente1").one()
        u.bloqueado_hasta = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    assert login(client, "cliente1", password_demo).status_code == 200


def test_login_exitoso_reinicia_contador(client, password_demo):
    for _ in range(4):
        login(client, "cliente1", "mala-clave")
    assert login(client, "cliente1", password_demo).status_code == 200
    for _ in range(4):  # si no se hubiera reiniciado, el 1.º ya bloquearía
        assert login(client, "cliente1", "mala-clave").status_code == 401


RUTAS_PROTEGIDAS = [
    ("get", "/auth/me"),
    ("get", "/disponibilidad?fecha=2030-01-01&hora=18:00"),
    ("post", "/reservas"),
    ("get", "/reservas"),
    ("get", "/reservas/mias"),
    ("post", "/reservas/checkin"),
    ("get", "/reservas/ABC12345"),
    ("post", "/fidelidad/acumular"),
    ("get", "/fidelidad/puntos/cliente1"),
    ("get", "/fidelidad/beneficios"),
    ("post", "/fidelidad/canjear"),
    ("post", "/fidelidad/limite"),
    ("post", "/fidelidad/gasto"),
    ("post", "/fidelidad/autoexclusion"),
    ("get", "/fidelidad/autoexclusion/cliente1"),
    ("post", "/billetera/recarga"),
    ("get", "/billetera/validar"),
    ("get", "/billetera/reportes"),
    ("get", "/billetera/cliente1"),
    ("post", "/notificaciones/enviar"),
    ("post", "/notificaciones/reservas-proximas"),
    ("get", "/notificaciones/cliente1"),
    ("get", "/usuarios/cliente1"),
]


@pytest.mark.parametrize("metodo,ruta", RUTAS_PROTEGIDAS)
def test_sin_token_da_401(client, metodo, ruta):
    r = getattr(client, metodo)(ruta)
    assert r.status_code == 401, f"{metodo.upper()} {ruta} respondió {r.status_code}"
    assert r.headers["www-authenticate"] == "Bearer"


def test_token_invalido_401(client):
    r = client.get("/auth/me", headers={"Authorization": "Bearer esto.no.es.un.jwt"})
    assert r.status_code == 401


def test_token_firmado_con_otra_clave_401(client):
    falso = jwt.encode({"sub": "gerente", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, "otra", "HS256")
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {falso}"}).status_code == 401


def test_token_expirado_401(client):
    vencido = jwt.encode(
        {"sub": "gerente", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        config.JWT_SECRET,
        "HS256",
    )
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {vencido}"})
    assert r.status_code == 401
    assert "expir" in r.json()["detail"].lower()


def test_token_de_usuario_inexistente_401(client):
    token = jwt.encode(
        {"sub": "fantasma", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        config.JWT_SECRET,
        "HS256",
    )
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_endpoints_publicos_no_piden_token(client):
    assert client.get("/health").status_code == 200
    assert client.get("/").status_code == 200
    assert client.post("/auth/login", json={"usuario": "x", "password": "y"}).status_code == 401
