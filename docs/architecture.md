# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Streamlit Dashboard                       │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────┐ ┌────────┐  │
│  │ User Lookup  │ │Role Explorer │ │Drift Monitor│ │What-If │  │
│  └──────┬───────┘ └──────┬───────┘ └──────┬──────┘ └───┬────┘  │
│         └────────────────┴────────────────┴────────────┘        │
│                           HTTP (requests)                        │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                    ┌───────────▼────────────┐
                    │     FastAPI (port 8000) │
                    │  /users  /roles  /drift │
                    └───────────┬────────────┘
                                │ loads once at startup
                    ┌───────────▼────────────┐
                    │   _model_loader.py      │
                    │  (lru_cache singletons) │
                    └──┬────────────────┬─────┘
                       │                │
          ┌────────────▼───┐   ┌────────▼───────────┐
          │ ProbabilisticR │   │    DriftScorer      │
          │   oleMiner     │   │  (overlap-based)    │
          │  (NMF model)   │   └────────────────────┘
          └────────────────┘
                   │
          ┌────────▼────────┐
          │ models/          │
          │ role_miner_      │
          │ 15roles.joblib   │
          └─────────────────┘

Data pipeline (offline):
  UCI API → data/raw/ → data/interim/ → data/processed/
      ↓
  NMF training → models/role_miner_*.joblib
      ↓
  XGBoost training → models/drift_classifier.joblib
```

---

## Component Descriptions

### Data Pipeline (`src/role_recommender/data/`)
| File | Responsibility |
|---|---|
| `download.py` | Fetches dataset from UCI ML Repo via `ucimlrepo` |
| `preprocess.py` | Cleans data, builds binary user × resource matrix |

### Role Mining (`src/role_recommender/mining/`)
| File | Responsibility |
|---|---|
| `probabilistic.py` | NMF-based role miner (Frank/Basin approximation) |
| `clustering.py` | k-means baseline for comparison |
| `model_selection.py` | BIC / elbow analysis for choosing k |
| `matrix.py` | Matrix load + stats helpers |

### Drift Detection (`src/role_recommender/drift/`)
| File | Responsibility |
|---|---|
| `scorer.py` | Stage 1: permission-overlap drift score (rule-based, fast) |
| `detector.py` | Stage 2: XGBoost classifier trained on revocation events |
| `explainer.py` | SHAP explanations for the classifier decisions |

### API (`src/role_recommender/api/`)
| File | Responsibility |
|---|---|
| `main.py` | FastAPI app, CORS middleware, router registration |
| `schemas.py` | Pydantic request/response models |
| `_model_loader.py` | Singleton model/matrix loading (lru_cache) |
| `routers/users.py` | `GET /users/{id}/role`, `GET /users/{id}/permissions` |
| `routers/roles.py` | `GET /roles/`, `GET /roles/{id}` |
| `routers/drift.py` | `POST /drift/score` |

### Dashboard (`src/role_recommender/dashboard/`)
| File | Responsibility |
|---|---|
| `app.py` | Entry point + landing page |
| `pages/01_user_lookup.py` | User role + permission viewer |
| `pages/02_role_explorer.py` | Role browsing with slider |
| `pages/03_drift_monitor.py` | Real-time drift scoring form |
| `pages/04_what_if.py` | Drift simulation panel |
| `components/role_card.py` | Reusable role summary card |
| `components/drift_timeline.py` | Altair drift timeline chart |

---

## Data Flow: Drift Scoring

```
New access event (user_id, resource_id)
        │
        ▼
DriftScorer.score()
        │
        ├── miner.get_user_role(user_id)        → dominant_role
        ├── miner.get_role_permissions(role, 50) → role_perm_set
        │
        ├── resource in role_perm_set?
        │       YES → drift_score = 0.0
        │       NO  → check secondary roles (weight > 5%)
        │               covered → drift_score = 0.3
        │               not covered → drift_score = 1.0
        │
        └── is_drift = drift_score >= threshold (default 0.5)
```

---

## Deployment Notes

- The API is stateless; models are loaded once per process (`lru_cache`).
- The dashboard talks to the API over HTTP — they can run on different hosts.
- No authentication is implemented; add OAuth2 before any production use.
- CORS is open (`allow_origins=["*"]`); restrict to the dashboard origin in production.
