"""
evaluation.py — Model quality report for the NMF role miner + XGBoost drift system.

Three sections:
  1. NMF Role Mining   — reconstruction error, coverage, weight entropy
  2. XGBoost Classifier — 5-fold cross-validated ROC-AUC, precision, recall, F1
  3. Rule-based Scorer  — fleet-wide drift score distribution

Run with:
    python -m role_recommender.evaluation
or:
    make evaluate

Output is printed to stdout and saved to models/evaluation_report.txt.
"""
from __future__ import annotations

import textwrap
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger
from tqdm import tqdm

from role_recommender.config import (
    DATA_PROCESSED,
    MODELS_DIR,
    PROCESSED_EVENTS,
    PROCESSED_MATRIX,
    RANDOM_STATE,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _load_miner():
    from role_recommender.mining.probabilistic import ProbabilisticRoleMiner
    path = next(MODELS_DIR.glob("role_miner_*.joblib"), None)
    if path is None:
        raise FileNotFoundError(
            "No trained role miner found. Run `make train` first."
        )
    return ProbabilisticRoleMiner.load(path)


def _section(title: str, width: int = 60) -> str:
    bar = "─" * width
    return f"\n{title}\n{bar}"


# ── Section 1: NMF Role Mining ───────────────────────────────────────────────

def evaluate_nmf(miner, matrix: pd.DataFrame) -> dict:
    """
    Compute NMF quality metrics.

    Returns
    -------
    dict with:
      reconstruction_error_abs   Frobenius norm ||X - WH||_F
      reconstruction_error_rel   Relative error (normalised by ||X||_F)
      mean_coverage              Avg fraction of each user's accesses explained
                                 by their dominant cluster's top-50 systems
      pct_fully_covered          % of users where coverage == 1.0
      mean_weight_entropy        Avg Shannon entropy of cluster weight vectors
                                 (lower = cleaner membership; max = ln(k))
    """
    X = matrix.values.astype(float)
    abs_err = miner.reconstruction_error()
    rel_err = abs_err / (np.linalg.norm(X, "fro") + 1e-10)

    # Coverage: per user, fraction of actual accesses in dominant cluster top-50
    coverage_scores: list[float] = []
    entropies: list[float] = []

    for user_id in tqdm(miner.user_index, desc="NMF coverage", leave=False):
        row = matrix.loc[user_id]
        actual = set(row[row > 0].index.tolist())
        if not actual:
            continue

        dom = miner.get_user_role(user_id)
        cluster_top = set(miner.get_role_permissions(dom, top_n=50))
        coverage_scores.append(len(actual & cluster_top) / len(actual))

        weights = miner.get_user_role_weights(user_id)
        w = weights[weights > 0]
        entropies.append(float(-np.sum(w * np.log(w + 1e-12))))

    return {
        "reconstruction_error_abs": float(abs_err),
        "reconstruction_error_rel": float(rel_err),
        "mean_coverage": float(np.mean(coverage_scores)),
        "pct_fully_covered": float(
            np.mean([c == 1.0 for c in coverage_scores])
        ),
        "mean_weight_entropy": float(np.mean(entropies)),
        "max_possible_entropy": float(np.log(miner.n_roles)),
        "n_roles": miner.n_roles,
    }


# ── Section 2: XGBoost Drift Classifier ─────────────────────────────────────

def _build_features(
    events: pd.DataFrame,
    miner,
    matrix: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build the XGBoost feature matrix from the events log.
    Reimplements detector.build_features() with corrected scorer key names.
    """
    from role_recommender.drift.scorer import DriftScorer

    scorer = DriftScorer(miner)
    resource_freq = matrix.sum(axis=0) / len(matrix)
    user_perm_count = matrix.sum(axis=1)

    rows: list[dict] = []
    for _, ev in tqdm(
        events.iterrows(), total=len(events),
        desc="Building features", leave=False,
    ):
        user_id = ev.get("ROLE_CODE")
        resource_id = ev.get("RESOURCE")

        if user_id not in miner.user_index:
            continue
        if resource_id not in miner.resource_index:
            continue

        result = scorer.score(user_id, resource_id)
        dom = miner.get_user_role(user_id)
        weights = miner.get_user_role_weights(user_id)

        rows.append({
            "drift_score": result["drift_score"],
            "dominant_role": dom,
            "role_weight_dominant": float(weights[dom]),
            "resource_frequency": float(
                resource_freq.get(resource_id, 0.0)
            ),
            "user_permission_count": int(
                user_perm_count.get(user_id, 0)
            ),
            "ACTION": int(ev.get("ACTION", 1)),
        })

    return pd.DataFrame(rows)


def evaluate_classifier(
    events: pd.DataFrame, miner, matrix: pd.DataFrame
) -> dict | None:
    """
    5-fold stratified cross-validation of the XGBoost drift classifier.
    Labels: ACTION==0 (denied/revoked) → treated as anomalous (y=1).

    Returns None if there are too few samples to cross-validate.
    """
    from sklearn.model_selection import StratifiedKFold, cross_validate
    from xgboost import XGBClassifier

    features = _build_features(events, miner, matrix)
    if len(features) < 50:
        logger.warning("Too few feature rows to cross-validate classifier.")
        return None

    feature_cols = [
        "drift_score", "dominant_role", "role_weight_dominant",
        "resource_frequency", "user_permission_count",
    ]
    X = features[feature_cols]
    y = (features["ACTION"] == 0).astype(int)

    pos_frac = y.mean()
    scale_pw = max(1.0, (1 - pos_frac) / (pos_frac + 1e-10))

    clf = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        scale_pos_weight=scale_pw,
        random_state=RANDOM_STATE,
        eval_metric="logloss",
        verbosity=0,
    )

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    scoring = ["roc_auc", "precision", "recall", "f1"]
    results = cross_validate(clf, X, y, cv=cv, scoring=scoring)

    # Feature importances from a single fit on the full set
    clf.fit(X, y)
    importances = dict(
        zip(feature_cols, clf.feature_importances_.tolist())
    )
    importances = dict(
        sorted(importances.items(), key=lambda x: x[1], reverse=True)
    )

    return {
        "n_events": len(features),
        "pct_anomalous": float(pos_frac),
        "roc_auc_mean": float(np.mean(results["test_roc_auc"])),
        "roc_auc_std": float(np.std(results["test_roc_auc"])),
        "precision_mean": float(np.mean(results["test_precision"])),
        "recall_mean": float(np.mean(results["test_recall"])),
        "f1_mean": float(np.mean(results["test_f1"])),
        "feature_importances": importances,
    }


# ── Section 3: Rule-based Drift Scorer ──────────────────────────────────────

def evaluate_scorer(miner, matrix: pd.DataFrame) -> dict:
    """
    Fleet-wide distribution of drift scores across all current accesses.
    Uses fleet_analytics.parquet if fresh (< 24 h), else computes from scratch.
    """
    analytics_path = DATA_PROCESSED / "fleet_analytics.parquet"

    if analytics_path.exists():
        import time
        age = time.time() - analytics_path.stat().st_mtime
        if age < 86_400:
            df = pd.read_parquet(analytics_path)
            total_systems = int(df["n_systems"].sum())
            n_high = int(df["n_high"].sum())
            n_minor = int(df["n_minor"].sum())
            n_normal = int(df["n_normal"].sum())
            return {
                "source": "fleet_analytics.parquet",
                "n_employees": len(df),
                "total_system_accesses": total_systems,
                "n_normal": n_normal,
                "n_minor": n_minor,
                "n_high": n_high,
                "pct_normal": n_normal / total_systems,
                "pct_minor": n_minor / total_systems,
                "pct_high": n_high / total_systems,
                "mean_anomaly_rate": float(df["anomaly_rate"].mean()),
                "mean_balanced_risk_score": float(
                    df["balanced_risk_score"].mean()
                ),
                "risk_category_counts": (
                    df["risk_category"].value_counts().to_dict()
                ),
            }

    # Compute on the fly (slow — only if parquet is missing)
    from role_recommender.drift.scorer import DriftScorer
    scorer = DriftScorer(miner)

    n_normal = n_minor = n_high = 0
    n_employees = 0

    for user_id in tqdm(
        matrix.index, desc="Scoring fleet", leave=False
    ):
        user_row = matrix.loc[user_id]
        systems = user_row[user_row > 0].index.tolist()
        n_employees += 1
        for sys_id in systems:
            ds = scorer.score(user_id, sys_id)["drift_score"]
            if ds >= 1.0:
                n_high += 1
            elif ds > 0.0:
                n_minor += 1
            else:
                n_normal += 1

    total = n_normal + n_minor + n_high
    return {
        "source": "computed",
        "n_employees": n_employees,
        "total_system_accesses": total,
        "n_normal": n_normal,
        "n_minor": n_minor,
        "n_high": n_high,
        "pct_normal": n_normal / total if total else 0.0,
        "pct_minor": n_minor / total if total else 0.0,
        "pct_high": n_high / total if total else 0.0,
        "mean_anomaly_rate": None,
        "mean_balanced_risk_score": None,
        "risk_category_counts": None,
    }


# ── Report formatter ─────────────────────────────────────────────────────────

def _fmt_pct(v: float) -> str:
    return f"{v * 100:.1f}%"


def format_report(nmf: dict, clf: dict | None, scorer: dict) -> str:
    width = 62
    border = "═" * width
    ts = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")

    lines: list[str] = [
        border,
        " ACCESS MANAGEMENT PLATFORM — MODEL EVALUATION REPORT".center(width),
        f" Generated: {ts}".center(width),
        border,
    ]

    # ── NMF ──
    lines.append(_section("1 · NMF ROLE MINING", width))
    lines += [
        f"  Clusters (k):                    {nmf['n_roles']}",
        f"  Reconstruction error (Frobenius): {nmf['reconstruction_error_abs']:.4f}",
        f"  Relative reconstruction error:    "
        f"{_fmt_pct(nmf['reconstruction_error_rel'])}",
        "",
        f"  Mean access coverage rate:        "
        f"{_fmt_pct(nmf['mean_coverage'])}",
        f"  Users fully covered (100%):       "
        f"{_fmt_pct(nmf['pct_fully_covered'])}",
        "",
        "  Coverage = fraction of a user's actual system accesses",
        "  explained by their dominant cluster's top-50 systems.",
        "  Higher is better. <50% suggests k may be too small.",
        "",
        f"  Mean cluster-weight entropy:      "
        f"{nmf['mean_weight_entropy']:.3f}",
        f"  Max possible entropy (ln {nmf['n_roles']}):        "
        f"{nmf['max_possible_entropy']:.3f}",
        "",
        "  Entropy measures how spread a user's membership is",
        "  across clusters. Low → clear assignment; high → fuzzy.",
    ]

    # ── Classifier ──
    lines.append(_section("2 · XGBOOST DRIFT CLASSIFIER  (5-fold CV)", width))
    lines += [
        "  ⚠  Label caveat: labels are ACCESS DENIALS (ACTION=0),",
        "     not confirmed anomalies. Metrics reflect how well",
        "     the model predicts denied requests, not true",
        "     security violations.",
        "",
    ]
    if clf is None:
        lines.append("  Skipped — insufficient events to cross-validate.")
    else:
        lines += [
            f"  Training events:                  {clf['n_events']:,}",
            f"  Anomalous label rate:             "
            f"{_fmt_pct(clf['pct_anomalous'])}",
            "",
            f"  ROC-AUC:    {clf['roc_auc_mean']:.3f}  "
            f"± {clf['roc_auc_std']:.3f}",
            f"  Precision:  {clf['precision_mean']:.3f}",
            f"  Recall:     {clf['recall_mean']:.3f}",
            f"  F1 Score:   {clf['f1_mean']:.3f}",
            "",
            "  Feature importances:",
        ]
        for feat, imp in clf["feature_importances"].items():
            bar = "█" * int(imp * 30)
            lines.append(f"    {feat:<28} {imp:.3f}  {bar}")

    # ── Scorer ──
    lines.append(_section("3 · RULE-BASED DRIFT SCORER — FLEET DISTRIBUTION", width))
    lines += [
        f"  Employees:               {scorer['n_employees']:,}",
        f"  Total system accesses:   {scorer['total_system_accesses']:,}",
        "",
        f"  Normal   (0.0):  {scorer['n_normal']:>6,}  "
        f"({_fmt_pct(scorer['pct_normal'])})",
        f"  Minor    (0.3):  {scorer['n_minor']:>6,}  "
        f"({_fmt_pct(scorer['pct_minor'])})",
        f"  High     (1.0):  {scorer['n_high']:>6,}  "
        f"({_fmt_pct(scorer['pct_high'])})",
    ]

    if scorer.get("mean_anomaly_rate") is not None:
        lines += [
            "",
            f"  Mean anomaly rate / employee:  "
            f"{_fmt_pct(scorer['mean_anomaly_rate'])}",
            f"  Mean Balanced Risk Score:      "
            f"{scorer['mean_balanced_risk_score']:.4f}",
        ]

    if scorer.get("risk_category_counts"):
        lines.append("")
        lines.append("  Risk category distribution (tertile-based):")
        for cat in ["Low", "Medium", "High"]:
            n = scorer["risk_category_counts"].get(cat, 0)
            pct = n / scorer["n_employees"] * 100
            lines.append(f"    {cat:<8}  {n:>4} employees  ({pct:.1f}%)")

    lines += [
        "",
        "  ⚠  High Drift does not confirm a security violation.",
        "     It flags accesses unusual relative to the cluster",
        "     model. Expert review determines true risk.",
        "",
        border,
    ]

    return "\n".join(lines)


# ── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    logger.info("Loading models…")
    miner = _load_miner()
    matrix = pd.read_parquet(PROCESSED_MATRIX)
    events = pd.read_parquet(PROCESSED_EVENTS)

    logger.info("Evaluating NMF role miner…")
    nmf_metrics = evaluate_nmf(miner, matrix)

    logger.info("Evaluating XGBoost classifier (5-fold CV)…")
    clf_metrics = evaluate_classifier(events, miner, matrix)

    logger.info("Computing drift scorer fleet distribution…")
    scorer_metrics = evaluate_scorer(miner, matrix)

    report = format_report(nmf_metrics, clf_metrics, scorer_metrics)

    print("\n" + report)

    out_path = MODELS_DIR / "evaluation_report.txt"
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    logger.success(f"Report saved → {out_path}")


if __name__ == "__main__":
    main()
