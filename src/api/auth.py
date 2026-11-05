"""
Autenticación y autorización.

- Contraseñas con PBKDF2-HMAC-SHA256 (biblioteca estándar) y sal aleatoria.
- Sesión con JWT (HS256); el token se envía en `Authorization: Bearer <token>`.
- Roles: cliente, anfitrion, cajero, gerente (STK del SRS).
"""

import hashlib
import os
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.api import config
from src.api.db import get_db
from src.api.orm import Usuario

CLIENTE = "cliente"
ANFITRION = "anfitrion"
CAJERO = "cajero"
GERENTE = "gerente"
PERSONAL = (ANFITRION, CAJERO, GERENTE)

_ITERACIONES = int(os.getenv("PBKDF2_ITERACIONES", "200000"))

# auto_error=False: respondemos nosotros 401 (HTTPBearer respondería 403 sin token).
esquema_bearer = HTTPBearer(auto_error=False, description="Token JWT obtenido en POST /auth/login")


def hashear_password(password: str) -> str:
    sal = secrets.token_hex(16)
    derivado = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(sal), _ITERACIONES)
    return f"pbkdf2_sha256${_ITERACIONES}${sal}${derivado.hex()}"


def verificar_password(password: str, almacenado: str) -> bool:
    try:
        _, iteraciones, sal, esperado = almacenado.split("$")
        derivado = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(sal), int(iteraciones))
    except ValueError:
        return False
    return hmac.compare_digest(derivado.hex(), esperado)


def crear_token(usuario: Usuario) -> str:
    ahora = datetime.now(timezone.utc)
    claims = {
        "sub": usuario.usuario,
        "rol": usuario.rol,
        "iat": ahora,
        "exp": ahora + timedelta(minutes=config.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(claims, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def _no_autenticado(detalle: str) -> HTTPException:
    return HTTPException(
        status_code=401, detail=detalle, headers={"WWW-Authenticate": "Bearer"}
    )


def usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(esquema_bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    """Devuelve el usuario del token; 401 si falta, es inválido o expiró."""
    if credenciales is None:
        raise _no_autenticado("No autenticado: falta el token de acceso.")
    try:
        datos = jwt.decode(
            credenciales.credentials, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise _no_autenticado("La sesión expiró. Inicia sesión de nuevo.")
    except jwt.InvalidTokenError:
        raise _no_autenticado("Token inválido.")

    usuario = db.query(Usuario).filter(Usuario.usuario == datos.get("sub")).one_or_none()
    if usuario is None:
        raise _no_autenticado("El usuario del token ya no existe.")
    return usuario


def requiere_roles(*roles: str):
    """Dependencia que exige que el usuario tenga alguno de los roles (403 si no)."""

    def dependencia(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
        if usuario.rol not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Tu rol ({usuario.rol}) no tiene permiso para esta operación.",
            )
        return usuario

    return dependencia


def resolver_cliente(db: Session, usuario: Usuario, cliente_id: str | None) -> str:
    """
    Determina sobre qué cliente se opera.

    - Un cliente solo opera sobre sí mismo (si indica otro cliente_id: 403).
    - El personal debe indicar el cliente_id, que debe existir (404 si no).
    """
    if usuario.rol == CLIENTE:
        if cliente_id not in (None, usuario.usuario):
            raise HTTPException(status_code=403, detail="Solo puedes operar sobre tu propia cuenta.")
        return usuario.usuario

    if not cliente_id:
        raise HTTPException(status_code=422, detail="El personal debe indicar el cliente_id.")
    existe = (
        db.query(Usuario.id)
        .filter(Usuario.usuario == cliente_id, Usuario.rol == CLIENTE)
        .first()
    )
    if existe is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    return cliente_id
