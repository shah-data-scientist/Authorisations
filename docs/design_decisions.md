# Design Decisions

This document records every non-trivial design choice made in this project
and the reasoning behind it. This is the most important file for portfolio
credibility — a recruiter or hiring manager reading this should understand
that you thought like an engineer, not just a notebook user.

---

## 1. Choice of dataset: UCI Amazon Access Samples (id=216)

**Why:** It contains real access-grant and access-removal events from
Amazon's internal systems (2010–2011), with categorical user attributes
(department, manager, title) and resource IDs. This is as close as a
public dataset gets to a real IAM audit log.

**Limitation acknowledged:** The dataset is from 2011 and does not include
temporal granularity finer than request date. It cannot simulate real-time
streaming scenarios.

---

## 2. Role mining method: NMF as a proxy for the Frank/Basin generative model

**Why NMF over k-means:**
k-means produces hard cluster assignments — every user belongs to exactly
one role. In practice, employees belong to multiple organisational units
and carry cross-functional permissions. NMF produces soft membership weights
(W matrix), which better reflects this reality.

**Why NMF over LDA:**
LDA requires count data interpreted as word frequencies. Our user-permission
matrix is binary. NMF works directly on binary/sparse matrices.

**Connection to Frank/Basin (arXiv:1212.4775):**
The Frank/Basin probabilistic model is a generative Bayesian formulation;
NMF is its MAP approximation under a Poisson likelihood. The paper validates
NMF as a practical implementation.

---

## 3. Number of roles: selected by BIC, not by business edict

**Approach:**
- Run NMF for k = 5, 7, 10, 12, 15, 20, 25, 30
- Compute reconstruction error (Frobenius norm) and Bayesian Information
  Criterion (BIC) for each k
- Choose the elbow / BIC minimum
- Sanity check: are the top-10 permissions per role interpretable as a job
  function? (Documented in notebooks/02_role_mining.ipynb)

**Default: k=15** — a reasonable starting point for a ~32,000-row dataset
with ~7,500 unique resources.

---

## 4. Drift scoring: purely unsupervised NMF cosine similarity

**Approach:**
The drift score for a (user, system) pair is:

```
drift_score = 1 − cosine_similarity(W[user], H[:, system])
```

Where `W[user]` is the employee's soft role membership vector (shape: n_roles)
and `H[:, system]` is the system's NMF loading across all roles (shape: n_roles).

A high dot product means the employee's role profile strongly overlaps with
the system's role profile → low drift. A low dot product means the system
belongs to roles the employee is not part of → high drift.

**Why not a classifier:**
An initial implementation used XGBoost trained on access-revocation events
(`ACTION=0`) as implicit negative labels. This was abandoned for two reasons:

1. **Weak labels** — `ACTION=0` in the Amazon dataset represents provisioning
   *refusals* (access was never granted), not *revocations* (access was granted
   then taken away). Treating refusals as anomaly labels is methodologically
   incorrect: a refused request is not evidence that the access would have been
   anomalous.

2. **Matrix contamination** — Including `ACTION=0` rows in the user-permission
   matrix inflated users' apparent access rights (recording systems they were
   refused access to as if they had access), corrupting the NMF decomposition.

The NMF cosine score is self-sufficient: it is trained on granted-only access
data and scores any (user, system) pair without requiring labels.

**Evaluation (unsupervised metrics):**

| Metric | Value |
|--------|-------|
| Reconstruction MSE | 0.0033 |
| Self-consistency gap | +0.519 (own systems 0.34 vs non-access 0.86) |
| Cluster separation | +0.740 (same-cluster 0.18 vs cross-cluster 0.92) |

The cluster separation of 0.74 confirms the score cleanly discriminates
same-role from cross-role access — which is exactly what a drift detector needs.

---

## 5. Drift thresholds: 0.3 and 0.7

**Thresholds:**
- `< 0.3` → **Normal** — system fits the employee's role profile well
- `0.3–0.7` → **Minor Drift** — partial role overlap; quick review recommended
- `≥ 0.7` → **High Drift** — system is outside the employee's role profile

**Why these values:**
The self-consistency evaluation shows own-system mean drift of 0.34 and
non-access mean drift of 0.86. The 0.3 / 0.7 boundaries sit at natural
inflection points between those two distributions. They are not arbitrary:
the intra-cluster mean (0.18) lies comfortably below 0.3, and the
inter-cluster mean (0.92) lies well above 0.7.

**Balanced Risk Score:**
```
balanced_risk_score = (n_high × 1.0 + n_minor × 0.5) / n_total
```
Aggregates per-system scores into a single employee-level risk number.
Risk categories (Low / Medium / High) are tertile-based so each band
contains approximately one-third of the fleet.

---

## 6. Why FastAPI over Flask

FastAPI provides automatic OpenAPI docs at `/docs`, native Pydantic
validation, and async support. For a portfolio project serving a Streamlit
frontend, this gives a better developer experience and is what most
production security-data teams actually use (2024–2026 job postings).

---

## 7. Audit persistence: SQLite over PostgreSQL

**Decision:** The simulation audit trail (`simulations` + `audit_log` tables)
uses SQLite via a synchronous SQLAlchemy engine, not PostgreSQL with asyncpg.

**Why SQLite:**
- Zero external dependencies — SQLite is built into Python. No separate
  database service, no connection string, no credentials to manage.
- Tables are created automatically at API startup via `create_tables()`
  (SQLAlchemy `Base.metadata.create_all`). No Alembic migration runner needed.
- The Docker stack drops from 6 services to 4 (removed `db` and `migrate`).
  The DB file lives at `audit/audit.db`, mounted as a named Docker volume
  so data persists across container restarts.
- WAL (Write-Ahead Logging) mode is enabled at connection time for safe
  concurrent reads from the dashboard while the API writes.

**Trade-off acknowledged:** SQLite does not support multiple simultaneous
writers and is not suitable for a multi-replica API deployment. For a
production system with horizontal scaling, replacing the SQLite engine with
PostgreSQL (changing the connection string in `config.py`) is the upgrade path.
The ORM models and endpoints are database-agnostic; only the engine URL and
the `JSONB`→`Text` column type change.

**Audit events logged:**

| Action | Trigger |
|---|---|
| `simulation_created` | `POST /simulations/` — drift score computed for a new access request |
| `simulation_approved` | `PATCH /simulations/{id}` — reviewer approves the access |
| `simulation_denied` | `PATCH /simulations/{id}` — reviewer denies the access |
| `access_revoked` | `POST /simulations/revoke` — User Access Review "Revoke Access" button |

---

## 8. What this project does NOT do (and why)

| Omission | Reason |
|---|---|
| Real-time Kafka/streaming ingestion | Out of scope for a 6-week portfolio project; noted as a future extension |
| Multi-tenancy / auth on the API | Not needed for a demo; add OAuth2 before production |
| LDAP/AD integration | No public LDAP dataset available; simulated via role attributes |
| Temporal drift (comparing week-over-week) | Dataset lacks fine-grained timestamps; flagged as a known limitation |
| Supervised classifier | Removed: labels (ACTION=0) are provisioning refusals, not confirmed anomalies |
