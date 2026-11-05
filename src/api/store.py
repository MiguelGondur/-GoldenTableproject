"""Consultas reutilizables sobre la base de datos."""

from datetime import date

from sqlalchemy.orm import Session

from src.api.orm import Mesa, Reserva


def mesas_disponibles(db: Session, fecha: date, hora: str) -> list[Mesa]:
    """
    Mesas libres para una fecha y hora: estado base 'disponible', franja
    horaria igual a la solicitada y sin una reserva ese día.
    """
    reservadas = db.query(Reserva.mesa_id).filter(Reserva.fecha == fecha, Reserva.hora == hora)
    return (
        db.query(Mesa)
        .filter(Mesa.estado == "disponible", Mesa.horario == hora, Mesa.id.not_in(reservadas))
        .order_by(Mesa.id)
        .all()
    )
