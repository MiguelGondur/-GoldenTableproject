"""
GoldenTable API — punto de entrada de la aplicación.

Cada épica del SRS vive en su propio router (src/api/routers/*) y el
estado compartido en memoria está en src/api/store.py.
"""

from datetime import date as date_type

from fastapi import FastAPI, Query

from src.api import store
from src.api.models import PATRON_HORA, Mesa
from src.api.routers import billetera, fidelidad, reservas, usuarios

app = FastAPI(
    title="GoldenTable API",
    description="API de reservas, fidelidad y billetera digital para casino físico.",
    version="1.0.0",
)
app.include_router(usuarios.router)
app.include_router(billetera.router)
app.include_router(fidelidad.router)
app.include_router(reservas.router)


@app.get("/")
def read_root():
    """Endpoint de salud básico para confirmar que la API está corriendo."""
    return {"status": "ok", "app": "GoldenTable"}


@app.get("/health")
def health_check():
    """Health check usado por el pipeline de CI y el smoke test."""
    return {"status": "healthy"}


@app.get("/disponibilidad", response_model=list[Mesa])
def consultar_disponibilidad(
    fecha: date_type = Query(..., description="Fecha de la reserva, formato YYYY-MM-DD"),
    hora: str = Query(..., pattern=PATRON_HORA, description="Hora deseada, formato HH:MM"),
):
    """
    HU-01: Consulta de disponibilidad en tiempo real (REQ-FUNC-001).

    Retorna las mesas disponibles para la fecha y hora solicitadas:
    estado 'disponible', misma franja horaria y sin reserva ese día.
    """
    return store.mesas_disponibles(fecha, hora)
