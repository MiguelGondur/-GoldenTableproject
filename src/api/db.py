"""Conexión a PostgreSQL con SQLAlchemy."""

import logging
import time

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.api import config

logger = logging.getLogger("goldentable.db")

engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """Dependencia de FastAPI: una sesión por petición."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def esperar_base_de_datos(intentos: int = 30, espera: float = 2.0) -> None:
    """Espera a que PostgreSQL acepte conexiones (útil al arrancar con Docker Compose)."""
    for intento in range(1, intentos + 1):
        try:
            with engine.connect():
                return
        except OperationalError:
            logger.warning("Base de datos no disponible (intento %s/%s)", intento, intentos)
            time.sleep(espera)
    raise RuntimeError("No fue posible conectarse a la base de datos")


def crear_tablas() -> None:
    from src.api import orm  # noqa: F401  (registra los modelos)

    Base.metadata.create_all(bind=engine)
