"""
Datos de ejemplo que existen desde el primer arranque (ver README).

Es idempotente: solo crea lo que falta, así que puede ejecutarse en cada
arranque sin duplicar datos ni pisar los cambios de los usuarios.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from src.api.auth import hashear_password
from src.api.orm import Billetera, Mesa, Notificacion, Puntos, Reserva, Transaccion, Usuario

PASSWORD_DEMO = "Casino2026!"

# (usuario, nombre, documento, nacimiento, rol, puntos, saldo)
USUARIOS_DEMO = [
    ("cliente1", "Carlos Mendoza", "1012345678", date(1990, 5, 14), "cliente", 500, Decimal("150000")),
    ("cliente2", "Laura Gómez", "1098765432", date(1995, 11, 2), "cliente", 120, Decimal("50000")),
    ("anfitrion", "Andrés Ruiz", "1020304050", date(1988, 3, 21), "anfitrion", 0, Decimal("0")),
    ("cajero", "Marta Díaz", "1030405060", date(1992, 8, 9), "cajero", 0, Decimal("0")),
    ("gerente", "Julián Torres", "1040506070", date(1985, 1, 30), "gerente", 0, Decimal("0")),
]


def _mesas_demo() -> list[Mesa]:
    base = [
        Mesa(id=1, capacidad=2, estado="disponible", horario="18:00"),
        Mesa(id=2, capacidad=4, estado="disponible", horario="18:00"),
        Mesa(id=3, capacidad=4, estado="reservada", horario="19:00"),
        Mesa(id=4, capacidad=6, estado="disponible", horario="19:00"),
        Mesa(id=5, capacidad=2, estado="ocupada", horario="20:00"),
        Mesa(id=6, capacidad=4, estado="disponible", horario="20:00"),
        Mesa(id=7, capacidad=8, estado="disponible", horario="18:00"),
        Mesa(id=8, capacidad=2, estado="disponible", horario="21:00"),
    ]
    siguiente = 9
    for hora in ("18:00", "19:00", "20:00", "21:00", "22:00"):
        for capacidad in (2, 4, 6):
            base.append(Mesa(id=siguiente, capacidad=capacidad, estado="disponible", horario=hora))
            siguiente += 1
    return base


def sembrar(db: Session) -> None:
    if db.query(Mesa).count() == 0:
        db.add_all(_mesas_demo())

    for usuario, nombre, documento, nacimiento, rol, puntos, saldo in USUARIOS_DEMO:
        if db.query(Usuario.id).filter(Usuario.usuario == usuario).first():
            continue
        db.add(
            Usuario(
                usuario=usuario,
                nombre=nombre,
                documento=documento,
                fecha_nacimiento=nacimiento,
                password_hash=hashear_password(PASSWORD_DEMO),
                rol=rol,
            )
        )
        db.flush()
        if rol == "cliente":
            db.add(Puntos(cliente_id=usuario, puntos=puntos))
            db.add(Billetera(cliente_id=usuario, saldo=saldo))
            ahora = datetime.now(timezone.utc)
            mitad = saldo / 2
            db.add(
                Transaccion(
                    cliente_id=usuario, tipo="recarga", monto=mitad, saldo_resultante=mitad,
                    metodo_pago="tarjeta", fecha=ahora - timedelta(days=2),
                )
            )
            db.add(
                Transaccion(
                    cliente_id=usuario, tipo="recarga", monto=saldo - mitad, saldo_resultante=saldo,
                    metodo_pago="efectivo", fecha=ahora - timedelta(days=1),
                )
            )
            db.add(
                Notificacion(
                    cliente_id=usuario,
                    tipo="promocion",
                    mensaje="¡Bienvenido a GoldenTable! Reserva tu mesa y acumula puntos.",
                )
            )

    db.flush()
    # Reserva de ejemplo para practicar el check-in como anfitrión.
    if db.get(Reserva, "DEMO0001") is None and db.get(Mesa, 4) is not None:
        db.add(
            Reserva(
                codigo_confirmacion="DEMO0001",
                mesa_id=4,
                fecha=date.today(),
                hora="19:00",
                cliente_id="cliente2",
            )
        )
    db.commit()
