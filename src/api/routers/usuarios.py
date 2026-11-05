"""
Endpoints de Usuarios.

HU-10: Verificación de edad/identidad al registrarse (REQ-FUNC-010)
"""

import re
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.auth import CLIENTE, hashear_password, resolver_cliente, usuario_actual
from src.api.db import get_db
from src.api.errores import errores
from src.api.orm import Billetera, Puntos, Usuario
from src.api.tiempo import hoy_casino

router = APIRouter(prefix="/usuarios", tags=["usuarios"])

EDAD_MINIMA = 18


class RegistroUsuario(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=120)
    usuario: str = Field(..., description="Nombre de usuario: 3 a 30 caracteres [a-z0-9_.-]")
    password: str = Field(..., min_length=8, max_length=72)
    documento: str
    fecha_nacimiento: date

    @field_validator("usuario")
    @classmethod
    def usuario_valido(cls, v: str) -> str:
        if not re.fullmatch(r"[a-z0-9_.-]{3,30}", v):
            raise ValueError("El usuario debe tener 3 a 30 caracteres: minúsculas, números, _ . -")
        return v

    @field_validator("documento")
    @classmethod
    def documento_valido(cls, v: str) -> str:
        """El documento debe ser numérico, de 6 a 10 dígitos (verificación de identidad)."""
        if not re.fullmatch(r"\d{6,10}", v):
            raise ValueError("El documento debe tener entre 6 y 10 dígitos numéricos.")
        return v


class UsuarioRegistrado(BaseModel):
    usuario: str
    nombre: str
    documento: str
    edad: int
    rol: str
    cuenta_activa: bool


def calcular_edad(fecha_nacimiento: date, hoy: date | None = None) -> int:
    """Calcula la edad exacta en años a partir de la fecha de nacimiento."""
    hoy = hoy or hoy_casino()
    edad = hoy.year - fecha_nacimiento.year
    if (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day):
        edad -= 1
    return edad


def _a_respuesta(u: Usuario) -> UsuarioRegistrado:
    return UsuarioRegistrado(
        usuario=u.usuario,
        nombre=u.nombre,
        documento=u.documento,
        edad=calcular_edad(u.fecha_nacimiento),
        rol=u.rol,
        cuenta_activa=True,
    )


@router.post(
    "/registro",
    response_model=UsuarioRegistrado,
    status_code=201,
    summary="Registrar un cliente (verifica edad y documento)",
    responses=errores(403, 409),
)
def registrar_usuario(datos: RegistroUsuario, db: Session = Depends(get_db)):
    """
    HU-10: valida la edad y el documento del usuario al registrarse.

    - 403 si es menor de 18 años: no se crea la cuenta (juego responsable).
    - 409 si el documento o el nombre de usuario ya existen.
    - 422 si el documento no tiene entre 6 y 10 dígitos u otros datos son inválidos.

    Los registros públicos siempre crean usuarios con rol `cliente`; el
    personal del casino lo crea la administración.
    """
    edad = calcular_edad(datos.fecha_nacimiento)
    if edad < EDAD_MINIMA:
        raise HTTPException(
            status_code=403,
            detail=f"Registro rechazado: se requiere ser mayor de {EDAD_MINIMA} años.",
        )

    existente = (
        db.query(Usuario)
        .filter((Usuario.documento == datos.documento) | (Usuario.usuario == datos.usuario))
        .first()
    )
    if existente is not None:
        raise HTTPException(
            status_code=409, detail="Ya existe un usuario con ese documento o nombre de usuario."
        )

    nuevo = Usuario(
        usuario=datos.usuario,
        nombre=datos.nombre,
        documento=datos.documento,
        fecha_nacimiento=datos.fecha_nacimiento,
        password_hash=hashear_password(datos.password),
        rol=CLIENTE,
    )
    db.add(nuevo)
    try:
        db.flush()
        db.add(Puntos(cliente_id=nuevo.usuario, puntos=0))
        db.add(Billetera(cliente_id=nuevo.usuario))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Ya existe un usuario con ese documento o nombre de usuario."
        )
    return _a_respuesta(nuevo)


@router.get(
    "/{usuario}",
    response_model=UsuarioRegistrado,
    summary="Consultar un usuario",
    responses=errores(401, 403, 404),
)
def consultar_usuario(
    usuario: str,
    actual: Usuario = Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    """Un cliente consulta su propio perfil; el personal puede consultar a cualquier cliente."""
    if actual.rol == CLIENTE:
        resolver_cliente(db, actual, usuario)
        return _a_respuesta(actual)
    encontrado = db.query(Usuario).filter(Usuario.usuario == usuario).one_or_none()
    if encontrado is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return _a_respuesta(encontrado)
