"""Tablas de la base de datos (SQLAlchemy 2.0)."""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.api.db import Base


def ahora() -> datetime:
    return datetime.now(timezone.utc)


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(120))
    documento: Mapped[str] = mapped_column(String(10), unique=True)
    fecha_nacimiento: Mapped[date] = mapped_column(Date)
    password_hash: Mapped[str] = mapped_column(String(200))
    rol: Mapped[str] = mapped_column(String(20), default="cliente")
    intentos_fallidos: Mapped[int] = mapped_column(Integer, default=0)
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class Mesa(Base):
    __tablename__ = "mesas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    capacidad: Mapped[int] = mapped_column(Integer)
    estado: Mapped[str] = mapped_column(String(20), default="disponible")
    horario: Mapped[str] = mapped_column(String(5))


class Reserva(Base):
    __tablename__ = "reservas"
    # Una mesa no puede reservarse dos veces para la misma fecha y hora
    # (protege contra reservas simultáneas).
    __table_args__ = (UniqueConstraint("mesa_id", "fecha", "hora", name="uq_reserva_mesa_fecha_hora"),)

    codigo_confirmacion: Mapped[str] = mapped_column(String(8), primary_key=True)
    mesa_id: Mapped[int] = mapped_column(ForeignKey("mesas.id"))
    fecha: Mapped[date] = mapped_column(Date)
    hora: Mapped[str] = mapped_column(String(5))
    cliente_id: Mapped[str] = mapped_column(ForeignKey("usuarios.usuario"), index=True)
    estado: Mapped[str] = mapped_column(String(20), default="confirmada")
    recordatorio_enviado: Mapped[bool] = mapped_column(Boolean, default=False)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
    check_in_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Puntos(Base):
    __tablename__ = "puntos"

    cliente_id: Mapped[str] = mapped_column(ForeignKey("usuarios.usuario"), primary_key=True)
    puntos: Mapped[int] = mapped_column(Integer, default=0)


class Canje(Base):
    __tablename__ = "canjes"

    cupon: Mapped[str] = mapped_column(String(8), primary_key=True)
    cliente_id: Mapped[str] = mapped_column(ForeignKey("usuarios.usuario"), index=True)
    beneficio: Mapped[str] = mapped_column(String(40))
    puntos_usados: Mapped[int] = mapped_column(Integer)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class Billetera(Base):
    __tablename__ = "billeteras"

    cliente_id: Mapped[str] = mapped_column(ForeignKey("usuarios.usuario"), primary_key=True)
    saldo: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))


class Transaccion(Base):
    __tablename__ = "transacciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[str] = mapped_column(ForeignKey("usuarios.usuario"), index=True)
    tipo: Mapped[str] = mapped_column(String(20))
    monto: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    saldo_resultante: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    metodo_pago: Mapped[str | None] = mapped_column(String(40), nullable=True)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class LimiteDiario(Base):
    __tablename__ = "limites_diarios"

    cliente_id: Mapped[str] = mapped_column(ForeignKey("usuarios.usuario"), primary_key=True)
    limite: Mapped[Decimal] = mapped_column(Numeric(14, 2))


class GastoDiario(Base):
    __tablename__ = "gastos_diarios"

    cliente_id: Mapped[str] = mapped_column(ForeignKey("usuarios.usuario"), primary_key=True)
    fecha: Mapped[date] = mapped_column(Date, primary_key=True)
    monto: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))


class Autoexclusion(Base):
    __tablename__ = "autoexclusiones"

    cliente_id: Mapped[str] = mapped_column(ForeignKey("usuarios.usuario"), primary_key=True)
    fecha_fin: Mapped[date] = mapped_column(Date)


class Notificacion(Base):
    __tablename__ = "notificaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[str] = mapped_column(ForeignKey("usuarios.usuario"), index=True)
    tipo: Mapped[str] = mapped_column(String(30))
    mensaje: Mapped[str] = mapped_column(String(300))
    canal: Mapped[str] = mapped_column(String(20), default="push")
    estado: Mapped[str] = mapped_column(String(20), default="enviada")
    enviada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
