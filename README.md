# Access Management Platform

> Projet 13 — OpenClassrooms Data & ML Engineering  
> Hybrid Role Mining + ABAC Drift Detection with containerised deployment  
> Dataset: UCI Amazon Employee Access (id=216)  
> Author: Shahul SHAIK

---

## What this project does

Mines implicit RBAC roles from historical access-request data, then detects when
new permission grants drift outside a user's expected role profile. Wraps the results
in a production-ready stack comparable to what SailPoint and Saviynt commercialise.

**Three core outputs:**

1. **Role Mining** — NMF (k=15, BIC-optimised) produces soft role memberships from
   the 32,769 × 7,518 user × permission matrix
2. **Drift Detection** — per-(employee, system) drift score using permission overlap
   against top-50 resources per cluster; XGBoost classifier (ROC-AUC 0.694)
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
│   │   └── preprocess.py       # encode, build user-permission matrix
│   │
│   ├── mining/
│   │   ├── matrix.py
│   │   ├── probabilistic.py    # NMF role mining (k=15)
│   │   ├── clustering.py
│   │   └── model_selection.py  # BIC optimisation
│   │
│   ├── drift/
│   │   ├── scorer.py           # overlap-based drift score
│   │   ├── detector.py         # XGBoost classifier
│   │   └── explainer.py        # SHAP explanations
│   │
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
│           ├── 01_access_intelligence.py
│           ├── 02_user_access_review.py
│           └── 03_user_access_simulation.py
│
├── models/                     # serialised NMF + XGBoost artefacts (joblib)
├── data/processed/             # feature matrices (parquet)
├── tests/
└── docs/
    └── project_management_report.md
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

# 3. Train models
make train

# 4. Start API (port 8000)
make api

# 5. Start dashboard (port 8501)
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
make data             # download + preprocess
make train            # run NMF mining + drift detector training
make test             # pytest
make lint             # black + flake8
```

---

## Key design decisions

- **NMF over k-means** — soft role membership; real employees belong to multiple
  organisational units. Hard clusters force artificial boundaries.
- **k=15 roles** — BIC-optimised; interpretable at the department/function level.
- **Balanced risk score** — `(n_high×1.0 + n_minor×0.5) / n_total`; tertile-based
  categories (Safe / Review / Escalate).
- **Redis cache** — fleet analytics (~30s to compute) cached as parquet bytes with
  24h TTL; shared across API + Dashboard replicas without hitting disk.
- **Non-blocking startup** — analytics computation fires as a background asyncio task
  so `/health` responds immediately and Docker health checks pass within `start_period`.
- **SHAP explanations** — per the 2026 ITDR Market Outlook, enterprise buyers require
  "evidence-grade reporting". A flagged event with no explanation is not actionable.
- **Audit log** — every simulation write is mirrored to `audit_log` for SOX-style traceability.

---

## Results

| Metric | Value |
|--------|-------|
| Roles mined (k) | 15 |
| Role coverage | 35.1% of employees have a dominant role (>50% membership) |
| Drift classifier ROC-AUC | 0.694 |
| High-drift flag rate | 76.8% of evaluated (employee, system) pairs |
| Fleet analytics compute time | ~30s (cached in Redis after first run) |

---

## References

- Frank, M., Buhmann, J., & Basin, D. (2012). *Role Mining with Probabilistic Models*. arXiv:1212.4775
- Cotrini, C. et al. (2019). *The Next 700 Policy Miners: A Universal Method for Building ABAC Miners* (UNICORN). arXiv:1908.05994
- UCI ML Repository — Amazon Employee Access Samples (id=216)
- Stoller, S. et al. (2019). *A Decision Tree Learning Approach for Mining Relationship-Based Access Control Policies*. arXiv:1909.12095
