"""
Endpoints de Usuarios.

HU-10: Verificación de edad/identidad y autoexclusión (REQ-FUNC-010)
"""

from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/usuarios", tags=["usuarios"])

EDAD_MINIMA = 18


class RegistroUsuario(BaseModel):
    nombre: str
    documento: str
    fecha_nacimiento: date


class UsuarioRegistrado(BaseModel):
    nombre: str
    documento: str
    edad: int
    cuenta_activa: bool


def calcular_edad(fecha_nacimiento: date, hoy: date | None = None) -> int:
    """Calcula la edad exacta en años a partir de la fecha de nacimiento."""
    hoy = hoy or date.today()
    edad = hoy.year - fecha_nacimiento.year
    if (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day):
        edad -= 1
    return edad


@router.post("/registro", response_model=UsuarioRegistrado)
def registrar_usuario(datos: RegistroUsuario):
    """
    HU-10: valida la edad del usuario al registrarse.

    Si el usuario es menor de 18 años, rechaza el registro (HTTP 403) y
    no activa la cuenta, cumpliendo con la normativa de juego responsable.
    """
    edad = calcular_edad(datos.fecha_nacimiento)

    if edad < EDAD_MINIMA:
        raise HTTPException(
            status_code=403,
            detail=f"Registro rechazado: se requiere ser mayor de {EDAD_MINIMA} años.",
        )

    return UsuarioRegistrado(
        nombre=datos.nombre,
        documento=datos.documento,
        edad=edad,
        cuenta_activa=True,
    )
