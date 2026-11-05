"""
Reglas transversales de juego responsable.

HU-11 (REQ-FUNC-011): un cliente autoexcluido queda bloqueado en toda la
plataforma (acumular puntos, canjear, gastar, recargar y reservar) hasta
que termine el periodo que él mismo definió.
"""

from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.api.orm import Autoexclusion
from src.api.tiempo import hoy_casino


def fecha_fin_autoexclusion(db: Session, cliente_id: str, hoy: date | None = None) -> date | None:
    """Fecha en que termina la autoexclusión vigente, o None si no hay una vigente."""
    hoy = hoy or hoy_casino()
    registro = db.get(Autoexclusion, cliente_id)
    if registro is not None and hoy < registro.fecha_fin:
        return registro.fecha_fin
    return None


def esta_autoexcluido(db: Session, cliente_id: str, hoy: date | None = None) -> bool:
    return fecha_fin_autoexclusion(db, cliente_id, hoy) is not None


def verificar_autoexclusion(db: Session, cliente_id: str) -> None:
    """Lanza HTTP 403 si el cliente está autoexcluido."""
    fecha_fin = fecha_fin_autoexclusion(db, cliente_id)
    if fecha_fin is not None:
        raise HTTPException(
            status_code=403,
            detail=f"Cliente autoexcluido hasta {fecha_fin.isoformat()}. Acceso bloqueado.",
        )
