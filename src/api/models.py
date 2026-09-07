"""
Modelos de datos del dominio de Reservas.

HU-01: Consulta de disponibilidad en tiempo real (REQ-FUNC-001)
"""

from enum import Enum

from pydantic import BaseModel, Field


class EstadoMesa(str, Enum):
    DISPONIBLE = "disponible"
    RESERVADA = "reservada"
    OCUPADA = "ocupada"


class Mesa(BaseModel):
    id: int
    capacidad: int = Field(..., gt=0, description="Número máximo de personas que soporta la mesa")
    estado: EstadoMesa = EstadoMesa.DISPONIBLE
    horario: str = Field(..., description="Franja horaria a la que aplica este estado, formato 'HH:MM'")
