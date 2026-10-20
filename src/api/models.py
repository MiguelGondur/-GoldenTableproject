"""
Modelos de datos del dominio de GoldenTable.

HU-01 (REQ-FUNC-001): Mesa y su estado base.
HU-02 / HU-03 (REQ-FUNC-002, REQ-FUNC-003): Reserva y su ciclo de vida.
HU-09 (REQ-FUNC-009): Notificación push.
"""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field

# Formato de hora 24h "HH:MM" (00:00 a 23:59), usado en mesas, reservas y consultas.
PATRON_HORA = r"^([01]\d|2[0-3]):[0-5]\d$"


class EstadoMesa(str, Enum):
    DISPONIBLE = "disponible"
    RESERVADA = "reservada"
    OCUPADA = "ocupada"


class Mesa(BaseModel):
    id: int
    capacidad: int = Field(..., gt=0, description="Número máximo de personas que soporta la mesa")
    estado: EstadoMesa = EstadoMesa.DISPONIBLE
    horario: str = Field(..., description="Franja horaria a la que aplica este estado, formato 'HH:MM'")


class EstadoReserva(str, Enum):
    CONFIRMADA = "confirmada"
    EN_CURSO = "en_curso"


class Reserva(BaseModel):
    codigo_confirmacion: str
    mesa_id: int
    fecha: date
    hora: str
    cliente_id: str
    estado: EstadoReserva = EstadoReserva.CONFIRMADA
    recordatorio_enviado: bool = False
    creada_en: datetime
    check_in_en: datetime | None = None


class TipoNotificacion(str, Enum):
    RESERVA_PROXIMA = "reserva_proxima"
    PROMOCION = "promocion"
    VENCIMIENTO_PUNTOS = "vencimiento_puntos"


class Notificacion(BaseModel):
    id: int
    cliente_id: str
    tipo: TipoNotificacion
    mensaje: str
    canal: str = "push"
    estado: str = "enviada"
    enviada_en: datetime
