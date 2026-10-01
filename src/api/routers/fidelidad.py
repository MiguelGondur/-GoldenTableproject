"""
Endpoints del Programa de Fidelidad.

HU-04: Acumulación automática de puntos (REQ-FUNC-004)
HU-05: Canje de puntos por beneficios (REQ-FUNC-005)
HU-11: Límites de autoexclusión (REQ-FUNC-011)
"""

import uuid
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/fidelidad", tags=["fidelidad"])

# Saldo de puntos por cliente — placeholder hasta integrar base de datos real.
# "cliente-demo" arranca con 500 puntos para poder probar el flujo end-to-end.
PUNTOS_DB: dict[str, int] = {
    "cliente-demo": 500,
}

# Autoexclusiones activas por cliente: cliente_id -> fecha en la que termina el bloqueo.
AUTOEXCLUSION_DB: dict[str, date] = {}

PUNTOS_POR_PESO = 0.01  # 1 punto por cada $100 de consumo (regla simple para REQ-FUNC-004)


class ConsumoRequest(BaseModel):
    cliente_id: str
    monto_consumo: float = Field(..., gt=0)


class PuntosAcreditados(BaseModel):
    cliente_id: str
    puntos_acreditados: int
    puntos_totales: int


class CanjeRequest(BaseModel):
    cliente_id: str
    beneficio: str
    costo_en_puntos: int = Field(..., gt=0)


class CanjeConfirmado(BaseModel):
    cupon: str
    beneficio: str
    puntos_restantes: int


class AutoexclusionRequest(BaseModel):
    cliente_id: str
    dias: int = Field(..., gt=0, description="Duración del bloqueo en días")


class AutoexclusionConfirmada(BaseModel):
    cliente_id: str
    bloqueado_hasta: date


def _verificar_autoexclusion(cliente_id: str) -> None:
    """Lanza HTTP 403 si el cliente tiene una autoexclusión activa (HU-11)."""
    fecha_fin = AUTOEXCLUSION_DB.get(cliente_id)
    if fecha_fin and date.today() < fecha_fin:
        raise HTTPException(
            status_code=403,
            detail=f"Cliente autoexcluido hasta {fecha_fin.isoformat()}. Acceso bloqueado.",
        )


@router.post("/acumular", response_model=PuntosAcreditados)
def acumular_puntos(datos: ConsumoRequest):
    """
    HU-04: acredita puntos automáticamente según el consumo registrado
    del cliente. Respeta cualquier autoexclusión activa (HU-11): un
    cliente excluido no puede seguir acumulando puntos.
    """
    _verificar_autoexclusion(datos.cliente_id)

    puntos_nuevos = int(datos.monto_consumo * PUNTOS_POR_PESO)
    puntos_actuales = PUNTOS_DB.get(datos.cliente_id, 0)
    PUNTOS_DB[datos.cliente_id] = puntos_actuales + puntos_nuevos

    return PuntosAcreditados(
        cliente_id=datos.cliente_id,
        puntos_acreditados=puntos_nuevos,
        puntos_totales=PUNTOS_DB[datos.cliente_id],
    )


@router.post("/canje", response_model=CanjeConfirmado)
def canjear_puntos(datos: CanjeRequest):
    """
    HU-05: canjea los puntos del cliente por un beneficio, descuenta el
    saldo de puntos y genera un cupón digital único.
    """
    _verificar_autoexclusion(datos.cliente_id)

    puntos_actuales = PUNTOS_DB.get(datos.cliente_id, 0)

    if puntos_actuales < datos.costo_en_puntos:
        raise HTTPException(status_code=409, detail="Puntos insuficientes para este canje.")

    PUNTOS_DB[datos.cliente_id] = puntos_actuales - datos.costo_en_puntos
    cupon = str(uuid.uuid4())[:8].upper()

    return CanjeConfirmado(
        cupon=cupon,
        beneficio=datos.beneficio,
        puntos_restantes=PUNTOS_DB[datos.cliente_id],
    )


@router.post("/autoexclusion", response_model=AutoexclusionConfirmada)
def establecer_autoexclusion(datos: AutoexclusionRequest):
    """
    HU-11: establece un período de autoexclusión para el cliente, para
    promover el juego responsable. Una vez activo, no existe endpoint
    para cancelarlo anticipadamente (por diseño, según el requisito).
    """
    fecha_fin = date.today() + timedelta(days=datos.dias)
    AUTOEXCLUSION_DB[datos.cliente_id] = fecha_fin

    return AutoexclusionConfirmada(cliente_id=datos.cliente_id, bloqueado_hasta=fecha_fin)
