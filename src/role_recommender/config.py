"""
config.py — centralised paths, hyperparameters, and constants.
All modules import from here; no magic strings elsewhere.
"""
import os
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
# APP_ROOT is set to /app in Docker so paths resolve correctly from the
# installed wheel (whose __file__ points into site-packages, not /app).
ROOT = Path(os.environ.get("APP_ROOT", str(Path(__file__).resolve().parents[2])))

DATA_RAW        = ROOT / "data" / "raw"
DATA_INTERIM    = ROOT / "data" / "interim"
DATA_PROCESSED  = ROOT / "data" / "processed"
MODELS_DIR      = ROOT / "models"

RAW_DATASET      = DATA_RAW / "amazon_access_samples.csv"
PROCESSED_MATRIX = DATA_PROCESSED / "user_permission_matrix.parquet"
PROCESSED_EVENTS = DATA_PROCESSED / "access_events.parquet"

# ── UCI dataset ID ────────────────────────────────────────────────────────────
UCI_DATASET_ID = 216  # Amazon Access Samples

# ── Role mining hyperparameters ───────────────────────────────────────────────
ROLE_COUNT_MIN     = 5
ROLE_COUNT_MAX     = 30
ROLE_COUNT_DEFAULT = 15        # starting point; tune via BIC
RANDOM_STATE       = 42

# ── Drift detection ───────────────────────────────────────────────────────────
DRIFT_OVERLAP_THRESHOLD     = 0.5   # fraction of new perms not explained by role
DRIFT_CLASSIFIER_THRESHOLD  = 0.7   # XGBoost probability threshold

# ── API ───────────────────────────────────────────────────────────────────────
API_HOST = "0.0.0.0"
API_PORT = 8000

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = "INFO"

# ── Infrastructure (set via env vars in Docker; empty = local dev) ────────────
DATABASE_URL = os.environ.get("DATABASE_URL", "")
REDIS_URL = os.environ.get("REDIS_URL", "")
