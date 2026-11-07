"""
GoldenTable API — punto de entrada de la aplicación.

Cada épica del SRS vive en su propio router (src/api/routers/*). Los datos
se guardan en PostgreSQL (src/api/orm.py) y el acceso se protege con JWT.
"""

import logging
from contextlib import asynccontextmanager
from datetime import date as date_type

from fastapi import Depends, FastAPI, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api import config, store
from src.api.auth import usuario_actual
from src.api.db import SessionLocal, crear_tablas, esperar_base_de_datos, get_db
from src.api.errores import errores
from src.api.models import PATRON_HORA, Mesa
from src.api.orm import Usuario
from src.api.routers import auth, billetera, fidelidad, notificaciones, reservas, usuarios
from src.api.seed import sembrar

logging.basicConfig(level=logging.INFO)


class EstadoApi(BaseModel):
    status: str
    app: str


class Salud(BaseModel):
    status: str


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Al arrancar: espera la base de datos, crea las tablas y carga los datos de ejemplo."""
    esperar_base_de_datos()
    crear_tablas()
    if config.SEED_DATA:
        with SessionLocal() as db:
            sembrar(db)
    yield


app = FastAPI(
    title="GoldenTable API",
    description=(
        "API de reservas, fidelidad y billetera digital para casino físico. "
        "Autenticación con JWT: obtén el token en `POST /auth/login` y envíalo en "
        "`Authorization: Bearer <token>`."
    ),
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(billetera.router)
app.include_router(fidelidad.router)
app.include_router(reservas.router)
app.include_router(notificaciones.router)


@app.get("/", response_model=EstadoApi, tags=["sistema"], summary="Estado de la API")
def read_root():
    """Endpoint básico para confirmar que la API está corriendo."""
    return {"status": "ok", "app": "GoldenTable"}


@app.get("/health", response_model=Salud, tags=["sistema"], summary="Health check")
def health_check():
    """Health check usado por Docker Compose, el CI y el smoke test."""
    return {"status": "healthy"}


@app.get(
    "/disponibilidad",
    response_model=list[Mesa],
    tags=["reservas"],
    summary="Consultar disponibilidad de mesas",
    responses=errores(401),
)
def consultar_disponibilidad(
    fecha: date_type = Query(..., description="Fecha de la reserva, formato YYYY-MM-DD"),
    hora: str = Query(..., pattern=PATRON_HORA, description="Hora deseada, formato HH:MM"),
    _: Usuario = Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    """
    HU-01: Consulta de disponibilidad en tiempo real (REQ-FUNC-001).

    Retorna las mesas disponibles para la fecha y hora solicitadas:
    estado 'disponible', misma franja horaria y sin reserva ese día.
    """
    return store.mesas_disponibles(db, fecha, hora)
