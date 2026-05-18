"""
roles.py — /roles endpoints.

GET /roles              → list all role IDs
GET /roles/{role_id}    → top permissions for a role
"""
from fastapi import APIRouter, HTTPException
from role_recommender.api._model_loader import get_miner

router = APIRouter()


@router.get("/")
def list_roles():
    miner = get_miner()
    return {"n_clusters": miner.n_roles, "cluster_ids": list(range(miner.n_roles))}


@router.get("/{role_id}")
def get_role(role_id: int, top_n: int = 20):
    miner = get_miner()
    if role_id < 0 or role_id >= miner.n_roles:
        raise HTTPException(status_code=404, detail=f"Cluster {role_id} not found.")
    perms = miner.get_role_permissions(role_id, top_n=top_n)
    return {"cluster_id": role_id, "typical_systems": perms}
