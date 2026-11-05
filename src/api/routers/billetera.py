"""
Endpoints de la Billetera Digital.

HU-06: Recarga de saldo (REQ-FUNC-006)
HU-07: Consulta de saldo e historial (REQ-FUNC-007)
HU-08: Validación de saldo en caja (REQ-FUNC-008)
HU-12: Reportes de transacciones en CSV (REQ-FUNC-012)
"""

import csv
import io
from datetime import date as date_type
from datetime import datetime, time, timezone
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.auth import ANFITRION, CAJERO, GERENTE, requiere_roles, resolver_cliente, usuario_actual
from src.api.db import get_db
from src.api.errores import errores
from src.api.orm import Billetera as BilleteraDB
from src.api.orm import Transaccion as TransaccionDB
from src.api.orm import Usuario
from src.api.seguridad import verificar_autoexclusion

router = APIRouter(prefix="/billetera", tags=["billetera"])

MAX_TRANSACCIONES_HISTORIAL = 20


class CSVResponse(StreamingResponse):
    """Respuesta CSV (documenta text/csv en OpenAPI en lugar de application/json)."""

    media_type = "text/csv"


class RecargaRequest(BaseModel):
    cliente_id: str | None = Field(
        default=None, description="Solo para el personal (recarga en caja); el cliente recarga la suya"
    )
    monto: float = Field(..., gt=0, description="Monto a recargar; debe ser mayor a 0")
    metodo_pago: Literal["tarjeta", "pse", "efectivo"]


class Billetera(BaseModel):
    cliente_id: str
    saldo: float


class Transaccion(BaseModel):
    cliente_id: str
    tipo: str
    monto: float
    saldo_resultante: float
    fecha: datetime


class HistorialBilletera(BaseModel):
    cliente_id: str
    saldo: float
    transacciones: list[Transaccion]


class ValidacionSaldo(BaseModel):
    cliente_id: str
    saldo_disponible: float
    monto_requerido: float
    valido: bool


def _a_transaccion(t: TransaccionDB) -> Transaccion:
    return Transaccion(
        cliente_id=t.cliente_id,
        tipo=t.tipo,
        monto=float(t.monto),
        saldo_resultante=float(t.saldo_resultante),
        fecha=t.fecha,
    )


