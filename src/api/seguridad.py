"""
Reglas transversales de juego responsable.

HU-11 (REQ-FUNC-011): un cliente autoexcluido queda bloqueado en toda la
plataforma (acumular puntos, canjear, gastar, recargar y reservar) hasta
que termine el periodo que él mismo definió.
"""

from datetime import date

from fastapi import HTTPException

from src.api.store import AUTOEXCLUSION_DB


def esta_autoexcluido(cliente_id: str, hoy: date | None = None) -> bool:
    """Indica si el cliente tiene una autoexclusión vigente."""
    hoy = hoy or date.today()
    fecha_fin = AUTOEXCLUSION_DB.get(cliente_id)
    return fecha_fin is not None and hoy < fecha_fin


def verificar_autoexclusion(cliente_id: str) -> None:
    """Lanza HTTP 403 si el cliente está autoexcluido."""
    if esta_autoexcluido(cliente_id):
        fecha_fin = AUTOEXCLUSION_DB[cliente_id]
        raise HTTPException(
            status_code=403,
            detail=f"Cliente autoexcluido hasta {fecha_fin.isoformat()}. Acceso bloqueado.",
        )
