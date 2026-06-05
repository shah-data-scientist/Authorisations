"""
evaluate_model.py — unsupervised performance metrics for NMF + drift scorer.
"""
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from role_recommender.mining.probabilistic import ProbabilisticRoleMiner
from role_recommender.drift.scorer import DriftScorer
from role_recommender.config import MODELS_DIR, PROCESSED_MATRIX

rng = np.random.default_rng(42)

print("Loading model and matrix...")
miner = ProbabilisticRoleMiner.load(next(MODELS_DIR.glob("role_miner_*.joblib")))
matrix = pd.read_parquet(PROCESSED_MATRIX)
scorer = DriftScorer(miner)

W = miner.W   # (n_users, n_roles)
H = miner.H   # (n_roles, n_systems)

# ── 1. NMF reconstruction error ───────────────────────────────────────────────
print("\n── 1. NMF Reconstruction Error ──")
X = matrix.values.astype(float)
X_hat = W @ H
reconstruction_error = np.mean((X - X_hat) ** 2)
print(f"  MSE (X vs W·H):       {reconstruction_error:.4f}")
print(f"  Frobenius norm error: {np.linalg.norm(X - X_hat):.2f}")

# ── 2. Role coverage ──────────────────────────────────────────────────────────
print("\n── 2. Role Coverage ──")
dominant_weights = W.max(axis=1)
strong   = (dominant_weights > 0.7).mean()
partial  = ((dominant_weights > 0.3) & (dominant_weights <= 0.7)).mean()
weak     = (dominant_weights <= 0.3).mean()
print(f"  Strong membership (>70%):   {strong:.1%} of employees")
print(f"  Partial membership (30-70%): {partial:.1%} of employees")
print(f"  Weak membership (<30%):     {weak:.1%} of employees")

# ── 3. Self-consistency gap ───────────────────────────────────────────────────
print("\n── 3. Self-Consistency Gap ──")
print("  Sampling 50 users × 20 systems each (own vs random non-access)...")

own_scores, rand_scores = [], []
users = matrix.index.tolist()
sample_users = rng.choice(users, size=min(50, len(users)), replace=False)

for user_id in sample_users:
    row = matrix.loc[user_id]
    own_systems = row[row > 0].index.tolist()
    non_systems = row[row == 0].index.tolist()

    if not own_systems or not non_systems:
        continue

    # sample up to 20 own systems
    sample_own = rng.choice(
        own_systems, size=min(20, len(own_systems)), replace=False
    )
    for s in sample_own:
        own_scores.append(scorer.score(user_id, s)["drift_score"])

    # sample 20 random non-access systems
    sample_rand = rng.choice(
        non_systems, size=min(20, len(non_systems)), replace=False
    )
    for s in sample_rand:
        rand_scores.append(scorer.score(user_id, s)["drift_score"])

own_mean  = np.mean(own_scores)
rand_mean = np.mean(rand_scores)
gap       = rand_mean - own_mean
print(f"  Mean drift — own systems:        {own_mean:.4f}")
print(f"  Mean drift — non-access systems: {rand_mean:.4f}")
print(f"  Self-consistency gap:            {gap:.4f}  (higher = better)")

# ── 4. Intra vs inter-cluster separation ─────────────────────────────────────
print("\n── 4. Intra vs Inter-Cluster Separation ──")
print("  Sampling 500 random (user, system) pairs each...")

dominant_roles = W.argmax(axis=1)  # dominant cluster per user
system_dominant = H.argmax(axis=0)  # dominant cluster per system

users_list   = matrix.index.tolist()
systems_list = matrix.columns.tolist()

intra_scores, inter_scores = [], []

for _ in range(500):
    u_idx = rng.integers(0, len(users_list))
    s_idx = rng.integers(0, len(systems_list))
    user_id   = users_list[u_idx]
    system_id = systems_list[s_idx]
    ds = scorer.score(user_id, system_id)["drift_score"]

    if dominant_roles[u_idx] == system_dominant[s_idx]:
        intra_scores.append(ds)
    else:
        inter_scores.append(ds)

intra_mean = np.mean(intra_scores)
inter_mean = np.mean(inter_scores)
separation = inter_mean - intra_mean
print(f"  Mean drift — same cluster:      {intra_mean:.4f}")
print(f"  Mean drift — different cluster: {inter_mean:.4f}")
print(f"  Cluster separation:             {separation:.4f}  (higher = better)")

# ── 5. Score distribution ─────────────────────────────────────────────────────
print("\n── 5. Score Distribution (own systems, 50 users × 20 systems) ──")
all_own = np.array(own_scores)
for label, lo, hi in [
    ("Normal      (< 0.3)", 0.0, 0.3),
    ("Minor Drift (0.3–0.7)", 0.3, 0.7),
    ("High Drift  (>= 0.7)", 0.7, 1.01),
]:
    frac = ((all_own >= lo) & (all_own < hi)).mean()
    print(f"  {label}: {frac:.1%}")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n── Summary ──")
print(f"  Reconstruction MSE:      {reconstruction_error:.4f}")
print(f"  Strong role coverage:    {strong:.1%}")
print(f"  Self-consistency gap:    {gap:.4f}")
print(f"  Cluster separation:      {separation:.4f}")
print(f"  Total own scores:        {len(own_scores)}")
print(f"  Total random scores:     {len(rand_scores)}")
