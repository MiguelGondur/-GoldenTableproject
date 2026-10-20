"""Aísla cada prueba: restablece todo el estado en memoria antes de ejecutarla."""

import pytest

from src.api import store
from src.api.routers import billetera, fidelidad


@pytest.fixture(autouse=True)
def estado_limpio():
    store.reset_state()
    billetera.BILLETERAS_DB.clear()
    billetera.TRANSACCIONES_DB.clear()
    fidelidad.PUNTOS_DB.clear()
    fidelidad.PUNTOS_DB["cliente-demo"] = 500
    fidelidad.LIMITES_DIARIOS_DB.clear()
    fidelidad.GASTO_DIARIO_DB.clear()
    yield
