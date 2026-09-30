"""
Endpoints del Programa de Fidelidad.

HU-04: Acumulación automática de puntos (REQ-FUNC-004)
HU-05: Canje de puntos por beneficios (REQ-FUNC-005)
HU-11: Límites de autoexclusión (REQ-FUNC-011)
"""

from datetime import date as date_type

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/fidelidad", tags=["fidelidad"])

# Almacenamiento en memoria — placeholder hasta integrar base de datos real.
PUNTOS_DB: dict[str, int] = {}
LIMITES_DB: dict[str, float] = {}
GASTO_DIARIO_DB: dict[str, dict[date_type, float]] = {}

# 1 punto por cada 1000 pesos gastados/recargados (regla simple, ajustable).
PESOS_POR_PUNTO = 1000

# Catálogo de beneficios canjeables: nombre -> costo en puntos.
CATALOGO_BENEFICIOS: dict[str, int] = {
    "bebida_gratis": 50,
    "descuento_10": 100,
    "cena_vip": 300,
}


class AcumulacionRequest(BaseModel):
    cliente_id: str
    monto_gastado: float = Field(..., gt=0, description="Monto de la transacción que genera puntos")


class PuntosFidelidad(BaseModel):
    cliente_id: str
    puntos_ganados: int
    puntos_totales: int


class CanjeRequest(BaseModel):
    cliente_id: str
    beneficio: str


class CanjeResponse(BaseModel):
    cliente_id: str
    beneficio: str
    puntos_usados: int
    puntos_restantes: int


class LimiteRequest(BaseModel):
    cliente_id: str
    limite_diario: float = Field(..., gt=0, description="Monto máximo que el cliente se permite gastar por día")


class LimiteResponse(BaseModel):
    cliente_id: str
    limite_diario: float


class RegistroGastoRequest(BaseModel):
    cliente_id: str
    monto: float = Field(..., gt=0)


class RegistroGastoResponse(BaseModel):
    cliente_id: str
    permitido: bool
    gastado_hoy: float
    limite_diario: float


@router.post("/acumular", response_model=PuntosFidelidad)
def acumular_puntos(datos: AcumulacionRequest):
    """
    HU-04: suma puntos de fidelidad automáticamente según el monto de una
    transacción (recarga o consumo) del cliente.
    """
    puntos_ganados = int(datos.monto_gastado // PESOS_POR_PUNTO)
    puntos_actuales = PUNTOS_DB.get(datos.cliente_id, 0)
    nuevos_puntos_totales = puntos_actuales + puntos_ganados
    PUNTOS_DB[datos.cliente_id] = nuevos_puntos_totales

    return PuntosFidelidad(
        cliente_id=datos.cliente_id,
        puntos_ganados=puntos_ganados,
        puntos_totales=nuevos_puntos_totales,
    )


@router.post("/canjear", response_model=CanjeResponse)
def canjear_puntos(datos: CanjeRequest):
    """
    HU-05: canjea los puntos acumulados del cliente por un beneficio del
    catálogo, siempre que tenga puntos suficientes.
    """
    if datos.beneficio not in CATALOGO_BENEFICIOS:
        raise HTTPException(status_code=404, detail="Beneficio no existe en el catálogo")

    costo = CATALOGO_BENEFICIOS[datos.beneficio]
    puntos_actuales = PUNTOS_DB.get(datos.cliente_id, 0)

    if puntos_actuales < costo:
        raise HTTPException(status_code=402, detail="Puntos insuficientes para este beneficio")

    puntos_restantes = puntos_actuales - costo
    PUNTOS_DB[datos.cliente_id] = puntos_restantes

    return CanjeResponse(
        cliente_id=datos.cliente_id,
        beneficio=datos.beneficio,
        puntos_usados=costo,
        puntos_restantes=puntos_restantes,
    )


@router.post("/limite", response_model=LimiteResponse)
def definir_limite(datos: LimiteRequest):
    """
    HU-11: permite al cliente fijar (o actualizar) su límite de gasto
    diario, como herramienta de juego responsable / autoexclusión.
    """
    LIMITES_DB[datos.cliente_id] = datos.limite_diario
    return LimiteResponse(cliente_id=datos.cliente_id, limite_diario=datos.limite_diario)


@router.post("/gasto", response_model=RegistroGastoResponse)
def registrar_gasto(datos: RegistroGastoRequest):
    """
    HU-11: registra un intento de gasto del cliente y valida contra su
    límite diario de autoexclusión. Si no ha definido un límite, se
    permite el gasto sin restricción (todavía no activó la función).
    """
    limite_diario = LIMITES_DB.get(datos.cliente_id)
    hoy = date_type.today()
    gastos_cliente = GASTO_DIARIO_DB.setdefault(datos.cliente_id, {})
    gastado_hoy = gastos_cliente.get(hoy, 0.0)

    if limite_diario is not None and (gastado_hoy + datos.monto) > limite_diario:
        return RegistroGastoResponse(
            cliente_id=datos.cliente_id,
            permitido=False,
            gastado_hoy=gastado_hoy,
            limite_diario=limite_diario,
        )

    gastos_cliente[hoy] = gastado_hoy + datos.monto

    return RegistroGastoResponse(
        cliente_id=datos.cliente_id,
        permitido=True,
        gastado_hoy=gastos_cliente[hoy],
        limite_diario=limite_diario if limite_diario is not None else 0.0,
    )
