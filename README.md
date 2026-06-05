# Access Management Platform

> Projet 13 — OpenClassrooms Data & ML Engineering  
> Hybrid Role Mining + NMF Cosine Drift Detection with containerised deployment  
> Dataset: UCI Amazon Employee Access (id=216)  
> Author: Shahul SHAIK

---

## What this project does

Mines implicit RBAC roles from historical access-request data, then detects when
new permission grants drift outside a user's expected role profile. Wraps the results
in a production-ready stack comparable to what SailPoint and Saviynt commercialise.

**Three core outputs:**

1. **Role Mining** — NMF (k=15, BIC-optimised) decomposes the 340 × 7,226
   user × permission matrix into soft role memberships (W) and role-permission
   profiles (H)
2. **Drift Detection** — continuous NMF cosine drift score per (employee, system)
   pair: `1 − cosine_similarity(W[user], H[:, system])`. Fully unsupervised —
   no labelled anomalies required.
3. **Dashboard + API** — Streamlit UI for access review, simulation, and approval
   workflow; FastAPI backend with full CRUD and audit trail in PostgreSQL

---

## Architecture

```
                        Browser / corporate network
                               │
                          ┌────▼─────┐
                          │  Nginx   │  :80
                          └──┬────┬──┘
                /api/*        │    │  /
         ┌───────────────────┘    └──────────────────┐
         │                                           │
   ┌─────▼──────┐                          ┌─────────▼──────┐
   │  FastAPI   │  :8000                   │   Streamlit    │  :8501
   │  gunicorn  │                          │   dashboard    │
   └──┬──────┬──┘                          └────────────────┘
      │      │
 ┌────▼────┐ └──────────────┐
 │  Redis  │  :6379   ┌─────▼──────┐
 │  cache  │          │ PostgreSQL │  :5432
 └─────────┘          └────────────┘
```

| Service     | Image                    | Purpose                                          |
|-------------|--------------------------|--------------------------------------------------|
| `nginx`     | `nginx:alpine`           | Reverse proxy, routing                           |
| `api`       | `./Dockerfile.api`       | FastAPI + gunicorn (2 uvicorn workers)           |
| `dashboard` | `./Dockerfile.dashboard` | Streamlit UI                                     |
| `db`        | `postgres:16-alpine`     | Simulation history, audit log                    |
| `redis`     | `redis:7-alpine`         | Fleet analytics cache (24h TTL)                  |
| `migrate`   | same as `api`            | One-shot Alembic migration on startup            |

---

## Project structure

```
.
├── Dockerfile.api              # multi-stage: build wheel → runtime + gunicorn
├── Dockerfile.dashboard        # streamlit image
├── docker-compose.yml          # all 6 services
├── nginx/nginx.conf            # proxy rules
├── env.example                 # secrets template
├── pyproject.toml
├── Makefile
├── evaluate_model.py           # unsupervised performance metrics
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/001_init.py   # simulations + audit_log tables
│
├── src/role_recommender/
│   ├── config.py
│   ├── cache.py                # Redis helper (get_df / set_df)
│   │
│   ├── data/
│   │   ├── download.py         # fetch UCI dataset
│   │   └── preprocess.py       # clean, filter granted-only, build binary matrix
│   │
│   ├── mining/
│   │   ├── matrix.py
│   │   ├── probabilistic.py    # NMF role mining (k=15, BIC-optimised)
│   │   ├── clustering.py       # k-means baseline (comparison only)
│   │   └── model_selection.py  # BIC optimisation across k=[5,7,10,12,15,20,25,30]
│   │
│   ├── drift/
│   │   └── scorer.py           # NMF cosine drift score (continuous 0–1)
│   │
│   ├── analytics.py            # balanced risk score + fleet analytics
│   ├── db/
│   │   ├── models.py           # Simulation + AuditLog ORM
│   │   └── session.py          # async SQLAlchemy session factory
│   │
│   ├── api/
│   │   ├── main.py             # FastAPI entry point
│   │   ├── schemas.py
│   │   └── routers/
│   │       ├── users.py
│   │       ├── roles.py
│   │       ├── drift.py
│   │       ├── analytics.py    # fleet analytics (Redis-backed)
│   │       └── simulations.py  # CRUD + approval workflow
│   │
│   └── dashboard/
│       ├── app.py
│       ├── cluster_utils.py    # fleet analytics loader (Redis → parquet → compute)
│       └── pages/
│           ├── 01_access_intelligence.py   # fleet overview + system risk
│           ├── 02_user_access_review.py    # fleet risk table + employee drilldown
│           └── 03_user_access_simulation.py # grant simulation + scoring
│
├── models/                     # serialised NMF artefact (joblib)
├── data/processed/             # user_permission_matrix.parquet + fleet_analytics.parquet
├── tests/
└── docs/
```

