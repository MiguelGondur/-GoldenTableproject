"""
Endpoints de Reservas.

HU-01: Consulta de disponibilidad (en main.py: GET /disponibilidad)
HU-02: Reserva de mesa con confirmación inmediata (REQ-FUNC-002)
HU-03: Vista del anfitrión y check-in del cliente (REQ-FUNC-003)
"""

import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.auth import ANFITRION, CLIENTE, GERENTE, requiere_roles, resolver_cliente, usuario_actual
from src.api.db import get_db
from src.api.errores import errores
from src.api.models import PATRON_HORA, Reserva
from src.api.orm import Mesa
from src.api.orm import Reserva as ReservaDB
from src.api.orm import Usuario
from src.api.seguridad import verificar_autoexclusion
from src.api.tiempo import hoy_casino

router = APIRouter(prefix="/reservas", tags=["reservas"])


class ReservaRequest(BaseModel):
    cliente_id: str | None = Field(
        default=None, description="Solo para el personal (reserva telefónica); el cliente reserva a su nombre"
    )
    mesa_id: int
    fecha: date
    hora: str = Field(..., pattern=PATRON_HORA, description="Hora de la reserva, formato HH:MM")


class CheckInRequest(BaseModel):
    codigo_confirmacion: str = Field(..., min_length=1, max_length=20)


def _resultado(reserva: ReservaDB) -> Reserva:
    return Reserva.model_validate(reserva)


@router.post(
    "",
    response_model=Reserva,
    status_code=201,
    summary="Reservar una mesa",
    responses=errores(401, 403, 404, 409),
)
def crear_reserva(
    datos: ReservaRequest,
    usuario: Usuario = Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    """
    HU-02: bloquea la mesa y devuelve un código de confirmación único.

    - 403 si el cliente está autoexcluido.
    - 404 si la mesa no existe.
    - 409 si la mesa no está disponible a esa hora o ya fue reservada
      para esa fecha y hora (también ante peticiones simultáneas).
    - 422 si la fecha ya pasó o la hora no tiene el formato HH:MM.
    """
    cliente = resolver_cliente(db, usuario, datos.cliente_id)
    verificar_autoexclusion(db, cliente)

    if datos.fecha < hoy_casino():
        raise HTTPException(status_code=422, detail="La fecha de la reserva no puede ser pasada.")

    mesa = db.get(Mesa, datos.mesa_id)
    if mesa is None:
        raise HTTPException(status_code=404, detail="La mesa solicitada no existe.")
    if mesa.estado != "disponible" or mesa.horario != datos.hora:
        raise HTTPException(status_code=409, detail="La mesa no está disponible a esa hora.")

    for _ in range(5):
        ocupada = (
            db.query(ReservaDB.codigo_confirmacion)
            .filter(
                ReservaDB.mesa_id == datos.mesa_id,
                ReservaDB.fecha == datos.fecha,
                ReservaDB.hora == datos.hora,
            )
            .first()
        )
        if ocupada is not None:
            raise HTTPException(
                status_code=409, detail="La mesa ya está reservada para esa fecha y hora."
            )
        reserva = ReservaDB(
            codigo_confirmacion=uuid.uuid4().hex[:8].upper(),
            mesa_id=datos.mesa_id,
            fecha=datos.fecha,
            hora=datos.hora,
            cliente_id=cliente,
            creada_en=datetime.now(timezone.utc),
        )
        db.add(reserva)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()  # código repetido o reserva simultánea: se reintenta/revalida
            continue
        return _resultado(reserva)
    raise HTTPException(status_code=409, detail="No fue posible completar la reserva. Intenta de nuevo.")


@router.get(
    "",
    response_model=list[Reserva],
    summary="Reservas del día (vista del anfitrión)",
    responses=errores(401, 403),
)
def listar_reservas(
    fecha: date | None = Query(None, description="Filtra por fecha YYYY-MM-DD"),
    _: Usuario = Depends(requiere_roles(ANFITRION, GERENTE)),
    db: Session = Depends(get_db),
):
    """US-003: el anfitrión ve las reservas (opcionalmente de un día) ordenadas por hora."""
    consulta = db.query(ReservaDB)
    if fecha is not None:
        consulta = consulta.filter(ReservaDB.fecha == fecha)
    return [_resultado(r) for r in consulta.order_by(ReservaDB.fecha, ReservaDB.hora, ReservaDB.mesa_id)]


@router.get(
    "/mias",
    response_model=list[Reserva],
    summary="Mis reservas",
    responses=errores(401, 403),
)
def mis_reservas(
    usuario: Usuario = Depends(requiere_roles(CLIENTE)), db: Session = Depends(get_db)
):
    """Reservas del cliente autenticado, la más próxima primero."""
    reservas = (
        db.query(ReservaDB)
        .filter(ReservaDB.cliente_id == usuario.usuario)
        .order_by(ReservaDB.fecha, ReservaDB.hora)
        .all()
    )
    return [_resultado(r) for r in reservas]


@router.post(
    "/checkin",
    response_model=Reserva,
    summary="Check-in de una reserva",
    responses=errores(401, 403, 404, 409),
)
def hacer_checkin(
    datos: CheckInRequest,
    _: Usuario = Depends(requiere_roles(ANFITRION, GERENTE)),
    db: Session = Depends(get_db),
):
    """
    HU-03: el anfitrión escanea/ingresa el código de confirmación y la
    reserva pasa a 'en_curso'.

    - 404 si el código no existe.
    - 409 si ya se hizo check-in.
    """
    reserva = db.get(ReservaDB, datos.codigo_confirmacion.strip().upper(), with_for_update=True)
    if reserva is None:
        raise HTTPException(status_code=404, detail="Código de confirmación no encontrado.")
    if reserva.estado == "en_curso":
        raise HTTPException(status_code=409, detail="El check-in de esta reserva ya fue realizado.")

    reserva.estado = "en_curso"
    reserva.check_in_en = datetime.now(timezone.utc)
    db.commit()
    return _resultado(reserva)


@router.get(
    "/{codigo}",
    response_model=Reserva,
    summary="Consultar una reserva por código",
    responses=errores(401, 403, 404),
)
def consultar_reserva(
    codigo: str, usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)
):
    """Un cliente solo ve sus reservas; el personal puede ver cualquiera."""
    reserva = db.get(ReservaDB, codigo.strip().upper())
    if reserva is None:
        raise HTTPException(status_code=404, detail="Reserva no encontrada.")
    if usuario.rol == CLIENTE and reserva.cliente_id != usuario.usuario:
        raise HTTPException(status_code=403, detail="Esta reserva pertenece a otro cliente.")
    return _resultado(reserva)
