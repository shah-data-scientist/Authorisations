"""
generate_synthetic.py — create a realistic synthetic Amazon Access Samples dataset.

Matches the real dataset's structure exactly:
  - 32,769 rows, 10 columns
  - Same column names and dtypes as the UCI original
  - ~94% ACTION=1 (granted), ~6% ACTION=0 (revoked)
  - Clear role clusters so NMF mining produces interpretable roles
  - Saved to data/raw/amazon_access_samples.csv

Used when the UCI / Kaggle download is unavailable.
"""
import numpy as np
import pandas as pd
from loguru import logger
from role_recommender.config import DATA_RAW, RAW_DATASET

N_ROWS       = 32_769
N_RESOURCES  = 7_518
N_MANAGERS   = 2_000
N_ROLE_CODES = 3_874   # unique employees
N_ROLES      = 15      # ground-truth role clusters

REVOKE_RATE  = 0.06    # fraction of ACTION=0
RANDOM_STATE = 42


def _role_resource_map(rng, n_roles, n_resources, coverage=40):
    """Each role owns a set of ~coverage resources (with overlap)."""
    role_resources = {}
    for r in range(n_roles):
        core = rng.integers(0, n_resources, size=coverage).tolist()
        role_resources[r] = list(set(core))
    return role_resources


def generate() -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_STATE)
    logger.info("Generating synthetic Amazon Access Samples …")

    # Assign each employee (ROLE_CODE) a primary role
    role_codes   = np.arange(1_000_000, 1_000_000 + N_ROLE_CODES)
    emp_role     = rng.integers(0, N_ROLES, size=N_ROLE_CODES)        # primary role per user
    emp_dept     = rng.integers(10_000, 11_000, size=N_ROLE_CODES)    # ROLE_ROLLUP_1
    emp_subdept  = rng.integers(20_000, 21_000, size=N_ROLE_CODES)    # ROLE_ROLLUP_2
    emp_deptname = rng.integers(30_000, 31_000, size=N_ROLE_CODES)
    emp_title    = rng.integers(40_000, 41_000, size=N_ROLE_CODES)
    emp_family_d = rng.integers(50_000, 51_000, size=N_ROLE_CODES)
    emp_family   = rng.integers(60_000, 61_000, size=N_ROLE_CODES)
    emp_mgr      = rng.integers(70_000, 70_000 + N_MANAGERS, size=N_ROLE_CODES)

    resource_ids = np.arange(200_000, 200_000 + N_RESOURCES)
    role_resource_map = _role_resource_map(rng, N_ROLES, N_RESOURCES, coverage=50)

    rows = []
    for _ in range(N_ROWS):
        emp_idx  = rng.integers(0, N_ROLE_CODES)
        role     = emp_role[emp_idx]

        # 80% chance: pick a resource from the user's role (realistic grant)
        # 20% chance: random resource (cross-role / drift)
        if rng.random() < 0.80 and role_resource_map[role]:
            res_local_idx = rng.integers(0, len(role_resource_map[role]))
            res_id = resource_ids[role_resource_map[role][res_local_idx]]
        else:
            res_id = resource_ids[rng.integers(0, N_RESOURCES)]

        action = 0 if rng.random() < REVOKE_RATE else 1

        rows.append({
            "ACTION":           action,
            "RESOURCE":         int(res_id),
            "MGR_ID":           int(emp_mgr[emp_idx]),
            "ROLE_ROLLUP_1":    int(emp_dept[emp_idx]),
            "ROLE_ROLLUP_2":    int(emp_subdept[emp_idx]),
            "ROLE_DEPTNAME":    int(emp_deptname[emp_idx]),
            "ROLE_TITLE":       int(emp_title[emp_idx]),
            "ROLE_FAMILY_DESC": int(emp_family_d[emp_idx]),
            "ROLE_FAMILY":      int(emp_family[emp_idx]),
            "ROLE_CODE":        int(role_codes[emp_idx]),
        })

    df = pd.DataFrame(rows)
    logger.info(
        f"Generated {len(df):,} rows | "
        f"ACTION=1: {df.ACTION.mean():.1%} | "
        f"Unique resources: {df.RESOURCE.nunique():,} | "
        f"Unique employees: {df.ROLE_CODE.nunique():,}"
    )
    return df


def run() -> None:
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    if RAW_DATASET.exists():
        logger.info(f"Dataset already exists at {RAW_DATASET} — skipping generation.")
        return
    df = generate()
    df.to_csv(RAW_DATASET, index=False)
    logger.success(f"Synthetic dataset saved → {RAW_DATASET}")


if __name__ == "__main__":
    run()