---

## Quickstart — Docker (recommended)

```bash
# 1. Copy and configure secrets
cp env.example .env
# edit .env → set POSTGRES_PASSWORD

# 2. Build and start all services (detached)
make docker-restart
# or: docker compose up --build -d

# 3. Open the dashboard
#    http://localhost          (via Nginx)
#    http://localhost:8501     (direct)
#    http://localhost:8000/docs  (API docs)
```

All services include health checks. The `migrate` container runs `alembic upgrade head`
before the API starts.

---

## Quickstart — local (dev)

```bash
# 1. Install
pip install -e ".[dev]"

# 2. Download and preprocess data
make data

# 3. Train the NMF role miner
make train

# 4. (Optional) Evaluate model quality
python evaluate_model.py

# 5. Start API (port 8000)
make api

# 6. Start dashboard (port 8501)
make dashboard
```

Requires a local PostgreSQL instance if you want simulation persistence.
Set `DATABASE_URL` and `REDIS_URL` in your shell or `.env` file, or leave
them unset — the app falls back to in-process state gracefully.

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check |
| GET | `/users/{id}/role` | Role assignment for an employee |
| GET | `/users/{id}/permissions` | Resolved permissions |
| GET | `/roles` | All mined roles |
| GET | `/roles/{id}` | Role detail + top resources |
| POST | `/drift/score` | Score a new access event |
| GET | `/analytics/fleet` | Pre-computed fleet stats |
| POST | `/simulations` | Save simulation result |
| GET | `/simulations` | List simulations (filter by status/employee) |
| GET | `/simulations/history` | Employee simulation history |
| PATCH | `/simulations/{id}` | Update review status (approved/denied) |

---

## Make targets

```bash
make docker-restart   # docker compose up --build -d
make docker-dev       # docker compose up --build  (foreground, with logs)
make docker-down      # stop all containers
make docker-clean     # stop + remove volumes + local images
make data             # download + preprocess (granted-only matrix)
make train            # run NMF role mining
make test             # pytest
make lint             # black + flake8
```

---

## Key design decisions

- **NMF over k-means** — soft role membership; real employees belong to multiple
  organisational units. Hard clusters force artificial boundaries.
- **k=15 roles** — BIC-optimised; interpretable at the department/function level.
- **Granted-only matrix** — only `ACTION=1` rows are used. Denied-access rows
  (`ACTION=0`) are Amazon's provisioning refusals, not revocations; they do not
  carry anomaly signal and were removed from the pipeline.
- **Unsupervised drift scoring** — `1 − cosine_similarity(W[user], H[:, system])`
  requires no labels. Thresholds: < 0.3 = Normal, 0.3–0.7 = Minor Drift, ≥ 0.7 = High Drift.
- **Balanced risk score** — `(n_high×1.0 + n_minor×0.5) / n_total`; tertile-based
  categories (Low / Medium / High) ensure each band contains ~⅓ of employees.
- **Redis cache** — fleet analytics (~30s to compute) cached as parquet bytes with
  24h TTL; shared across API + Dashboard replicas without hitting disk.
- **Non-blocking startup** — analytics computation fires as a background asyncio task
  so `/health` responds immediately and Docker health checks pass within `start_period`.
- **Audit log** — every simulation write is mirrored to `audit_log` for SOX-style traceability.

---

## Results

| Metric | Value |
|--------|-------|
| Roles mined (k) | 15 |
| Matrix dimensions | 340 users × 7,226 resources |
| Reconstruction MSE (X vs W·H) | 0.0033 |
| Strong role membership (>70%) | 15.0% of employees |
| Self-consistency gap | +0.519 (own-system drift 0.34 vs non-access 0.86) |
| Cluster separation | +0.740 (same-cluster drift 0.18 vs cross-cluster 0.92) |
| Fleet analytics compute time | ~30s (cached in Redis after first run) |

The self-consistency gap and cluster separation confirm that the NMF cosine score
cleanly distinguishes access that fits an employee's role profile from access that
does not — with no labelled training data required.

---

## References

- Frank, M., Buhmann, J., & Basin, D. (2012). *Role Mining with Probabilistic Models*. arXiv:1212.4775
- Cotrini, C. et al. (2019). *The Next 700 Policy Miners: A Universal Method for Building ABAC Miners* (UNICORN). arXiv:1908.05994
- UCI ML Repository — Amazon Employee Access Samples (id=216)
- Stoller, S. et al. (2019). *A Decision Tree Learning Approach for Mining Relationship-Based Access Control Policies*. arXiv:1909.12095
