"""
Endpoints de Notificaciones push.

HU-09: Notificaciones de reservas próximas, promociones y vencimiento de
puntos (REQ-FUNC-009).

El proveedor push real (FCM/APNs) no está integrado: el envío se simula
registrando la notificación y escribiendo una línea en el log
`goldentable.notificaciones` (ver docs/DEUDA_TECNICA.md).
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api.auth import ANFITRION, GERENTE, requiere_roles, resolver_cliente, usuario_actual
from src.api.db import get_db
from src.api.errores import errores
from src.api.models import Notificacion, TipoNotificacion
from src.api.orm import Notificacion as NotificacionDB
from src.api.orm import Reserva, Usuario
from src.api.seguridad import esta_autoexcluido
from src.api.tiempo import ahora_casino

router = APIRouter(prefix="/notificaciones", tags=["notificaciones"])
logger = logging.getLogger("goldentable.notificaciones")

MENSAJES_POR_DEFECTO = {
    TipoNotificacion.RESERVA_PROXIMA: "Tu reserva en GoldenTable es pronto. ¡Te esperamos!",
    TipoNotificacion.PROMOCION: "Tenemos una promoción especial para ti en GoldenTable.",
    TipoNotificacion.VENCIMIENTO_PUNTOS: "Tus puntos de fidelidad están próximos a vencer. ¡Canjéalos!",
}


class EnvioRequest(BaseModel):
    cliente_id: str
    tipo: TipoNotificacion
    mensaje: str | None = None


def _enviar(db: Session, cliente_id: str, tipo: TipoNotificacion, mensaje: str | None) -> NotificacionDB:
    notificacion = NotificacionDB(
        cliente_id=cliente_id,
        tipo=tipo.value,
        mensaje=mensaje or MENSAJES_POR_DEFECTO[tipo],
        enviada_en=datetime.now(timezone.utc),
    )
    db.add(notificacion)
    db.flush()
    logger.info("PUSH -> %s [%s]: %s", cliente_id, tipo.value, notificacion.mensaje)
    return notificacion


@router.post(
    "/enviar",
    response_model=Notificacion,
    status_code=201,
    summary="Enviar una notificación push a un cliente",
    responses=errores(401, 403, 404, 409),
)
def enviar_notificacion(
    datos: EnvioRequest,
    _: Usuario = Depends(requiere_roles(ANFITRION, GERENTE)),
    db: Session = Depends(get_db),
):
    """
    Envía una notificación push al cliente (promoción, vencimiento de
    puntos o reserva próxima). Las promociones NO se envían a clientes
    autoexcluidos (409), por juego responsable.
    """
    existe = db.query(Usuario.id).filter(Usuario.usuario == datos.cliente_id).first()
    if existe is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    if datos.tipo == TipoNotificacion.PROMOCION and esta_autoexcluido(db, datos.cliente_id):
        raise HTTPException(
            status_code=409, detail="No se envían promociones a clientes autoexcluidos."
        )
    notificacion = _enviar(db, datos.cliente_id, datos.tipo, datos.mensaje)
    db.commit()
    return Notificacion.model_validate(notificacion)


@router.post(
    "/reservas-proximas",
    response_model=list[Notificacion],
    summary="Enviar recordatorios de reservas próximas",
    responses=errores(401, 403),
)
def notificar_reservas_proximas(
    horas: int = Query(2, ge=1, le=48, description="Ventana en horas hacia adelante"),
    ahora: datetime | None = Query(
        None, description="Momento de referencia en hora del casino (por defecto, ahora)"
    ),
    _: Usuario = Depends(requiere_roles(ANFITRION, GERENTE)),
    db: Session = Depends(get_db),
):
    """
    Envía un recordatorio a cada cliente con una reserva confirmada que
    empieza dentro de la ventana indicada y que aún no fue notificado.
    Pensado para ejecutarse periódicamente (cron/scheduler).
    """
    ahora = (ahora or ahora_casino()).replace(tzinfo=None)
    limite = ahora + timedelta(hours=horas)
    candidatas = (
        db.query(Reserva)
        .filter(
            Reserva.estado == "confirmada",
            Reserva.recordatorio_enviado.is_(False),
            Reserva.fecha >= ahora.date(),
            Reserva.fecha <= limite.date(),
        )
        .order_by(Reserva.fecha, Reserva.hora)
        .all()
    )
    enviadas: list[NotificacionDB] = []
    for reserva in candidatas:
        hh, mm = (int(x) for x in reserva.hora.split(":"))
        inicio = datetime(reserva.fecha.year, reserva.fecha.month, reserva.fecha.day, hh, mm)
        if not (ahora <= inicio <= limite):
            continue
        cuando = (
            f"hoy a las {reserva.hora}"
            if inicio.date() == ahora.date()
            else f"el {reserva.fecha.isoformat()} a las {reserva.hora}"
        )
        mensaje = (
            f"Recordatorio: tu reserva {reserva.codigo_confirmacion} es {cuando} "
            f"(mesa {reserva.mesa_id})."
        )
        enviadas.append(_enviar(db, reserva.cliente_id, TipoNotificacion.RESERVA_PROXIMA, mensaje))
        reserva.recordatorio_enviado = True
    db.commit()
    return [Notificacion.model_validate(n) for n in enviadas]


@router.get(
    "/{cliente_id}",
    response_model=list[Notificacion],
    summary="Historial de notificaciones de un cliente",
    responses=errores(401, 403, 404),
)
def listar_notificaciones(
    cliente_id: str, usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)
):
    """Historial de notificaciones del cliente, la más reciente primero."""
    cliente = resolver_cliente(db, usuario, cliente_id)
    filas = (
        db.query(NotificacionDB)
        .filter(NotificacionDB.cliente_id == cliente)
        .order_by(NotificacionDB.id.desc())
        .all()
    )
    return [Notificacion.model_validate(n) for n in filas]
