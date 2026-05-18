"""
test_mining.py — unit tests for the NMF role mining model.
"""
import numpy as np
import pandas as pd
import pytest
from role_recommender.mining.probabilistic import ProbabilisticRoleMiner


@pytest.fixture
def small_matrix():
    """5 users × 8 resources — deterministic synthetic matrix."""
    rng = np.random.default_rng(42)
    data = rng.integers(0, 2, size=(5, 8)).astype(float)
    users = [101, 102, 103, 104, 105]
    resources = [10, 20, 30, 40, 50, 60, 70, 80]
    return pd.DataFrame(data, index=users, columns=resources)


def test_fit_produces_W_and_H(small_matrix):
    miner = ProbabilisticRoleMiner(n_roles=3)
    miner.fit(small_matrix)
    assert miner.W is not None
    assert miner.H is not None
    assert miner.W.shape == (5, 3)
    assert miner.H.shape == (3, 8)


def test_user_index_set(small_matrix):
    miner = ProbabilisticRoleMiner(n_roles=3)
    miner.fit(small_matrix)
    assert miner.user_index == [101, 102, 103, 104, 105]


def test_get_user_role_returns_int(small_matrix):
    miner = ProbabilisticRoleMiner(n_roles=3)
    miner.fit(small_matrix)
    role = miner.get_user_role(101)
    assert isinstance(role, int)
    assert 0 <= role < 3


def test_role_weights_sum_to_one(small_matrix):
    miner = ProbabilisticRoleMiner(n_roles=3)
    miner.fit(small_matrix)
    weights = miner.get_user_role_weights(102)
    assert abs(weights.sum() - 1.0) < 1e-6


def test_get_role_permissions_length(small_matrix):
    miner = ProbabilisticRoleMiner(n_roles=3)
    miner.fit(small_matrix)
    perms = miner.get_role_permissions(0, top_n=5)
    assert len(perms) == 5


def test_get_role_permissions_are_valid_resources(small_matrix):
    miner = ProbabilisticRoleMiner(n_roles=3)
    miner.fit(small_matrix)
    perms = miner.get_role_permissions(1, top_n=8)
    assert all(p in [10, 20, 30, 40, 50, 60, 70, 80] for p in perms)
