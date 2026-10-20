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

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.api.models import EstadoReserva, Notificacion, TipoNotificacion
from src.api.seguridad import esta_autoexcluido
from src.api.store import NOTIFICACIONES_DB, RESERVAS_DB

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


def _enviar(cliente_id: str, tipo: TipoNotificacion, mensaje: str | None = None) -> Notificacion:
    notificacion = Notificacion(
        id=len(NOTIFICACIONES_DB) + 1,
        cliente_id=cliente_id,
        tipo=tipo,
        mensaje=mensaje or MENSAJES_POR_DEFECTO[tipo],
        enviada_en=datetime.now(timezone.utc),
    )
    NOTIFICACIONES_DB.append(notificacion)
    logger.info("PUSH -> %s [%s]: %s", cliente_id, tipo.value, notificacion.mensaje)
    return notificacion


@router.post("/enviar", response_model=Notificacion, status_code=201)
def enviar_notificacion(datos: EnvioRequest):
    """
    Envía una notificación push al cliente. Las promociones NO se envían a
    clientes autoexcluidos (409), por juego responsable.
    """
    if datos.tipo == TipoNotificacion.PROMOCION and esta_autoexcluido(datos.cliente_id):
        raise HTTPException(
            status_code=409,
            detail="No se envían promociones a clientes autoexcluidos.",
        )
    return _enviar(datos.cliente_id, datos.tipo, datos.mensaje)


@router.post("/reservas-proximas", response_model=list[Notificacion])
def notificar_reservas_proximas(
    horas: int = Query(2, ge=1, le=48, description="Ventana en horas hacia adelante"),
    ahora: datetime | None = Query(None, description="Momento de referencia (por defecto, ahora)"),
):
    """
    Envía un recordatorio a cada cliente con una reserva confirmada que
    empieza dentro de la ventana indicada y que aún no fue notificado.
    Pensado para ejecutarse periódicamente (cron/scheduler).
    """
    ahora = (ahora or datetime.now()).replace(tzinfo=None)
    limite = ahora + timedelta(hours=horas)
    enviadas: list[Notificacion] = []

    for reserva in RESERVAS_DB.values():
        if reserva.estado != EstadoReserva.CONFIRMADA or reserva.recordatorio_enviado:
            continue
        hh, mm = (int(x) for x in reserva.hora.split(":"))
        inicio = datetime(reserva.fecha.year, reserva.fecha.month, reserva.fecha.day, hh, mm)
        if ahora <= inicio <= limite:
            mensaje = (
                f"Recordatorio: tu reserva {reserva.codigo_confirmacion} es hoy a las "
                f"{reserva.hora} (mesa {reserva.mesa_id})."
                if inicio.date() == ahora.date()
                else f"Recordatorio: tu reserva {reserva.codigo_confirmacion} es el "
                f"{reserva.fecha.isoformat()} a las {reserva.hora} (mesa {reserva.mesa_id})."
            )
            enviadas.append(_enviar(reserva.cliente_id, TipoNotificacion.RESERVA_PROXIMA, mensaje))
            reserva.recordatorio_enviado = True
    return enviadas


@router.get("/{cliente_id}", response_model=list[Notificacion])
def listar_notificaciones(cliente_id: str):
    """Historial de notificaciones del cliente, la más reciente primero."""
    return [n for n in reversed(NOTIFICACIONES_DB) if n.cliente_id == cliente_id]
