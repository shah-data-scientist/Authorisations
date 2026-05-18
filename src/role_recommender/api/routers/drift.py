"""
drift.py — POST /drift/score endpoint.
"""
from fastapi import APIRouter, HTTPException
from role_recommender.api.schemas import DriftRequest
from role_recommender.api._model_loader import get_scorer

router = APIRouter()


@router.post("/score")
def score_drift(req: DriftRequest):
    """Score a new access-grant event for drift."""
    scorer = get_scorer()
    try:
        return scorer.score(req.user_id, req.system_id)
    except ValueError:
        known = scorer.miner.user_index
        raise HTTPException(
            status_code=422,
            detail=(
                f"Employee ID {req.user_id!r} is not in the model. "
                f"The model knows {len(known)} employees. "
                f"Example valid IDs: {known[:5]}"
            ),
        )
