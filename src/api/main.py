"""
GoldenTable API — punto de entrada de la aplicación.

Los endpoints reales para cada requisito funcional (REQ-FUNC-001 a
REQ-FUNC-012) se van agregando en las siguientes iteraciones, cada uno
en su propia rama feature/*.
"""

from datetime import date as date_type

from fastapi import FastAPI, Query

from src.api.models import EstadoMesa, Mesa
from src.api.routers import billetera, fidelidad, reservas, usuarios
from src.api.store import MESAS_DB

app = FastAPI(
    title="GoldenTable API",
    description="API de reservas, fidelidad y billetera digital para casino físico.",
    version="0.1.0",
)


@app.get("/")
def read_root():
    """Endpoint de salud básico para confirmar que la API está corriendo."""
    return {"status": "ok", "app": "GoldenTable"}


@app.get("/health")
def health_check():
    """Health check usado por el pipeline de CI en Seguimiento 3."""
    return {"status": "healthy"}


@app.get("/disponibilidad", response_model=list[Mesa])
def consultar_disponibilidad(
    fecha: date_type = Query(..., description="Fecha de la reserva, formato YYYY-MM-DD"),
    hora: str = Query(..., description="Hora deseada, formato HH:MM"),
):
    """
    HU-01: Consulta de disponibilidad en tiempo real (REQ-FUNC-001).

    Retorna únicamente las mesas cuyo estado es 'disponible' para la
    hora solicitada. La fecha se recibe para una futura integración con
    el calendario de reservas; por ahora el filtro se aplica solo por hora.
    """
    mesas_disponibles = [
        mesa
        for mesa in MESAS_DB
        if mesa.estado == EstadoMesa.DISPONIBLE and mesa.horario == hora
    ]
    return mesas_disponibles


app.include_router(usuarios.router)
app.include_router(billetera.router)
app.include_router(reservas.router)
app.include_router(fidelidad.router)
