"""
Endpoints de Reservas.

HU-02: Reserva de mesa con confirmación inmediata (REQ-FUNC-002)
HU-03: Check-in del cliente en recepción (REQ-FUNC-003)
"""

import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.api.models import PATRON_HORA, EstadoReserva, Reserva
from src.api.seguridad import verificar_autoexclusion
from src.api.store import MESAS_DB, RESERVAS_DB

router = APIRouter(prefix="/reservas", tags=["reservas"])


class ReservaRequest(BaseModel):
    cliente_id: str
    mesa_id: int
    fecha: date
    hora: str = Field(..., pattern=PATRON_HORA, description="Hora de la reserva, formato HH:MM")


class CheckInRequest(BaseModel):
    codigo_confirmacion: str


def _codigo_unico() -> str:
    while True:
        codigo = uuid.uuid4().hex[:8].upper()
        if codigo not in RESERVAS_DB:
            return codigo


@router.post("", response_model=Reserva, status_code=201)
def crear_reserva(datos: ReservaRequest):
    """
    HU-02: crea una reserva y devuelve un código de confirmación inmediato.

    - 403 si el cliente está autoexcluido.
    - 404 si la mesa no existe.
    - 409 si la mesa no está disponible a esa hora o ya fue reservada
      para esa fecha y hora.
    """
    verificar_autoexclusion(datos.cliente_id)

    mesa = next((m for m in MESAS_DB if m.id == datos.mesa_id), None)
    if mesa is None:
        raise HTTPException(status_code=404, detail="La mesa solicitada no existe.")

    if mesa.estado.value != "disponible" or mesa.horario != datos.hora:
        raise HTTPException(status_code=409, detail="La mesa no está disponible a esa hora.")

    if any(
        r.mesa_id == datos.mesa_id and r.fecha == datos.fecha and r.hora == datos.hora
        for r in RESERVAS_DB.values()
    ):
        raise HTTPException(status_code=409, detail="La mesa ya está reservada para esa fecha y hora.")

    reserva = Reserva(
        codigo_confirmacion=_codigo_unico(),
        mesa_id=datos.mesa_id,
        fecha=datos.fecha,
        hora=datos.hora,
        cliente_id=datos.cliente_id,
        creada_en=datetime.now(timezone.utc),
    )
    RESERVAS_DB[reserva.codigo_confirmacion] = reserva
    return reserva


@router.get("", response_model=list[Reserva])
def listar_reservas(fecha: date | None = Query(None, description="Filtra por fecha YYYY-MM-DD")):
    """Vista del anfitrión: reservas (opcionalmente de un día) ordenadas por hora."""
    reservas = [r for r in RESERVAS_DB.values() if fecha is None or r.fecha == fecha]
    return sorted(reservas, key=lambda r: (r.fecha, r.hora))


@router.post("/checkin", response_model=Reserva)
def hacer_checkin(datos: CheckInRequest):
    """
    HU-03: el cliente llega al casino y confirma su reserva con el código
    recibido. La reserva pasa a 'en_curso'.

    - 404 si el código no existe.
    - 409 si ya se hizo check-in.
    """
    reserva = RESERVAS_DB.get(datos.codigo_confirmacion.strip().upper())
    if reserva is None:
        raise HTTPException(status_code=404, detail="Código de confirmación no encontrado.")
    if reserva.estado == EstadoReserva.EN_CURSO:
        raise HTTPException(status_code=409, detail="El check-in de esta reserva ya fue realizado.")

    reserva.estado = EstadoReserva.EN_CURSO
    reserva.check_in_en = datetime.now(timezone.utc)
    return reserva


@router.get("/{codigo}", response_model=Reserva)
def consultar_reserva(codigo: str):
    """Consulta una reserva por su código de confirmación."""
    reserva = RESERVAS_DB.get(codigo.strip().upper())
    if reserva is None:
        raise HTTPException(status_code=404, detail="Reserva no encontrada.")
    return reserva
