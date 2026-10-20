"""
Endpoints del Programa de Fidelidad.

HU-04: Acumulación automática de puntos (REQ-FUNC-004)
HU-05: Canje de puntos por beneficios (REQ-FUNC-005)
HU-11: Límites de autoexclusión y de gasto diario (REQ-FUNC-011)
"""

import uuid
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.api.seguridad import esta_autoexcluido, verificar_autoexclusion
from src.api.store import AUTOEXCLUSION_DB

router = APIRouter(prefix="/fidelidad", tags=["fidelidad"])

# Se acredita 1 punto por cada $1.000 gastados (REQ-FUNC-004).
PESOS_POR_PUNTO = 1000

# Catálogo de beneficios canjeables y su costo en puntos (REQ-FUNC-005).
BENEFICIOS: dict[str, int] = {
    "bebida_gratis": 50,
    "entrada_evento": 150,
    "cena_vip": 300,
    "noche_hotel": 500,
}

# Almacenamiento en memoria — placeholder hasta integrar base de datos real.
# "cliente-demo" arranca con 500 puntos para poder probar el flujo end-to-end.
PUNTOS_DB: dict[str, int] = {"cliente-demo": 500}
LIMITES_DIARIOS_DB: dict[str, float] = {}
GASTO_DIARIO_DB: dict[tuple[str, date], float] = {}


# --------------------------------------------------------------------- modelos
class AcumularRequest(BaseModel):
    cliente_id: str
    monto_gastado: float = Field(..., gt=0, description="Monto del consumo en pesos")


class PuntosAcumulados(BaseModel):
    cliente_id: str
    puntos_ganados: int
    puntos_totales: int


class CanjeRequest(BaseModel):
    cliente_id: str
    beneficio: str = Field(..., description="Clave del beneficio del catálogo")


class CanjeConfirmado(BaseModel):
    cupon: str
    beneficio: str
    puntos_usados: int
    puntos_restantes: int


class SaldoPuntos(BaseModel):
    cliente_id: str
    puntos: int


class LimiteRequest(BaseModel):
    cliente_id: str
    limite_diario: float = Field(..., gt=0, description="Gasto máximo permitido por día")


class LimiteDefinido(BaseModel):
    cliente_id: str
    limite_diario: float


class GastoRequest(BaseModel):
    cliente_id: str
    monto: float = Field(..., gt=0)


class GastoResultado(BaseModel):
    cliente_id: str
    permitido: bool
    gastado_hoy: float
    limite_diario: float | None = None
    mensaje: str


class AutoexclusionRequest(BaseModel):
    cliente_id: str
    dias: int = Field(..., gt=0, le=3650, description="Duración del bloqueo en días")


class AutoexclusionConfirmada(BaseModel):
    cliente_id: str
    bloqueado_hasta: date


class EstadoAutoexclusion(BaseModel):
    cliente_id: str
    activa: bool
    bloqueado_hasta: date | None = None


