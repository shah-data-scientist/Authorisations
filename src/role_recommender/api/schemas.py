"""
schemas.py — Pydantic request/response models for the FastAPI application.
"""
from pydantic import BaseModel, Field
from typing import Any


class DriftRequest(BaseModel):
    user_id: int | str = Field(..., description="Employee ID (ROLE_CODE)")
    system_id: int = Field(..., description="ID of the internal system being requested")


class DriftResponse(BaseModel):
    user_id: int | str
    system_id: int
    user_cluster: int
    typical_systems: list[int | str]
    drift_score: float = Field(..., ge=0.0, le=1.0)
    is_drift: bool
    explanation: str


class RoleDetail(BaseModel):
    cluster_id: int
    typical_systems: list[int | str]


class UserRoleResponse(BaseModel):
    user_id: int | str
    user_cluster: int
    cluster_weights: list[float]


class HealthResponse(BaseModel):
    status: str
