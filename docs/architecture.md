# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Streamlit Dashboard                       │
│  ┌──────────────────┐ ┌────────────────────┐ ┌───────────────┐  │
│  │ Access           │ │ User Access        │ │ User Access   │  │
│  │ Intelligence     │ │ Review             │ │ Simulation    │  │
│  └──────┬───────────┘ └──────┬─────────────┘ └──────┬────────┘  │
│         └────────────────────┴────────────────────── ┘          │
│                     HTTP (httpx) + st.cache_resource             │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                    ┌───────────▼────────────┐
                    │     FastAPI (port 8000) │
                    │  /users  /roles  /drift │
                    │  /analytics  /simulations│
                    └───────────┬────────────┘
                                │ loads once at startup
                    ┌───────────▼────────────┐
                    │   _model_loader.py      │
                    │  (lru_cache singletons) │
                    └──┬────────────────┬─────┘
                       │                │
          ┌────────────▼───┐   ┌────────▼──────────┐
          │ Probabilistic  │   │   DriftScorer      │
          │  RoleMiner     │   │  (NMF cosine)      │
          │  (NMF model)   │   └───────────────────┘
          └────────────────┘
                   │
          ┌────────▼────────┐         ┌──────────────┐
          │ models/          │         │  SQLite       │
          │ role_miner_      │         │ audit/audit.db│
          │ *.joblib         │         │  simulations  │
          └─────────────────┘         │  + audit_log  │
                                      └──────────────┘
                                      ┌──────────────┐
                                      │    Redis      │
                                      │ fleet cache   │
                                      │   (24h TTL)   │
                                      └──────────────┘

Nginx (port 80) routes:
  /api/* → FastAPI :8000
  /      → Streamlit :8501

Data pipeline (offline):
  UCI API → data/raw/ → data/interim/ → data/processed/
      ↓ (granted-only, ACTION=1)
  NMF training → models/role_miner_*.joblib
```

---

## Component Descriptions

### Data Pipeline (`src/role_recommender/data/`)
| File | Responsibility |
|---|---|
| `download.py` | Fetches dataset from UCI ML Repo via `ucimlrepo` |
| `preprocess.py` | Cleans data, filters to `ACTION=1` (granted only), builds binary user × resource matrix |

### Role Mining (`src/role_recommender/mining/`)
| File | Responsibility |
|---|---|
| `probabilistic.py` | NMF-based role miner (Frank/Basin approximation); saves W, H, user_index, resource_index |
| `clustering.py` | k-means baseline for comparison |
| `model_selection.py` | BIC / elbow analysis for choosing k from [5, 7, 10, 12, 15, 20, 25, 30] |
| `matrix.py` | Matrix load + stats helpers |

### Drift Detection (`src/role_recommender/drift/`)
| File | Responsibility |
|---|---|
| `scorer.py` | NMF cosine drift score: `1 − cosine_similarity(W[user], H[:, system])`. Continuous 0–1. |

### Analytics (`src/role_recommender/`)
| File | Responsibility |
|---|---|
| `analytics.py` | Computes balanced risk score + fleet statistics per employee; tertile-based risk categories |
| `cache.py` | Redis helper: `get_df` / `set_df` with 24h TTL; no-op fallback when Redis is unavailable |

### API (`src/role_recommender/api/`)
| File | Responsibility |
|---|---|
| `main.py` | FastAPI app, CORS middleware, router registration, background analytics warm-up |
| `schemas.py` | Pydantic request/response models |
| `_model_loader.py` | Singleton model/matrix loading (lru_cache) — HTTPException 503 if model missing |
| `routers/users.py` | `GET /users/{id}/role`, `GET /users/{id}/permissions` |
| `routers/roles.py` | `GET /roles/`, `GET /roles/{id}` |
| `routers/drift.py` | `POST /drift/score` — score a new access event |
| `routers/analytics.py` | `GET /analytics/fleet` — Redis → parquet → compute |
| `routers/simulations.py` | CRUD for simulation history + approval workflow; `POST /simulations/revoke` for access revocation events |

### Database (`src/role_recommender/db/`)
| File | Responsibility |
|---|---|
| `models.py` | SQLAlchemy ORM: `Simulation` (approval lifecycle) + `AuditLog` (immutable event log); uses `Text` for JSON fields (SQLite-compatible) |
| `session.py` | Sync SQLite session factory; `create_tables()` called at API startup; WAL mode enabled; DB file at `audit/audit.db` |

### Dashboard (`src/role_recommender/dashboard/`)
| File | Responsibility |
|---|---|
| `app.py` | Entry point + landing page |
| `cluster_utils.py` | Shared data loaders + cached computation helpers (Redis → parquet → compute) |
| `pages/01_access_intelligence.py` | Fleet overview: cluster membership, system risk analysis |
| `pages/02_user_access_review.py` | Fleet risk table sorted by balanced risk score + employee drilldown + Revoke Access (logs to audit trail) |
| `pages/03_user_access_simulation.py` | Simulate granting a new access; score + approval persistence |

---

## Data Flow: Drift Scoring

```
New access event (user_id, resource_id)
        │
        ▼
DriftScorer.score()
        │
        ├── miner.user_index.index(user_id)  → user_idx
        ├── W[user_idx]                       → user_vec  (n_roles,)
        │
        ├── miner.resource_index.index(resource_id) → sys_idx
        ├── H[:, sys_idx]                     → sys_vec   (n_roles,)
        │
        ├── similarity = dot(user_vec, sys_vec) / (‖user_vec‖·‖sys_vec‖)
        ├── drift_score = 1 − similarity       [0, 1]
        │
        ├── < 0.3  → "Normal"      — fits employee's role profile
        ├── 0.3–0.7 → "Minor Drift" — partial overlap
        └── ≥ 0.7  → "High Drift"  — outside employee's role profile

        is_drift = drift_score >= 0.7
```

## Data Flow: Fleet Analytics

```
compute_fleet_analytics(miner, matrix)
        │
        ├── for each user_id in matrix.index:
        │       score every system they have access to
        │       → n_high (≥0.7), n_minor (0.3–0.7), n_normal (<0.3)
        │       → balanced_risk_score = (n_high + 0.5·n_minor) / n_total
        │
        ├── tertile split → risk_category: Low / Medium / High
        │
        └── write to Redis (24h TTL) + data/processed/fleet_analytics.parquet
```

---

## Deployment Notes

- The API is stateless; models are loaded once per process (`lru_cache`).
- `APP_ROOT` env var must be set to `/app` in Docker so path resolution
  works from the installed wheel (whose `__file__` points into site-packages).
- The dashboard talks to the API over HTTP — they can run on different hosts.
- No authentication is implemented; add OAuth2 before any production use.
- CORS is open (`allow_origins=["*"]`); restrict to the dashboard origin in production.
- The SQLite audit database (`audit/audit.db`) is created automatically at API
  startup via `create_tables()`. In Docker, this path is mounted as a named
  volume (`audit_db:/app/audit`) so data persists across container restarts.
- Nginx (port 80) is the single entry point: `/api/*` → FastAPI, `/` → Streamlit.
  Backend containers are not exposed directly; only Nginx has an external port.
