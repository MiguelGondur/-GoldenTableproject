"""
Endpoints de Billetera Digital.

HU-06: Recarga de saldo (REQ-FUNC-006)
HU-07: Consulta de saldo e historial (REQ-FUNC-007)
HU-08: Validación de saldo en caja (REQ-FUNC-008)
HU-12: Reportes de recargas y transacciones (REQ-FUNC-012)
"""

import csv
import io
from datetime import date as date_type
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/billetera", tags=["billetera"])

# Almacenamiento en memoria — placeholder hasta integrar base de datos real.
BILLETERAS_DB: dict[str, float] = {}
# Historial de transacciones por cliente, más reciente al final.
TRANSACCIONES_DB: dict[str, list["Transaccion"]] = {}
MAX_TRANSACCIONES_HISTORIAL = 20


class RecargaRequest(BaseModel):
    cliente_id: str
    monto: float = Field(..., gt=0, description="Monto a recargar; debe ser mayor a 0")
    metodo_pago: str


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

    transaccion = Transaccion(
        cliente_id=datos.cliente_id,
        tipo="recarga",
        monto=datos.monto,
        saldo_resultante=nuevo_saldo,
        fecha=datetime.now(timezone.utc),
    )
    TRANSACCIONES_DB.setdefault(datos.cliente_id, []).append(transaccion)

    return Billetera(cliente_id=datos.cliente_id, saldo=nuevo_saldo)


@router.get("/validar", response_model=ValidacionSaldo)
def validar_saldo(
    cliente_id: str = Query(..., description="Código del cliente escaneado en caja"),
    monto_requerido: float = Query(
        default=0.0, ge=0, description="Monto en fichas que el cajero necesita autorizar"
    ),
):
    """
    HU-08: valida en caja si el cliente tiene saldo suficiente para una
    operación con fichas por `monto_requerido`.

    Si el cliente no existe en la billetera aún (no se ha registrado ni
    recargado), se asume saldo 0 en vez de fallar, para que el cajero
    reciba una respuesta clara (no autorizado) en lugar de un error.
    """
    saldo_actual = BILLETERAS_DB.get(cliente_id, 0.0)
    return ValidacionSaldo(
        cliente_id=cliente_id,
        saldo_disponible=saldo_actual,
        monto_requerido=monto_requerido,
        valido=saldo_actual >= monto_requerido,
    )


@router.get("/reportes")
def generar_reporte(
    fecha_inicio: date_type | None = Query(
        default=None, description="Filtra transacciones desde esta fecha (YYYY-MM-DD)"
    ),
    fecha_fin: date_type | None = Query(
        default=None, description="Filtra transacciones hasta esta fecha (YYYY-MM-DD)"
    ),
):
    """
    HU-12: genera un reporte exportable (CSV) de todas las recargas y
    transacciones registradas, para que el gerente de operaciones pueda
    auditar el flujo de caja digital.

    Se puede filtrar por rango de fechas con `fecha_inicio` y `fecha_fin`;
    si no se envían, el reporte incluye todas las transacciones.
    """
    todas_las_transacciones = [
        transaccion
        for transacciones_cliente in TRANSACCIONES_DB.values()
        for transaccion in transacciones_cliente
    ]

    if fecha_inicio is not None:
        todas_las_transacciones = [
            t for t in todas_las_transacciones if t.fecha.date() >= fecha_inicio
        ]
    if fecha_fin is not None:
        todas_las_transacciones = [
            t for t in todas_las_transacciones if t.fecha.date() <= fecha_fin
        ]

    todas_las_transacciones.sort(key=lambda t: t.fecha)

    buffer = io.StringIO()
    escritor = csv.writer(buffer)
    escritor.writerow(["cliente_id", "tipo", "monto", "saldo_resultante", "fecha"])
    for t in todas_las_transacciones:
        escritor.writerow(
            [t.cliente_id, t.tipo, t.monto, t.saldo_resultante, t.fecha.isoformat()]
        )
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=reporte_billetera.csv"},
    )


# IMPORTANTE: esta ruta debe declararse DESPUÉS de "/validar" y "/reportes". Al tener un
# parámetro dinámico ({cliente_id}), FastAPI la usaría para *cualquier*
# texto en esa posición — incluida la palabra "validar" — si quedara antes.
@router.get("/{cliente_id}", response_model=HistorialBilletera)
def consultar_saldo_e_historial(cliente_id: str):
    """
    HU-07: retorna el saldo actual del cliente y sus últimas 20
    transacciones (recargas), de la más reciente a la más antigua.
    """
    if cliente_id not in BILLETERAS_DB:
        raise HTTPException(
            status_code=404, detail="El cliente no tiene una billetera registrada"
        )

    historial = TRANSACCIONES_DB.get(cliente_id, [])
    ultimas_20 = list(reversed(historial))[:MAX_TRANSACCIONES_HISTORIAL]

    return HistorialBilletera(
        cliente_id=cliente_id,
        saldo=BILLETERAS_DB[cliente_id],
        transacciones=ultimas_20,
    )
