"""
Endpoints del Programa de Fidelidad.

HU-04: Acumulación automática de puntos (REQ-FUNC-004)
HU-05: Canje de puntos por beneficios (REQ-FUNC-005)
HU-11: Límites de autoexclusión y de gasto diario (REQ-FUNC-011)
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.auth import CAJERO, CLIENTE, GERENTE, requiere_roles, resolver_cliente, usuario_actual
from src.api.db import get_db
from src.api.errores import errores
from src.api.orm import Autoexclusion, Canje, GastoDiario, LimiteDiario, Puntos, Usuario
from src.api.seguridad import fecha_fin_autoexclusion, verificar_autoexclusion
from src.api.tiempo import hoy_casino

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


# --------------------------------------------------------------------- modelos
class AcumularRequest(BaseModel):
    cliente_id: str = Field(..., description="Cliente al que se le acreditan los puntos")
    monto_gastado: float = Field(..., gt=0, description="Monto del consumo en pesos")


class PuntosAcumulados(BaseModel):
    cliente_id: str
    puntos_ganados: int
    puntos_totales: int


class CanjeRequest(BaseModel):
    cliente_id: str | None = None
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
    cliente_id: str | None = None
    limite_diario: float = Field(..., gt=0, description="Gasto máximo permitido por día")


class LimiteDefinido(BaseModel):
    cliente_id: str
    limite_diario: float


class GastoRequest(BaseModel):
    cliente_id: str | None = None
    monto: float = Field(..., gt=0)


class GastoResultado(BaseModel):
    cliente_id: str
    permitido: bool
    gastado_hoy: float
    limite_diario: float | None = None
    mensaje: str


class AutoexclusionRequest(BaseModel):
    dias: int = Field(..., gt=0, le=3650, description="Duración del bloqueo en días")


class AutoexclusionConfirmada(BaseModel):
    cliente_id: str
    bloqueado_hasta: date


class EstadoAutoexclusion(BaseModel):
    cliente_id: str
    activa: bool
    bloqueado_hasta: date | None = None


# -------------------------------------------------------------------- endpoints
@router.post(
    "/acumular",
    response_model=PuntosAcumulados,
    summary="Acreditar puntos por un consumo",
    responses=errores(401, 403, 404),
)
def acumular_puntos(
    datos: AcumularRequest,
    _: Usuario = Depends(requiere_roles(CAJERO, GERENTE)),
    db: Session = Depends(get_db),
):
    """
    HU-04: la caja registra un consumo válido y se acreditan los puntos
    automáticamente (1 punto por cada $1.000). Un cliente autoexcluido no
    acumula puntos (403).
    """
    cliente = db.query(Usuario).filter(Usuario.usuario == datos.cliente_id, Usuario.rol == CLIENTE).first()
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    verificar_autoexclusion(db, datos.cliente_id)

    ganados = int(datos.monto_gastado // PESOS_POR_PUNTO)
    registro = db.get(Puntos, datos.cliente_id, with_for_update=True)
    if registro is None:
        registro = Puntos(cliente_id=datos.cliente_id, puntos=0)
        db.add(registro)
    registro.puntos += ganados
    db.commit()
    return PuntosAcumulados(
        cliente_id=datos.cliente_id, puntos_ganados=ganados, puntos_totales=registro.puntos
    )


@router.get(
    "/puntos/{cliente_id}",
    response_model=SaldoPuntos,
    summary="Consultar saldo de puntos",
    responses=errores(401, 403, 404),
)
def consultar_puntos(
    cliente_id: str, usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)
):
    """Consulta el saldo de puntos del cliente (0 si aún no ha acumulado)."""
    cliente = resolver_cliente(db, usuario, cliente_id)
    registro = db.get(Puntos, cliente)
    return SaldoPuntos(cliente_id=cliente, puntos=registro.puntos if registro else 0)


@router.get(
    "/beneficios",
    response_model=dict[str, int],
    summary="Catálogo de beneficios",
    responses=errores(401),
)
def listar_beneficios(_: Usuario = Depends(usuario_actual)):
    """Catálogo de beneficios canjeables y su costo en puntos."""
    return BENEFICIOS


@router.post(
    "/canjear",
    response_model=CanjeConfirmado,
    summary="Canjear puntos por un beneficio",
    responses=errores(401, 402, 403, 404),
)
def canjear_beneficio(
    datos: CanjeRequest, usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)
):
    """
    HU-05: canjea puntos por un beneficio del catálogo. El costo lo define
    el catálogo del sistema (no el cliente), se descuentan los puntos y se
    genera un cupón digital único.

    - 404 si el beneficio no existe.
    - 402 si el cliente no tiene puntos suficientes.
    """
    cliente = resolver_cliente(db, usuario, datos.cliente_id)
    verificar_autoexclusion(db, cliente)

    costo = BENEFICIOS.get(datos.beneficio)
    if costo is None:
        raise HTTPException(status_code=404, detail="El beneficio solicitado no existe.")

    registro = db.get(Puntos, cliente, with_for_update=True)
    actuales = registro.puntos if registro else 0
    if registro is None or actuales < costo:
        raise HTTPException(
            status_code=402,
            detail=f"Puntos insuficientes: se necesitan {costo} y el cliente tiene {actuales}.",
        )

    registro.puntos = actuales - costo
    cupon = uuid.uuid4().hex[:8].upper()
    db.add(Canje(cupon=cupon, cliente_id=cliente, beneficio=datos.beneficio, puntos_usados=costo))
    db.commit()
    return CanjeConfirmado(
        cupon=cupon, beneficio=datos.beneficio, puntos_usados=costo, puntos_restantes=registro.puntos
    )


@router.post(
    "/limite",
    response_model=LimiteDefinido,
    summary="Definir límite de gasto diario",
    responses=errores(401, 403, 404),
)
def definir_limite_diario(
    datos: LimiteRequest, usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)
):
    """HU-11: el cliente define su límite de gasto diario (juego responsable)."""
    cliente = resolver_cliente(db, usuario, datos.cliente_id)
    registro = db.get(LimiteDiario, cliente)
    limite = Decimal(str(datos.limite_diario))
    if registro is None:
        db.add(LimiteDiario(cliente_id=cliente, limite=limite))
    else:
        registro.limite = limite
    db.commit()
    return LimiteDefinido(cliente_id=cliente, limite_diario=datos.limite_diario)


@router.post(
    "/gasto",
    response_model=GastoResultado,
    summary="Registrar un gasto validando el límite diario",
    responses=errores(401, 403, 404),
)
def registrar_gasto(
    datos: GastoRequest, usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)
):
    """
    HU-11: registra un gasto del día si no supera el límite diario del
    cliente. Si lo supera, responde `permitido: false` y el gasto NO queda
    registrado. Sin límite definido, el gasto siempre se permite.
    """
    cliente = resolver_cliente(db, usuario, datos.cliente_id)
    verificar_autoexclusion(db, cliente)

    hoy = hoy_casino()
    gasto = db.get(GastoDiario, (cliente, hoy), with_for_update=True)
    if gasto is None:
        gasto = GastoDiario(cliente_id=cliente, fecha=hoy, monto=Decimal("0"))
        db.add(gasto)
        db.flush()
    limite_reg = db.get(LimiteDiario, cliente)
    limite = float(limite_reg.limite) if limite_reg else None
    monto = Decimal(str(datos.monto))

    if limite_reg is not None and gasto.monto + monto > limite_reg.limite:
        db.commit()
        return GastoResultado(
            cliente_id=cliente,
            permitido=False,
            gastado_hoy=float(gasto.monto),
            limite_diario=limite,
            mensaje="Gasto rechazado: supera el límite diario definido por el cliente.",
        )

    gasto.monto = gasto.monto + monto
    db.commit()
    return GastoResultado(
        cliente_id=cliente,
        permitido=True,
        gastado_hoy=float(gasto.monto),
        limite_diario=limite,
        mensaje="Gasto registrado.",
    )


@router.post(
    "/autoexclusion",
    response_model=AutoexclusionConfirmada,
    summary="Activar autoexclusión voluntaria",
    responses=errores(401, 403),
)
def establecer_autoexclusion(
    datos: AutoexclusionRequest,
    usuario: Usuario = Depends(requiere_roles(CLIENTE)),
    db: Session = Depends(get_db),
):
    """
    HU-11: el cliente establece un periodo de autoexclusión. Una vez activo
    no se puede cancelar ni acortar: si envía un periodo más corto que el
    vigente, se conserva el más largo (sin reversión anticipada).
    """
    nueva_fin = hoy_casino() + timedelta(days=datos.dias)
    registro = db.get(Autoexclusion, usuario.usuario)
    if registro is None:
        registro = Autoexclusion(cliente_id=usuario.usuario, fecha_fin=nueva_fin)
        db.add(registro)
    elif registro.fecha_fin < nueva_fin:
        registro.fecha_fin = nueva_fin
    db.commit()
    return AutoexclusionConfirmada(cliente_id=usuario.usuario, bloqueado_hasta=registro.fecha_fin)


@router.get(
    "/autoexclusion/{cliente_id}",
    response_model=EstadoAutoexclusion,
    summary="Consultar autoexclusión",
    responses=errores(401, 403, 404),
)
def consultar_autoexclusion(
    cliente_id: str, usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)
):
    """Consulta si el cliente tiene una autoexclusión vigente."""
    cliente = resolver_cliente(db, usuario, cliente_id)
    fin = fecha_fin_autoexclusion(db, cliente)
    return EstadoAutoexclusion(cliente_id=cliente, activa=fin is not None, bloqueado_hasta=fin)
