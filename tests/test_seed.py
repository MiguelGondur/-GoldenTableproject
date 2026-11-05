"""Los datos de ejemplo del README existen desde el primer arranque."""

from src.api import orm
from src.api.db import SessionLocal
from src.api.seed import PASSWORD_DEMO, USUARIOS_DEMO, sembrar


def test_usuarios_de_ejemplo_pueden_iniciar_sesion(client):
    for usuario, *_ in USUARIOS_DEMO:
        r = client.post("/auth/login", json={"usuario": usuario, "password": PASSWORD_DEMO})
        assert r.status_code == 200, usuario


def test_datos_de_ejemplo_existen():
    with SessionLocal() as db:
        assert db.query(orm.Mesa).count() == 23
        assert db.query(orm.Usuario).count() == 5
        assert db.get(orm.Puntos, "cliente1").puntos == 500
        assert float(db.get(orm.Billetera, "cliente1").saldo) == 150000
        assert db.get(orm.Reserva, "DEMO0001") is not None


def test_sembrar_es_idempotente():
    with SessionLocal() as db:
        sembrar(db)
        sembrar(db)
        assert db.query(orm.Usuario).count() == 5
        assert db.query(orm.Mesa).count() == 23
        assert db.query(orm.Reserva).count() == 1