@router.post(
    "/recarga",
    response_model=Billetera,
    summary="Recargar saldo",
    responses=errores(401, 403, 404),
)
def recargar_saldo(
    datos: RecargaRequest,
    usuario: Usuario = Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    """
    HU-06: recarga el saldo de la billetera digital.

    Los montos negativos o en cero y los medios de pago no válidos se
    rechazan con 422. Un cliente autoexcluido no puede recargar (403).
    """
    cliente_id = resolver_cliente(db, usuario, datos.cliente_id)
    verificar_autoexclusion(db, cliente_id)

    billetera = db.get(BilleteraDB, cliente_id, with_for_update=True)
    if billetera is None:
        billetera = BilleteraDB(cliente_id=cliente_id, saldo=Decimal("0"))
        db.add(billetera)
    monto = Decimal(str(datos.monto))
    billetera.saldo = billetera.saldo + monto
    db.add(
        TransaccionDB(
            cliente_id=cliente_id,
            tipo="recarga",
            monto=monto,
            saldo_resultante=billetera.saldo,
            metodo_pago=datos.metodo_pago,
            fecha=datetime.now(timezone.utc),
        )
    )
    db.commit()
    return Billetera(cliente_id=cliente_id, saldo=float(billetera.saldo))


@router.get(
    "/validar",
    response_model=ValidacionSaldo,
    summary="Validar saldo en caja",
    responses=errores(401, 403, 404),
)
def validar_saldo(
    cliente_id: str | None = Query(
        default=None, description="Código del cliente escaneado en caja (obligatorio para el personal)"
    ),
    monto_requerido: float = Query(
        default=0.0, ge=0, description="Monto en fichas que el cajero necesita autorizar"
    ),
    usuario: Usuario = Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    """
    HU-08: valida en caja si el cliente tiene saldo suficiente para una
    operación con fichas por `monto_requerido`. Lo usa el cajero (o el
    gerente); un cliente solo puede validar su propio saldo.
    """
    if usuario.rol == ANFITRION:
        raise HTTPException(status_code=403, detail="El anfitrión no valida saldos en caja.")
    cliente = resolver_cliente(db, usuario, cliente_id)
    billetera = db.get(BilleteraDB, cliente)
    saldo = float(billetera.saldo) if billetera else 0.0
    return ValidacionSaldo(
        cliente_id=cliente,
        saldo_disponible=saldo,
        monto_requerido=monto_requerido,
        valido=saldo >= monto_requerido,
    )


@router.get(
    "/reportes",
    response_class=CSVResponse,
    summary="Reporte de transacciones (CSV)",
    responses={
        200: {
            "description": "Archivo CSV con las transacciones del periodo.",
            "content": {"text/csv": {"schema": {"type": "string"}}},
        },
        **errores(401, 403),
    },
)
def generar_reporte(
    fecha_inicio: date_type | None = Query(
        default=None, description="Filtra transacciones desde esta fecha (YYYY-MM-DD)"
    ),
    fecha_fin: date_type | None = Query(
        default=None, description="Filtra transacciones hasta esta fecha (YYYY-MM-DD)"
    ),
    _: Usuario = Depends(requiere_roles(GERENTE)),
    db: Session = Depends(get_db),
):
    """
    HU-12: genera un reporte exportable (CSV) de las recargas y
    transacciones, para que el gerente de operaciones audite el flujo de
    caja digital. Se puede filtrar por rango de fechas.
    """
    consulta = db.query(TransaccionDB)
    if fecha_inicio is not None:
        consulta = consulta.filter(
            TransaccionDB.fecha >= datetime.combine(fecha_inicio, time.min, tzinfo=timezone.utc)
        )
    if fecha_fin is not None:
        consulta = consulta.filter(
            TransaccionDB.fecha <= datetime.combine(fecha_fin, time.max, tzinfo=timezone.utc)
        )

    buffer = io.StringIO()
    escritor = csv.writer(buffer)
    escritor.writerow(["cliente_id", "tipo", "monto", "saldo_resultante", "fecha"])
    for t in consulta.order_by(TransaccionDB.fecha, TransaccionDB.id):
        escritor.writerow(
            [t.cliente_id, t.tipo, float(t.monto), float(t.saldo_resultante), t.fecha.isoformat()]
        )
    buffer.seek(0)

    return CSVResponse(
        buffer,
        headers={"Content-Disposition": "attachment; filename=reporte_billetera.csv"},
    )


# IMPORTANTE: esta ruta debe declararse DESPUÉS de "/validar" y "/reportes". Al tener un
# parámetro dinámico ({cliente_id}), FastAPI la usaría para *cualquier*
# texto en esa posición — incluida la palabra "validar" — si quedara antes.
@router.get(
    "/{cliente_id}",
    response_model=HistorialBilletera,
    summary="Saldo e historial (últimas 20 transacciones)",
    responses=errores(401, 403, 404),
)
def consultar_saldo_e_historial(
    cliente_id: str,
    usuario: Usuario = Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    """
    HU-07: retorna el saldo actual del cliente y sus últimas 20
    transacciones, de la más reciente a la más antigua.
    """
    cliente = resolver_cliente(db, usuario, cliente_id)
    billetera = db.get(BilleteraDB, cliente)
    if billetera is None:
        raise HTTPException(status_code=404, detail="El cliente no tiene una billetera registrada")

    ultimas = (
        db.query(TransaccionDB)
        .filter(TransaccionDB.cliente_id == cliente)
        .order_by(TransaccionDB.fecha.desc(), TransaccionDB.id.desc())
        .limit(MAX_TRANSACCIONES_HISTORIAL)
        .all()
    )
    return HistorialBilletera(
        cliente_id=cliente,
        saldo=float(billetera.saldo),
        transacciones=[_a_transaccion(t) for t in ultimas],
    )
