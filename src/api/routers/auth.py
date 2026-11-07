"""
Autenticación: inicio de sesión con JWT.

REQ-NFUNC-003: la cuenta se bloquea tras 5 intentos fallidos de inicio de sesión.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api import config
from src.api.auth import crear_token, usuario_actual, verificar_password
from src.api.db import get_db
from src.api.errores import errores
from src.api.orm import Usuario

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    usuario: str = Field(..., min_length=1, description="Nombre de usuario")
    password: str = Field(..., min_length=1)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: str
    nombre: str
    rol: str


class Perfil(BaseModel):
    usuario: str
    nombre: str
    rol: str


@router.post(
    "/login",
    response_model=Token,
    summary="Iniciar sesión y obtener un token JWT",
    responses=errores(401, 423),
)
def login(datos: LoginRequest, db: Session = Depends(get_db)):
    """
    Valida las credenciales y emite un token JWT (`Authorization: Bearer ...`).

    - 401 si usuario o contraseña son incorrectos.
    - 423 si la cuenta está bloqueada: se bloquea durante
      `MINUTOS_BLOQUEO` minutos tras 5 intentos fallidos consecutivos.
    """
    usuario = db.query(Usuario).filter(Usuario.usuario == datos.usuario).one_or_none()
    ahora = datetime.now(timezone.utc)

    if usuario is not None and usuario.bloqueado_hasta and usuario.bloqueado_hasta > ahora:
        raise HTTPException(
            status_code=423,
            detail="Cuenta bloqueada por intentos fallidos. Intenta de nuevo más tarde.",
        )

    if usuario is None or not verificar_password(datos.password, usuario.password_hash):
        if usuario is not None:
            usuario.intentos_fallidos += 1
            if usuario.intentos_fallidos >= config.MAX_INTENTOS_LOGIN:
                usuario.bloqueado_hasta = ahora + timedelta(minutes=config.MINUTOS_BLOQUEO)
                usuario.intentos_fallidos = 0
                db.commit()
                raise HTTPException(
                    status_code=423,
                    detail="Cuenta bloqueada por 5 intentos fallidos. Intenta de nuevo más tarde.",
                )
            db.commit()
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")

    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    db.commit()
    return Token(
        access_token=crear_token(usuario),
        usuario=usuario.usuario,
        nombre=usuario.nombre,
        rol=usuario.rol,
    )


@router.get(
    "/me",
    response_model=Perfil,
    summary="Datos del usuario autenticado",
    responses=errores(401),
)
def perfil_actual(usuario: Usuario = Depends(usuario_actual)):
    """Devuelve el usuario dueño del token (sirve para validar la sesión)."""
    return Perfil(usuario=usuario.usuario, nombre=usuario.nombre, rol=usuario.rol)
