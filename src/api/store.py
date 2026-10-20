"""
Estado compartido en memoria del sistema.

Es un placeholder hasta integrar una base de datos real (ver
docs/DEUDA_TECNICA.md). Se centraliza aquí para que varios routers
(disponibilidad, reservas, notificaciones, seguridad) lean y modifiquen
los mismos datos en vez de mantener copias que se desincronizan.
"""

from datetime import date

from src.api.models import EstadoMesa, Mesa, Notificacion, Reserva


def _mesas_iniciales() -> list[Mesa]:
    return [
        Mesa(id=1, capacidad=2, estado=EstadoMesa.DISPONIBLE, horario="18:00"),
        Mesa(id=2, capacidad=4, estado=EstadoMesa.DISPONIBLE, horario="18:00"),
        Mesa(id=3, capacidad=4, estado=EstadoMesa.RESERVADA, horario="19:00"),
        Mesa(id=4, capacidad=6, estado=EstadoMesa.DISPONIBLE, horario="19:00"),
        Mesa(id=5, capacidad=2, estado=EstadoMesa.OCUPADA, horario="20:00"),
        Mesa(id=6, capacidad=4, estado=EstadoMesa.DISPONIBLE, horario="20:00"),
        Mesa(id=7, capacidad=8, estado=EstadoMesa.DISPONIBLE, horario="18:00"),
        Mesa(id=8, capacidad=2, estado=EstadoMesa.DISPONIBLE, horario="21:00"),
    ]


# Catálogo de mesas (estado base de cada franja horaria).
MESAS_DB: list[Mesa] = _mesas_iniciales()

# Reservas por código de confirmación (HU-02, HU-03).
RESERVAS_DB: dict[str, Reserva] = {}

# Registro de notificaciones push enviadas (HU-09).
NOTIFICACIONES_DB: list[Notificacion] = []

# Autoexclusiones activas: cliente_id -> fecha en la que termina el bloqueo (HU-11).
AUTOEXCLUSION_DB: dict[str, date] = {}

# Usuarios registrados: documento -> datos del usuario (HU-10).
USUARIOS_DB: dict[str, dict] = {}


def mesas_disponibles(fecha: date, hora: str) -> list[Mesa]:
    """
    Mesas libres para una fecha y hora: estado base 'disponible', franja
    horaria igual a la solicitada y sin una reserva activa ese día.
    """
    mesas_reservadas = {
        reserva.mesa_id
        for reserva in RESERVAS_DB.values()
        if reserva.fecha == fecha and reserva.hora == hora
    }
    return [
        mesa
        for mesa in MESAS_DB
        if mesa.estado == EstadoMesa.DISPONIBLE
        and mesa.horario == hora
        and mesa.id not in mesas_reservadas
    ]


def reset_state() -> None:
    """Restablece el estado compartido (se usa para aislar las pruebas)."""
    MESAS_DB[:] = _mesas_iniciales()
    RESERVAS_DB.clear()
    NOTIFICACIONES_DB.clear()
    AUTOEXCLUSION_DB.clear()
    USUARIOS_DB.clear()
