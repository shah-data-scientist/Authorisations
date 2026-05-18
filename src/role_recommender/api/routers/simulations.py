"""
simulations.py — CRUD endpoints for simulation persistence.

POST /simulations/         — save a simulation result + audit row
GET  /simulations/         — list simulations (filter by employee, status)
GET  /simulations/history  — employee-centric history (employee_id required)
PATCH /simulations/{id}    — update review_status + reviewer notes
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from role_recommender.db.models import AuditLog, Simulation
from role_recommender.db.session import get_session

router = APIRouter()


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class SimulationCreate(BaseModel):
    employee_id: int
    system_id: int
    drift_score: float
    risk_label: str
    explanation: Optional[str] = None


class SimulationUpdate(BaseModel):
    review_status: str
    reviewed_by: str
    notes: Optional[str] = None


class SimulationOut(BaseModel):
    id: int
    employee_id: int
    system_id: int
    drift_score: float
    risk_label: str
    explanation: Optional[str]
    requested_at: Optional[datetime]
    review_status: str
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    notes: Optional[str]

    model_config = {"from_attributes": True}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/", response_model=SimulationOut, status_code=201)
async def create_simulation(
    payload: SimulationCreate,
    session: AsyncSession = Depends(get_session),
):
    sim = Simulation(**payload.model_dump())
    session.add(sim)
    log = AuditLog(
        action="simulation_created",
        employee_id=payload.employee_id,
        system_id=payload.system_id,
        drift_score=payload.drift_score,
        details={"risk_label": payload.risk_label},
    )
    session.add(log)
    await session.commit()
    await session.refresh(sim)
    return sim


@router.get("/history", response_model=list[SimulationOut])
async def simulation_history(
    employee_id: int = Query(..., description="Filter by employee ID"),
    session: AsyncSession = Depends(get_session),
):
    q = (
        select(Simulation)
        .where(Simulation.employee_id == employee_id)
        .order_by(Simulation.requested_at.desc())
        .limit(50)
    )
    result = await session.execute(q)
    return result.scalars().all()


@router.get("/", response_model=list[SimulationOut])
async def list_simulations(
    employee_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None, description="pending / approved / denied"),
    limit: int = Query(100, le=500),
    session: AsyncSession = Depends(get_session),
):
    q = select(Simulation).order_by(Simulation.requested_at.desc()).limit(limit)
    if employee_id is not None:
        q = q.where(Simulation.employee_id == employee_id)
    if status is not None:
        q = q.where(Simulation.review_status == status)
    result = await session.execute(q)
    return result.scalars().all()


@router.patch("/{sim_id}", response_model=SimulationOut)
async def review_simulation(
    sim_id: int,
    payload: SimulationUpdate,
    session: AsyncSession = Depends(get_session),
):
    sim = await session.get(Simulation, sim_id)
    if sim is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    if payload.review_status not in ("approved", "denied", "pending"):
        raise HTTPException(
            status_code=422,
            detail="review_status must be approved, denied, or pending",
        )
    sim.review_status = payload.review_status
    sim.reviewed_by = payload.reviewed_by
    sim.reviewed_at = datetime.now(timezone.utc)
    sim.notes = payload.notes
    log = AuditLog(
        action=f"simulation_{payload.review_status}",
        employee_id=sim.employee_id,
        system_id=sim.system_id,
        drift_score=float(sim.drift_score),
        details={"reviewed_by": payload.reviewed_by, "notes": payload.notes},
    )
    session.add(log)
    await session.commit()
    await session.refresh(sim)
    return sim
