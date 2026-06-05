"""
models.py — SQLAlchemy ORM models for simulation persistence.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Simulation(Base):
    __tablename__ = "simulations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    system_id: Mapped[int] = mapped_column(Integer, nullable=False)
    drift_score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    risk_label: Mapped[str] = mapped_column(String(20), nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    review_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="pending", index=True
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(255))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    notes: Mapped[str | None] = mapped_column(Text)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    employee_id: Mapped[int | None] = mapped_column(Integer, index=True)
    system_id: Mapped[int | None] = mapped_column(Integer)
    drift_score: Mapped[float | None] = mapped_column(Numeric(5, 4))
    performed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    details: Mapped[str | None] = mapped_column(Text)  # JSON-encoded string