# -------------------------------------------------------------------- endpoints
@router.post("/acumular", response_model=PuntosAcumulados)
def acumular_puntos(datos: AcumularRequest):
    """
    HU-04: acredita puntos automáticamente según el monto consumido
    (1 punto por cada $1.000). Un cliente autoexcluido no acumula puntos.
    """
    verificar_autoexclusion(datos.cliente_id)

    puntos_ganados = int(datos.monto_gastado // PESOS_POR_PUNTO)
    PUNTOS_DB[datos.cliente_id] = PUNTOS_DB.get(datos.cliente_id, 0) + puntos_ganados

    return PuntosAcumulados(
        cliente_id=datos.cliente_id,
        puntos_ganados=puntos_ganados,
        puntos_totales=PUNTOS_DB[datos.cliente_id],
    )


@router.get("/puntos/{cliente_id}", response_model=SaldoPuntos)
def consultar_puntos(cliente_id: str):
    """Consulta el saldo de puntos del cliente (0 si aún no ha acumulado)."""
    return SaldoPuntos(cliente_id=cliente_id, puntos=PUNTOS_DB.get(cliente_id, 0))


@router.get("/beneficios", response_model=dict[str, int])
def listar_beneficios():
    """Catálogo de beneficios canjeables y su costo en puntos."""
    return BENEFICIOS


@router.post("/canjear", response_model=CanjeConfirmado)
def canjear_beneficio(datos: CanjeRequest):
    """
    HU-05: canjea puntos por un beneficio del catálogo. El costo lo define
    el catálogo del sistema (no el cliente), se descuentan los puntos y se
    genera un cupón digital único.

    - 404 si el beneficio no existe.
    - 402 si el cliente no tiene puntos suficientes.
    """
    verificar_autoexclusion(datos.cliente_id)

    costo = BENEFICIOS.get(datos.beneficio)
    if costo is None:
        raise HTTPException(status_code=404, detail="El beneficio solicitado no existe.")

    puntos_actuales = PUNTOS_DB.get(datos.cliente_id, 0)
    if puntos_actuales < costo:
        raise HTTPException(
            status_code=402,
            detail=f"Puntos insuficientes: se necesitan {costo} y el cliente tiene {puntos_actuales}.",
        )

    PUNTOS_DB[datos.cliente_id] = puntos_actuales - costo
    return CanjeConfirmado(
        cupon=uuid.uuid4().hex[:8].upper(),
        beneficio=datos.beneficio,
        puntos_usados=costo,
        puntos_restantes=PUNTOS_DB[datos.cliente_id],
    )


@router.post("/limite", response_model=LimiteDefinido)
def definir_limite_diario(datos: LimiteRequest):
    """HU-11: el cliente define su límite de gasto diario (juego responsable)."""
    LIMITES_DIARIOS_DB[datos.cliente_id] = datos.limite_diario
    return LimiteDefinido(cliente_id=datos.cliente_id, limite_diario=datos.limite_diario)


@router.post("/gasto", response_model=GastoResultado)
def registrar_gasto(datos: GastoRequest):
    """
    HU-11: registra un gasto del día si no supera el límite diario del
    cliente. Si lo supera, responde `permitido: false` y el gasto NO queda
    registrado. Sin límite definido, el gasto siempre se permite.
    """
    verificar_autoexclusion(datos.cliente_id)

    clave = (datos.cliente_id, date.today())
    gastado_hoy = GASTO_DIARIO_DB.get(clave, 0.0)
    limite = LIMITES_DIARIOS_DB.get(datos.cliente_id)

    if limite is not None and gastado_hoy + datos.monto > limite:
        return GastoResultado(
            cliente_id=datos.cliente_id,
            permitido=False,
            gastado_hoy=gastado_hoy,
            limite_diario=limite,
            mensaje="Gasto rechazado: supera el límite diario definido por el cliente.",
        )

    GASTO_DIARIO_DB[clave] = gastado_hoy + datos.monto
    return GastoResultado(
        cliente_id=datos.cliente_id,
        permitido=True,
        gastado_hoy=GASTO_DIARIO_DB[clave],
        limite_diario=limite,
        mensaje="Gasto registrado.",
    )


@router.post("/autoexclusion", response_model=AutoexclusionConfirmada)
def establecer_autoexclusion(datos: AutoexclusionRequest):
    """
    HU-11: establece un periodo de autoexclusión. Una vez activo no se puede
    cancelar ni acortar: si el cliente envía un periodo más corto que el
    vigente, se conserva el más largo (sin reversión anticipada).
    """
    nueva_fecha_fin = date.today() + timedelta(days=datos.dias)
    fecha_vigente = AUTOEXCLUSION_DB.get(datos.cliente_id)
    if fecha_vigente is not None and fecha_vigente > nueva_fecha_fin:
        nueva_fecha_fin = fecha_vigente

    AUTOEXCLUSION_DB[datos.cliente_id] = nueva_fecha_fin
    return AutoexclusionConfirmada(cliente_id=datos.cliente_id, bloqueado_hasta=nueva_fecha_fin)


@router.get("/autoexclusion/{cliente_id}", response_model=EstadoAutoexclusion)
def consultar_autoexclusion(cliente_id: str):
    """Consulta si el cliente tiene una autoexclusión vigente."""
    activa = esta_autoexcluido(cliente_id)
    return EstadoAutoexclusion(
        cliente_id=cliente_id,
        activa=activa,
        bloqueado_hasta=AUTOEXCLUSION_DB.get(cliente_id) if activa else None,
    )
