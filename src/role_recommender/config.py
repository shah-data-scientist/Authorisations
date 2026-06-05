"""
config.py — centralised paths, hyperparameters, and constants.
All modules import from here; no magic strings elsewhere.
"""
import os
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
# APP_ROOT is set to /app in Docker so paths resolve correctly from the
# installed wheel (whose __file__ points into site-packages, not /app).
ROOT = Path(
    os.environ.get("APP_ROOT", str(Path(__file__).resolve().parents[2]))
)

DATA_RAW = ROOT / "data" / "raw"
DATA_INTERIM = ROOT / "data" / "interim"
DATA_PROCESSED = ROOT / "data" / "processed"
MODELS_DIR = ROOT / "models"

RAW_DATASET = DATA_RAW / "amazon_access_samples.csv"
PROCESSED_MATRIX = DATA_PROCESSED / "user_permission_matrix.parquet"
AUDIT_DB = ROOT / "audit" / "audit.db"

# ── UCI dataset ID ───────────────────────────────────────────────────────────
UCI_DATASET_ID = 216  # Amazon Access Samples

# ── Role mining hyperparameters ──────────────────────────────────────────────
ROLE_COUNT_MIN = 5
ROLE_COUNT_MAX = 30
ROLE_COUNT_DEFAULT = 15
RANDOM_STATE = 42

# ── Drift detection ──────────────────────────────────────────────────────────
# NMF cosine drift score thresholds (scorer.py)
DRIFT_NORMAL_THRESHOLD = 0.3   # score < 0.3  → Normal
DRIFT_HIGH_THRESHOLD = 0.7     # score >= 0.7 → High Drift (between → Minor)
DRIFT_CLASSIFIER_THRESHOLD = 0.7  # is_drift binary decision boundary

# ── API ──────────────────────────────────────────────────────────────────────
API_HOST = "0.0.0.0"
API_PORT = 8000

# ── Logging ──────────────────────────────────────────────────────────────────
LOG_LEVEL = "INFO"

# ── Infrastructure (set via env vars in Docker; empty = local dev) ───────────
DATABASE_URL = os.environ.get("DATABASE_URL", "")
REDIS_URL = os.environ.get("REDIS_URL", "")
