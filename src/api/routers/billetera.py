"""
Endpoints de Billetera Digital.

HU-06: Recarga de saldo (REQ-FUNC-006)
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/billetera", tags=["billetera"])

# Almacenamiento en memoria — placeholder hasta integrar base de datos real.
BILLETERAS_DB: dict[str, float] = {}


class RecargaRequest(BaseModel):
    cliente_id: str
    monto: float = Field(..., gt=0, description="Monto a recargar; debe ser mayor a 0")
    metodo_pago: str


class Billetera(BaseModel):
    cliente_id: str
    saldo: float


@router.post("/recarga", response_model=Billetera)
def recargar_saldo(datos: RecargaRequest):
    """
    HU-06: recarga el saldo de la billetera digital del cliente.

    Los montos negativos o en cero son rechazados automáticamente por
    la validación `gt=0` del campo `monto` (FastAPI responde HTTP 422).
    """
    saldo_actual = BILLETERAS_DB.get(datos.cliente_id, 0.0)
    nuevo_saldo = saldo_actual + datos.monto
    BILLETERAS_DB[datos.cliente_id] = nuevo_saldo

    return Billetera(cliente_id=datos.cliente_id, saldo=nuevo_saldo)
