"""
test_preprocess.py — unit tests for data cleaning and matrix building.
"""
import pandas as pd
import pytest
from role_recommender.data.preprocess import clean, build_user_permission_matrix


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "ROLE_CODE": [1, 1, 2, 2, 2, 1],
        "RESOURCE":  [10, 20, 10, 30, 40, 10],   # row 5 is duplicate of row 0
        "MGR_ID":    [100, 100, 200, 200, 200, 100],
        "ROLE_ROLLUP_1": ["A", "A", "B", "B", "B", "A"],
        "ACTION": [1, 1, 1, 1, 1, 1],
    })


def test_clean_removes_duplicates(sample_df):
    cleaned = clean(sample_df)
    assert len(cleaned) == 5   # one duplicate removed


def test_clean_drops_null_rows():
    df = pd.DataFrame({
        "ROLE_CODE": [1, 2],
        "RESOURCE":  [None, 10],
        "MGR_ID":    [100, 200],
        "ROLE_ROLLUP_1": ["A", "B"],
    })
    cleaned = clean(df)
    assert len(cleaned) == 1


def test_matrix_shape(sample_df):
    cleaned = clean(sample_df)
    matrix = build_user_permission_matrix(cleaned)
    assert matrix.shape == (2, 4)   # 2 users × 4 unique resources {10,20,30,40}


def test_matrix_binary(sample_df):
    cleaned = clean(sample_df)
    matrix = build_user_permission_matrix(cleaned)
    assert matrix.values.max() == 1
    assert matrix.values.min() == 0


def test_matrix_index_is_role_code(sample_df):
    cleaned = clean(sample_df)
    matrix = build_user_permission_matrix(cleaned)
    assert set(matrix.index) == {1, 2}
