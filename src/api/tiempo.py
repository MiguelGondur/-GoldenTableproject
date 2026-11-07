"""Hora local del casino (por defecto America/Bogota), independiente de la zona del servidor."""

import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

ZONA_CASINO = ZoneInfo(os.getenv("CASINO_TZ", "America/Bogota"))


def ahora_casino() -> datetime:
    """Fecha y hora local del casino, sin zona horaria (naive)."""
    return datetime.now(ZONA_CASINO).replace(tzinfo=None)


def hoy_casino() -> date:
    return ahora_casino().date()
