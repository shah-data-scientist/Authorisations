"""
test_drift.py — unit tests for the drift scorer.
"""
import numpy as np
import pandas as pd
import pytest
from role_recommender.mining.probabilistic import ProbabilisticRoleMiner
from role_recommender.drift.scorer import DriftScorer


@pytest.fixture
def miner_and_user():
    """Train a tiny miner where user 101 clearly owns resource 10."""
    data = np.zeros((3, 6))
    data[0, 0] = 1  # user 101 has resource 10
    data[0, 1] = 1  # user 101 has resource 20
    data[1, 2] = 1  # user 102 has resource 30
    data[2, 4] = 1  # user 103 has resource 50
    matrix = pd.DataFrame(
        data, index=[101, 102, 103], columns=[10, 20, 30, 40, 50, 60]
    )
    miner = ProbabilisticRoleMiner(n_roles=2, random_state=42)
    miner.fit(matrix)
    return miner


def test_score_returns_expected_keys(miner_and_user):
    scorer = DriftScorer(miner_and_user)
    result = scorer.score(101, 10)
    expected_keys = {
        "user_id", "system_id", "user_cluster",
        "typical_systems", "drift_score", "is_drift", "explanation",
    }
    assert expected_keys == set(result.keys())


def test_drift_score_in_range(miner_and_user):
    scorer = DriftScorer(miner_and_user)
    result = scorer.score(101, 99)  # 99 doesn't exist in any role
    assert 0.0 <= result["drift_score"] <= 1.0


def test_is_drift_consistent_with_score(miner_and_user):
    scorer = DriftScorer(miner_and_user, threshold=0.5)
    result = scorer.score(101, 99)
    assert result["is_drift"] == (result["drift_score"] >= 0.5)


def test_explanation_is_string(miner_and_user):
    scorer = DriftScorer(miner_and_user)
    result = scorer.score(102, 10)
    assert isinstance(result["explanation"], str)
    assert len(result["explanation"]) > 0
