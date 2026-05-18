"""
users.py — /users endpoints.

GET /users/{user_id}/role          → dominant role + soft weights
GET /users/{user_id}/permissions   → list of resources the user has access to
"""
from fastapi import APIRouter, HTTPException
from role_recommender.api._model_loader import get_miner, get_matrix

router = APIRouter()


@router.get("/{user_id}/role")
def get_user_role(user_id: int):
    miner = get_miner()
    if user_id not in miner.user_index:
        raise HTTPException(
            status_code=404, detail=f"User {user_id} not found."
        )
    dominant = miner.get_user_role(user_id)
    weights = miner.get_user_role_weights(user_id).tolist()
    return {
        "user_id": user_id,
        "user_cluster": dominant,
        "cluster_weights": weights,
    }


@router.get("/{user_id}/permissions")
def get_user_permissions(user_id: int):
    matrix = get_matrix()
    if user_id not in matrix.index:
        raise HTTPException(
            status_code=404, detail=f"User {user_id} not found."
        )
    perms = matrix.loc[user_id]
    granted = perms[perms > 0].index.tolist()
    return {
        "user_id": user_id,
        "permission_count": len(granted),
        "resources": granted[:100],  # cap response size
    }
