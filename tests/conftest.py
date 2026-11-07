"""
Configuración común de las pruebas.

Las pruebas corren contra una base PostgreSQL real (la misma tecnología de
producción). Antes de cada prueba se vacía y se vuelven a cargar los datos de
ejemplo, así que cada prueba es independiente.

Variable de entorno: DATABASE_URL (debe apuntar a una base cuyo nombre
contenga "test", para no borrar datos reales por accidente).
"""

import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/goldentable_test"
)
os.environ.setdefault("PBKDF2_ITERACIONES", "1000")  # contraseñas rápidas solo en pruebas

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from src.api import config, orm  # noqa: E402
from src.api.auth import crear_token, hashear_password  # noqa: E402
from src.api.db import Base, SessionLocal, crear_tablas, engine, esperar_base_de_datos  # noqa: E402
from src.api.main import app  # noqa: E402
from src.api.seed import PASSWORD_DEMO, sembrar  # noqa: E402

assert "test" in config.DATABASE_URL, "Las pruebas solo pueden correr sobre una base de datos *test*"


@pytest.fixture(scope="session", autouse=True)
def esquema():
    esperar_base_de_datos(intentos=5, espera=1)
    Base.metadata.drop_all(bind=engine)
    crear_tablas()
    yield


@pytest.fixture(autouse=True)
def datos_limpios(esquema):
    tablas = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with engine.begin() as conexion:
        conexion.execute(text(f"TRUNCATE {tablas} RESTART IDENTITY CASCADE"))
    with SessionLocal() as db:
        sembrar(db)
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def password_demo():
    return PASSWORD_DEMO


def _headers(usuario: str) -> dict:
    with SessionLocal() as db:
        u = db.query(orm.Usuario).filter(orm.Usuario.usuario == usuario).one()
        return {"Authorization": f"Bearer {crear_token(u)}"}


@pytest.fixture
def h_cliente1():
    return _headers("cliente1")


@pytest.fixture
def h_cliente2():
    return _headers("cliente2")


@pytest.fixture
def h_anfitrion():
    return _headers("anfitrion")


@pytest.fixture
def h_cajero():
    return _headers("cajero")


@pytest.fixture
def h_gerente():
    return _headers("gerente")


@pytest.fixture
def nuevo_cliente():
    """Crea un cliente vacío (0 puntos, saldo 0) y devuelve (nombre, headers)."""
    from datetime import date

    def _crear(nombre: str):
        with SessionLocal() as db:
            n = db.query(orm.Usuario).count() + 1
            db.add(
                orm.Usuario(
                    usuario=nombre,
                    nombre=f"Cliente {nombre}",
                    documento=f"{9000000000 + n}",
                    fecha_nacimiento=date(1990, 1, 1),
                    password_hash=hashear_password("Clave12345"),
                    rol="cliente",
                )
            )
            db.flush()
            db.add(orm.Puntos(cliente_id=nombre, puntos=0))
            db.add(orm.Billetera(cliente_id=nombre))
            db.commit()
        return nombre, _headers(nombre)

    return _crear
