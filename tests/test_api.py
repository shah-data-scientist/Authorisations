"""
test_api.py — integration tests for the FastAPI application.
Uses TestClient (httpx) and mocks the model loader to avoid needing trained models.
"""
import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from role_recommender.api.main import app
from role_recommender.mining.probabilistic import ProbabilisticRoleMiner
from role_recommender.drift.scorer import DriftScorer


def _make_mock_miner():
    data = np.array([[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]])
    matrix = pd.DataFrame(data, index=[101, 102, 103], columns=[10, 20])
    miner = ProbabilisticRoleMiner(n_roles=2, random_state=42)
    miner.fit(matrix)
    return miner


@pytest.fixture(autouse=True)
def mock_model_loader():
    miner = _make_mock_miner()
    scorer = DriftScorer(miner)
    matrix = pd.DataFrame(
        np.array([[1, 0], [0, 1], [1, 1]]),
        index=[101, 102, 103],
        columns=[10, 20],
    )
    # Patch where each name is consumed (not where it's defined),
    # because routers bind get_miner/get_matrix into their own namespace at import.
    with (
        patch("role_recommender.api.routers.roles.get_miner", return_value=miner),
        patch("role_recommender.api.routers.users.get_miner", return_value=miner),
        patch("role_recommender.api.routers.users.get_matrix", return_value=matrix),
        patch("role_recommender.api._model_loader.get_miner", return_value=miner),
        patch("role_recommender.api._model_loader.get_scorer", return_value=scorer),
        patch("role_recommender.api._model_loader.get_matrix", return_value=matrix),
    ):
        yield


client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_list_roles():
    resp = client.get("/roles/")
    assert resp.status_code == 200
    data = resp.json()
    assert "n_clusters" in data
    assert "cluster_ids" in data


def test_get_role_detail():
    resp = client.get("/roles/0")
    assert resp.status_code == 200
    data = resp.json()
    assert "typical_systems" in data


def test_get_role_not_found():
    resp = client.get("/roles/999")
    assert resp.status_code == 404


def test_drift_score():
    resp = client.post(
        "/drift/score",
        json={"user_id": 101, "system_id": 10},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "drift_score" in data
    assert "is_drift" in data
    assert "user_cluster" in data
    assert "typical_systems" in data
    assert 0.0 <= data["drift_score"] <= 1.0
