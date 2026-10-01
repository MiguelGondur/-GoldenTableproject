"""
Almacenamiento compartido en memoria — placeholder hasta integrar una
base de datos real.

Se centraliza aquí para que distintos routers (reservas, disponibilidad
en main.py) lean y modifiquen el mismo estado de las mesas, en vez de
tener copias separadas que se desincronizan entre sí.
"""

from src.api.models import EstadoMesa, Mesa

MESAS_DB: list[Mesa] = [
    Mesa(id=1, capacidad=2, estado=EstadoMesa.DISPONIBLE, horario="18:00"),
    Mesa(id=2, capacidad=4, estado=EstadoMesa.DISPONIBLE, horario="18:00"),
    Mesa(id=3, capacidad=4, estado=EstadoMesa.RESERVADA, horario="19:00"),
    Mesa(id=4, capacidad=6, estado=EstadoMesa.DISPONIBLE, horario="19:00"),
    Mesa(id=5, capacidad=2, estado=EstadoMesa.OCUPADA, horario="20:00"),
]
