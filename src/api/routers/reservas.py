"""
Endpoints de Reservas.

HU-02: Reserva y confirmación (REQ-FUNC-002)
"""

import uuid
from datetime import date as date_type

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.models import EstadoMesa
from src.api.store import MESAS_DB

router = APIRouter(prefix="/reservas", tags=["reservas"])

# Almacenamiento en memoria de reservas — placeholder hasta integrar base de datos real.
RESERVAS_DB: dict[str, dict] = {}


class ReservaRequest(BaseModel):
    mesa_id: int
    fecha: date_type
    hora: str
    cliente_id: str


class ReservaConfirmada(BaseModel):
    codigo_confirmacion: str
    mesa_id: int
    fecha: date_type
    hora: str
    cliente_id: str


@router.post("/", response_model=ReservaConfirmada)
def crear_reserva(datos: ReservaRequest):
    """
    HU-02: crea una reserva sobre una mesa disponible, genera un código
    de confirmación único y bloquea la mesa (pasa a estado 'reservada').
    """
    mesa = next((m for m in MESAS_DB if m.id == datos.mesa_id), None)

    if mesa is None:
        raise HTTPException(status_code=404, detail="La mesa solicitada no existe.")

    if mesa.estado != EstadoMesa.DISPONIBLE or mesa.horario != datos.hora:
        raise HTTPException(
            status_code=409,
            detail="La mesa no está disponible para la fecha/hora solicitada.",
        )

    mesa.estado = EstadoMesa.RESERVADA  # bloquea la mesa

    codigo_confirmacion = str(uuid.uuid4())[:8].upper()
    RESERVAS_DB[codigo_confirmacion] = {
        "mesa_id": mesa.id,
        "fecha": datos.fecha,
        "hora": datos.hora,
        "cliente_id": datos.cliente_id,
    }

    return ReservaConfirmada(
        codigo_confirmacion=codigo_confirmacion,
        mesa_id=mesa.id,
        fecha=datos.fecha,
        hora=datos.hora,
        cliente_id=datos.cliente_id,
    )
