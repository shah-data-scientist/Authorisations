"""
preprocess.py — clean raw data, encode features, build user-permission matrix.
"""
import pandas as pd
from loguru import logger
from role_recommender.config import (
    RAW_DATASET, DATA_INTERIM, DATA_PROCESSED,
    PROCESSED_MATRIX, PROCESSED_EVENTS,
)


def load_raw() -> pd.DataFrame:
    logger.info("Loading raw dataset …")
    df = pd.read_csv(RAW_DATASET)
    logger.info(f"  Shape: {df.shape}  |  Columns: {df.columns.tolist()}")
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Drop duplicates, handle nulls, enforce dtypes."""
    df = df.drop_duplicates()
    df = df.dropna(subset=["RESOURCE", "MGR_ID", "ROLE_ROLLUP_1"])
    logger.info(f"After cleaning: {df.shape}")
    return df


def build_user_permission_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a binary user × resource matrix.
    Rows = unique employees (by ROLE_CODE as user proxy).
    Columns = unique RESOURCE values.
    Entry = 1 if user has access, 0 otherwise.
    """
    logger.info("Building user × permission matrix …")
    matrix = (
        df.groupby(["ROLE_CODE", "RESOURCE"])
        .size()
        .unstack(fill_value=0)
        .clip(upper=1)  # binarise: has-access or not
    )
    logger.success(
        f"Matrix shape: {matrix.shape}  "
        f"({matrix.shape[0]} users × {matrix.shape[1]} resources)"
    )
    return matrix


def run() -> None:
    DATA_INTERIM.mkdir(parents=True, exist_ok=True)
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    df = load_raw()
    df = clean(df)

    interim_path = DATA_INTERIM / "cleaned.parquet"
    df.to_parquet(interim_path, index=False)
    logger.info(f"Interim saved → {interim_path}")

    matrix = build_user_permission_matrix(df)
    matrix.to_parquet(PROCESSED_MATRIX)
    logger.success(f"Matrix saved → {PROCESSED_MATRIX}")

    df.to_parquet(PROCESSED_EVENTS, index=False)
    logger.success(f"Events saved → {PROCESSED_EVENTS}")


if __name__ == "__main__":
    run()
