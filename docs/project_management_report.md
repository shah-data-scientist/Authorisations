# Project Management Report
## Projet 13 — Access Management Platform
### ML-Based Access Anomaly Detection

---

**Author:** Shahul SHAIK
**Date:** May 2026
**Programme:** OpenClassrooms — Data Scientist
**Repository:** `role-recommender` / Access Management Platform

---

## Table of Contents

1. [Context and Needs Analysis](#1-context-and-needs-analysis)
2. [Audit of the Existing Data Solution](#2-audit-of-the-existing-data-solution)
3. [Identification of a Target Technical Solution](#3-identification-of-a-target-technical-solution)
4. [Strategic and Methodological Support](#4-strategic-and-methodological-support)
5. [Project Control and Monitoring](#5-project-control-and-monitoring)
6. [Conclusion and Recommendations](#6-conclusion-and-recommendations)
7. [Appendices](#7-appendices)

---

## 1. Context and Needs Analysis

### 1.1 Presentation

**Sector and context**

Identity and Access Management (IAM) is a critical discipline in enterprise cybersecurity. Organisations of all sizes must control which employees can access which systems — and detect when those accesses become inappropriate over time. Regulatory frameworks (GDPR, SOX, ISO 27001) increasingly require documented, auditable access reviews.

Commercial IAM platforms (SailPoint, Saviynt, CyberArk) offer sophisticated Role-Based and Attribute-Based Access Control (RBAC/ABAC), but carry prohibitive licensing costs and require deep organisational configuration. This project was initiated to demonstrate that an open-source, data-driven alternative is achievable — one that derives access roles directly from observed behaviour rather than from declared organisational charts.

**Strategic data challenges**

| Challenge | Description |
|---|---|
| Privilege creep | Access rights accumulate over time as employees change roles, join projects, or inherit permissions from predecessors. |
| Orphan accounts | Accesses persist after role changes or departures, creating dormant attack vectors. |
| Audit burden | Manual quarterly access reviews are slow, inconsistent, and difficult to scale beyond a few hundred employees. |
| Explainability gap | Security teams need not just a flag but an explanation of *why* an access is anomalous. |

**Data maturity**

The project operates on the Amazon Access Samples dataset (UCI ML Repository, id=216) — real IAM data from Amazon's internal systems (2010–2011), fully anonymised. This represents a medium-maturity data context: structured, labelled at the event level (granted/denied), but with no textual identifiers and no ground-truth anomaly labels.

---

### 1.2 Business Needs Collection and Analysis

**Stakeholders**

| Stakeholder | Role | Primary concern |
|---|---|---|
| Security team | Access risk owners | Detect anomalous access before incidents occur |
| HR / People Ops | Offboarding and role changes | Ensure accesses are removed when roles change |
| IT Operations | System administrators | Know which systems are accessed by which clusters |
| Auditors | Compliance reviewers | Documented, reproducible access risk scores |
| Managers | Access approvers | Quick view of their team's risk exposure |

**Needs hierarchy (MoSCoW)**

| Priority | Need |
|---|---|
| **Must have** | Automatic inference of implicit access roles from historical data |
| **Must have** | Per-access drift score with a plain-language explanation |
| **Must have** | Fleet-wide risk ranking so reviewers know where to start |
| **Should have** | Interactive dashboard accessible to non-technical stakeholders |
| **Should have** | REST API exposing scores for integration with existing tooling |
| **Could have** | Simulation of hypothetical access requests before granting |
| **Could have** | Approval workflow for flagged accesses |
| **Won't have (v1)** | Real-time streaming ingestion; LDAP integration; authentication |

**Business constraints**

- **Regulatory:** Access review findings must be explainable and auditable — black-box scores alone are insufficient.
- **Operational:** The system must run on CPU-only infrastructure (no GPU dependency) to remain deployable on standard enterprise hardware.
- **Reusability:** The pipeline must be reproducible end-to-end (`make data && make train && make evaluate`) so results can be regenerated as new access data arrives.
- **Privacy:** All processing is local; no employee data leaves the organisation's environment.

---

## 2. Audit of the Existing Data Solution

### 2.1 Current or Proposed Solution

**Baseline: no automated detection**

Prior to this project, access review was a manual process: security teams periodically exported access lists and reviewed them by eye, typically quarterly. No algorithmic scoring existed. The dataset (Amazon Access Samples) is the closest proxy for a real enterprise access log.

**Dataset and pipeline**

| Artifact | Description |
|---|---|
| `data/raw/train.csv` | 32,769 access events; fields: ACTION, RESOURCE, ROLE_CODE, department codes, manager ID |
| `data/interim/cleaned.parquet` | Deduplicated, null-filtered events |
| `data/processed/user_permission_matrix.parquet` | Binary matrix 343 × 7,518 (users × systems) |
| `data/processed/access_events.parquet` | Row-level events for XGBoost training |
| `data/processed/fleet_analytics.parquet` | Pre-computed per-employee risk scores (24 h TTL) |

**Key dataset statistics**

| Metric | Value |
|---|---|
| Total events | 32,769 |
| Unique employees (ROLE_CODE) | 343 |
| Unique systems (RESOURCE) | 7,518 |
| Grant rate (ACTION=1) | ~94.2% |
| Denial rate (ACTION=0) | ~5.8% |
| Matrix sparsity | ~99% |

**Data flow**

```
data/raw/train.csv
      │
      ▼  preprocess.py
data/interim/cleaned.parquet
      │
      ├──► user_permission_matrix.parquet   (343 × 7,518 binary)
      └──► access_events.parquet            (events for XGBoost)
                                                    │
                                                    ▼  analytics.py
                                         fleet_analytics.parquet
                                         (per-employee risk scores)
```

---

### 2.2 Adequacy Assessment

**Criteria and findings**

| Criterion | Assessment | Gap identified |
|---|---|---|
| **Coverage** | All 343 employees and 7,518 systems captured | No temporal dimension — accesses are static snapshots |
| **Label quality** | ACTION=0 is a denial, not a confirmed anomaly | Proxy labels cap classifier performance |
| **Scalability** | Parquet + NMF scales well to ~10k employees | Beyond ~50k employees, incremental NMF or LSH needed |
| **Business relevance** | Role mining produces interpretable clusters | Top-50 threshold per cluster too restrictive at 7,518 resources |
| **Explainability** | Rule-based scorer gives textual reasons | XGBoost decisions not yet surfaced via SHAP in dashboard |
| **Security** | No authentication on API | Not production-ready for external exposure |

**Identified gaps**

1. **Label quality ceiling** — With no validated anomaly labels, the supervised model (XGBoost) is bounded by the quality of ACCESS DENIALS as a proxy. ROC-AUC of 0.694 reflects this ceiling.
2. **Threshold calibration** — The top-50 overlap rule generates 76.8% High Drift across the fleet, indicating the threshold is too conservative for a 7,518-resource space (covers only 0.7% of resources per cluster). Recalibration to top-200 or a percentile threshold on the H matrix is needed.
3. **Static model** — The NMF is trained once; access patterns evolve. No retraining schedule or incremental update mechanism exists yet.
4. **No persistence layer** — Simulation results and access review decisions are not stored, making audit trails impossible.

---

## 3. Identification of a Target Technical Solution

### Comparison of Technical Approaches

**Role mining alternatives**

| Approach | Advantages | Disadvantages | Decision |
|---|---|---|---|
| **K-Means** | Simple, fast | Hard assignment (one cluster per user), no multi-role support | Rejected |
| **NMF (selected)** | Soft membership weights, interpretable H matrix, MAP approximation of Frank & Basin probabilistic model | Requires k selection, sensitive to initialisation | **Selected** |
| **Hierarchical clustering** | Dendrogram for k exploration | Quadratic memory, no soft assignment | Rejected |
| **LDA (topic models)** | Natural for sparse binary data | Less standard in IAM literature | Considered, deferred |

**Anomaly detection alternatives**

| Approach | Advantages | Disadvantages | Decision |
|---|---|---|---|
| **Rule-based only** | Fully explainable, zero training data | No contextual adaptation | Stage 1 (retained) |
| **XGBoost on denial labels** | Contextual features, cross-validated | Proxy labels, low precision | Stage 2 (retained with caveat) |
| **Isolation Forest** | Unsupervised, no labels needed | No explanation, harder to tune | Deferred |
| **Autoencoder** | Captures complex patterns | GPU typically required, black box | Rejected (CPU constraint) |

**Rationale for the hybrid approach**

A rule-based score alone cannot leverage contextual user attributes (how many systems they access, how strongly they belong to their cluster). A classifier alone cannot provide the immediate, human-readable explanation required by auditors. The two-stage hybrid — overlap rule first, XGBoost enrichment second — satisfies both explainability and contextual sensitivity.

---

### Target Architecture

```
                   Access Management Platform
                   ─────────────────────────
  ┌─────────────────────────────────────────────────────┐
  │              Streamlit Dashboard  :8501              │
  │  ┌──────────────┐ ┌─────────────────┐ ┌──────────┐  │
  │  │   Access     │ │  User Access    │ │  User    │  │
  │  │Intelligence  │ │    Review       │ │ Access   │  │
  │  │(fleet +      │ │ (risk table +   │ │Simulation│  │
  │  │system risk)  │ │  drilldown)     │ │          │  │
  │  └──────────────┘ └─────────────────┘ └──────────┘  │
  └────────────────────────┬────────────────────────────┘
                           │  reads direct from disk
                 ┌─────────▼──────────┐
                 │     FastAPI  :8000  │
                 │  /users  /roles     │
                 │  /drift  /analytics │
                 └─────────┬──────────┘
                           │  lru_cache (single load)
                 ┌─────────▼──────────┐
                 │   Model Layer       │
                 │ ┌───────────────┐  │
                 │ │ NMF Miner     │  │  W: users × 15 roles
                 │ │ (15 clusters) │  │  H: 15 roles × 7,518 systems
                 │ └───────────────┘  │
                 │ ┌───────────────┐  │
                 │ │ DriftScorer   │  │  0.0 / 0.3 / 1.0
                 │ │ (overlap rule)│  │
                 │ └───────────────┘  │
                 │ ┌───────────────┐  │
                 │ │ XGBoost       │  │  context-aware
                 │ │ Classifier    │  │  drift prediction
                 │ └───────────────┘  │
                 └────────────────────┘
                           │
              ┌────────────▼────────────┐
              │    Data Layer (Parquet) │
              │  user_permission_matrix  │
              │  access_events           │
              │  fleet_analytics (24h)  │
              └─────────────────────────┘
```

**Target production architecture (planned — not yet implemented)**

```
Internet / Corporate network
           │
    ┌──────▼──────┐
    │   Nginx     │  :80/:443  TLS, rate limiting
    └──┬───────┬──┘
       │       │
  /api/*       /
  ┌────▼───┐  ┌▼──────────┐
  │FastAPI  │  │ Streamlit │
  │gunicorn │  │ dashboard │
  └────┬────┘  └─────┬─────┘
       │             │
  ┌────▼─────┐  ┌────▼────┐
  │PostgreSQL│  │  Redis  │
  │  audit   │  │  cache  │
  │   log    │  │ (fleet) │
  └──────────┘  └─────────┘
```

---

### Use Case Prioritisation

| Use Case | Business Value | Technical Complexity | Priority |
|---|---|---|---|
| Fleet risk ranking | High — directs reviewer effort | Low | P1 |
| Per-employee access drilldown | High — replaces manual review | Medium | P1 |
| Drift score with explanation | High — audit requirement | Medium | P1 |
| Access simulation | Medium — pre-approval screening | Medium | P2 |
| Simulation persistence / audit trail | High — compliance | Medium | P2 (planned) |
| Real-time streaming | Medium | High | P3 |
| LDAP / Active Directory integration | High | High | P3 |

---

### Key Success Factors and Watch Points

**Success factors**
- NMF cluster quality validated through BIC minimisation and manual permission review.
- Balanced Risk Score provides a single comparable metric across all employees.
- Drift score is always accompanied by a plain-language explanation (no black box output exposed to end users).

**Watch points**
- The top-50 threshold must be recalibrated before operational deployment; the current 76.8% High Drift rate is too noisy for effective triage.
- XGBoost labels (ACCESS DENIALS) are proxies — operational decisions should weight the rule-based score more heavily until validated anomaly labels are available.
- The system currently has no authentication layer; adding OAuth2/JWT is mandatory before any multi-user or internet-facing deployment.

---

## 4. Strategic and Methodological Support

### 4.1 Project Approach Proposal

**Methodology: adapted CRISP-DM**

The project follows the Cross-Industry Standard Process for Data Mining (CRISP-DM), with iterations:

```
Business Understanding → Data Understanding → Data Preparation
         ↑                                          │
         │                                          ▼
   Deployment ←── Evaluation ←────── Modelling
```

| CRISP-DM Phase | Activities performed | Output |
|---|---|---|
| Business Understanding | Stakeholder mapping, needs prioritisation, constraint identification | This report — Section 1 |
| Data Understanding | EDA on Amazon Access Samples; sparsity analysis; denial rate analysis | `preprocess.py`, cleaned parquet |
| Data Preparation | Binary matrix construction, event log extraction, fleet analytics pre-computation | `user_permission_matrix.parquet`, `fleet_analytics.parquet` |
| Modelling | NMF (k=15 via BIC), rule-based scorer, XGBoost classifier | `role_miner_*.joblib`, `drift_classifier_*.joblib` |
| Evaluation | 5-fold CV on XGBoost; NMF reconstruction + coverage; fleet distribution | `models/evaluation_report.txt` |
| Deployment | FastAPI + Streamlit; `make` automation; evaluation script | Running platform at :8000 / :8501 |

**Implementation roadmap**

| Phase | Deliverable | Status |
|---|---|---|
| Phase 1 — Foundation | Data pipeline, NMF role miner, drift scorer | ✅ Complete |
| Phase 2 — Detection layer | XGBoost classifier, evaluation script | ✅ Complete |
| Phase 3 — Interfaces | FastAPI REST API, Streamlit 3-page dashboard | ✅ Complete |
| Phase 4 — Analytics | Fleet analytics, Balanced Risk Score, pre-computed parquet | ✅ Complete |
| Phase 5 — Production | Docker, PostgreSQL, Redis, Nginx, Alembic migrations | 🔲 Planned |
| Phase 6 — Hardening | Authentication, retraining schedule, SHAP explainability, LDAP | 🔲 Deferred |

---

### 4.2 Decision-Making Support

**Risk and opportunity synthesis**

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Label quality limits classifier performance | High | Medium | Document clearly; use rule-based score as primary signal |
| Top-50 threshold produces too many false High Drift flags | High | High | Recalibrate to top-200 or percentile threshold on H matrix |
| Model staleness as access patterns evolve | Medium | High | Schedule periodic retraining; add incremental NMF option |
| No authentication — API exposed | High (if deployed) | Critical | Add OAuth2/JWT before any multi-user deployment |
| Regulatory challenge to proxy labels | Medium | Medium | Validate top-20 High Risk employees with security experts |

| Opportunity | Impact |
|---|---|
| Replacing manual quarterly reviews | Reduced review time from weeks to hours; consistent scoring |
| Simulation before access grant | Proactive risk reduction rather than reactive detection |
| Extensible to any tabular IAM dataset | Platform reusable across organisations without retraining methodology |

**Budget scenarios (indicative)**

| Scenario | Infrastructure | Effort | Annual Cost Estimate |
|---|---|---|---|
| **On-premise (current)** | Single server, 8 CPU cores, 32 GB RAM | 1 data engineer (maintenance) | ~€20k/yr (personnel) |
| **Cloud (AWS/Azure)** | 2× c5.xlarge + RDS PostgreSQL + ElastiCache | 0.5 FTE DevOps | ~€8k/yr (infra) + personnel |
| **SaaS IAM alternative** | SailPoint / Saviynt | Vendor support | €50k–€200k/yr (licensing) |

The open-source approach delivers a 60–90% cost reduction versus commercial IAM platforms, with the trade-off of requiring internal data engineering capacity.

**Success indicators (KPIs)**

| KPI | Target | Measurement |
|---|---|---|
| Fleet coverage | 100% employees scored | `fleet_analytics.parquet` row count |
| Review time reduction | ≥ 50% vs manual | Stakeholder feedback post-deployment |
| High Risk employees per quarter | Actionable list for security team | Top tertile — ~114 employees |
| Classifier ROC-AUC | ≥ 0.75 with validated labels | `make evaluate` output |
| NMF coverage rate | ≥ 50% with recalibrated threshold | Evaluation report metric |
| API response time (scoring) | < 100 ms per (employee, system) pair | `GET /drift/score` latency |
| Dashboard load time | < 5 s after initial cache warm | Browser / Streamlit timing |

**Ethical and regulatory considerations**

- **Fairness:** Cluster assignments must not correlate with protected attributes (gender, age, nationality). Since all fields are anonymised integers in this dataset, this risk is contained — but must be audited on real organisational data.
- **Transparency:** Every drift flag exposes its explanation to the reviewer; no silent denials. This is a deliberate design choice compliant with GDPR Article 22 (automated decision-making transparency).
- **Data minimisation:** Only access event logs are processed; no biometric, location, or communication data is ingested.
- **Right to contest:** The simulation page allows security teams to test access before granting, giving the employee's manager visibility before a decision is made.

---

## 5. Project Control and Monitoring

### 5.1 Monitoring Dashboard

**Technical KPI tracking**

| Indicator | Source | Frequency |
|---|---|---|
| NMF reconstruction error | `make evaluate` | Each model retrain |
| NMF mean coverage rate | `make evaluate` | Each model retrain |
| XGBoost ROC-AUC ± std | `make evaluate` (5-fold CV) | Each model retrain |
| Fleet High Drift rate | `fleet_analytics.parquet` | Daily (24 h TTL) |
| Mean Balanced Risk Score | `fleet_analytics.parquet` | Daily |
| API health | `GET /health` | Continuous (health check) |
| API scoring latency | Uvicorn logs | Per-request |

**Project delivery tracking**

| Deliverable | Status | Notes |
|---|---|---|
| Data pipeline (`make data`) | ✅ Done | Reproducible; idempotent |
| Model training (`make train`) | ✅ Done | NMF + XGBoost |
| Evaluation report (`make evaluate`) | ✅ Done | Auto-saved to `models/` |
| REST API (`make api`) | ✅ Done | FastAPI, 7 endpoints |
| Dashboard (`make dashboard`) | ✅ Done | 3 pages; Plotly charts |
| Docker containerisation | 🔲 Planned | Full plan drafted |
| Simulation persistence (PostgreSQL) | 🔲 Planned | Schema designed |

**Reporting mode**

Evaluation reports are generated on demand via `make evaluate` and saved to `models/evaluation_report.txt`. The dashboard displays live fleet analytics. No automated alerting is configured in v1; alerting on threshold breaches (e.g., mean BRS > 0.7) is a planned Phase 5 feature.

---

### 5.2 Tools and Monitoring Processes

**ML experiment tracking**

| Tool | Purpose |
|---|---|
| `make evaluate` | Standardised evaluation script; reproducible metrics |
| `loguru` | Structured logs with levels DEBUG / INFO / SUCCESS; written to `logs/` |
| `models/evaluation_report.txt` | Timestamped snapshot of every model evaluation run |
| BIC curve | k selection documented; re-runnable with `mining/probabilistic.py` |

**Project management and collaboration**

| Tool | Use |
|---|---|
| Git (local, main branch) | Version control; all code changes tracked |
| `Makefile` | Single entry point for all pipeline stages; eliminates environment-specific instructions |
| `pyproject.toml` | Dependency pinning; reproducible environments |
| `docs/` | Project reports and architecture notes |

**Test coverage**

```
tests/
├── test_miner.py       — NMF fit, save/load, user role queries
├── test_scorer.py      — Drift score values for known inputs
├── test_api.py         — FastAPI endpoint integration tests
└── test_analytics.py  — Fleet analytics computation
```

Run with `make test` (pytest). CI pipeline not yet configured (planned for Phase 5 alongside Docker).

---

## 6. Conclusion and Recommendations

### Summary of Decisions Made

| Decision | Rationale |
|---|---|
| NMF over K-Means for role mining | Soft membership weights; handles multi-role employees; interpretable H matrix |
| k = 15 clusters | Minimum BIC; confirmed by manual permission review |
| Hybrid scorer (rules + XGBoost) | Rules deliver explainability; XGBoost delivers contextual sensitivity |
| Top-50 overlap rule | Conservative threshold; must be recalibrated before deployment |
| Balanced Risk Score via tertiles | Equal distribution (⅓ Low / ⅓ Medium / ⅓ High) allows prioritised review queues |
| FastAPI + Streamlit stack | Industry-standard async API; rapid dashboard development |
| Pre-computed fleet analytics (parquet, 24 h TTL) | Avoids 30 s recomputation on every dashboard load |
| CPU-only ML configuration | Hardware constraint; ensures deployability on standard enterprise servers |

### Current Model Performance

| Metric | Value | Interpretation |
|---|---|---|
| XGBoost ROC-AUC | 0.694 ± 0.010 | Reasonable given proxy labels; improves with validated anomaly labels |
| NMF coverage rate (top-50) | 35.1% | Low due to conservative threshold; expected to reach >60% at top-200 |
| Fleet High Drift rate | 76.8% | Too noisy for operational use; threshold recalibration is the critical next action |
| Mean Balanced Risk Score | 0.5965 | Reflects the high drift rate; will normalise after recalibration |

### Recommended Next Steps

**Immediate (before operational deployment)**

1. **Recalibrate the drift threshold** — Change the overlap rule from top-50 to top-200 (or a percentile threshold on the H matrix, e.g., the 95th percentile of each role's resource weights). This single change is expected to reduce the High Drift rate from 76.8% to a manageable 15–25%.

2. **Add API authentication** — Implement OAuth2 bearer token or API key validation on FastAPI before exposing the service beyond localhost.

3. **Validate with a security expert** — Have a domain expert review the top-20 "High Risk" employees to confirm that High Drift flags correspond to genuinely anomalous accesses. This provides ground-truth labels for future classifier retraining.

**Short term (Phase 5 — 1–3 months)**

4. **Docker containerisation** — Deploy the full stack (FastAPI + Streamlit + PostgreSQL + Redis + Nginx) using the architecture plan already drafted. Enables multi-user access, audit trails, and cloud deployment.

5. **Simulation persistence** — Store simulation requests and reviewer decisions in PostgreSQL, enabling a full approval workflow and compliance-ready audit log.

6. **CI/CD pipeline** — Add GitHub Actions (or equivalent) to run `pytest` and `make evaluate` on every push, preventing model quality regressions.

**Medium term (Phase 6 — 3–6 months)**

7. **SHAP explainability** — Integrate SHAP values into the dashboard so each XGBoost flag includes a feature-level explanation alongside the rule-based reason.

8. **Temporal drift** — Extend the model to detect changes in an employee's access pattern over time (not just deviation from cluster at a single point in time).

9. **LDAP / Active Directory integration** — Enrich employee attributes with organisational metadata (department, manager, seniority) to improve classifier features and enable organisational-unit–level reporting.

### Perspectives for Evolution

The platform as built provides a solid, reproducible foundation. The core algorithm (NMF + hybrid scorer) is sound and grounded in peer-reviewed literature (Frank & Basin, 2012). The principal constraint at this stage is threshold calibration and label quality, not algorithmic weakness. Given access to an enterprise's real IAM data with expert-validated anomaly labels, this architecture is expected to achieve ROC-AUC ≥ 0.80 and a High Drift rate below 20% — making it operationally viable as a first-line access review tool.

---

## 7. Appendices

### Appendix A — Technical References

1. Frank, M., Buhmann, J., & Basin, D. (2012). *Role Mining with Probabilistic Models*. arXiv:1212.4775.
2. Cotrini, C. et al. (2019). *The Next 700 Policy Miners: A Universal Method for Building ABAC Miners* (UNICORN). arXiv:1908.05994.
3. Stoller, S. et al. (2019). *A Decision Tree Learning Approach for Mining Relationship-Based Access Control Policies*. arXiv:1909.12095.
4. UCI Machine Learning Repository — Amazon Access Samples (id=216).
5. Lee, D. D., & Seung, H. S. (1999). *Learning the parts of objects by non-negative matrix factorization*. Nature, 401, 788–791.
6. Chen, T., & Guestrin, C. (2016). *XGBoost: A Scalable Tree Boosting System*. KDD 2016.
7. Lundberg, S. M., & Lee, S. I. (2017). *A Unified Approach to Interpreting Model Predictions* (SHAP). NeurIPS 2017.

### Appendix B — Model Evaluation Report (generated 2026-05-17)

```
══════════════════════════════════════════════════════════════
     ACCESS MANAGEMENT PLATFORM — MODEL EVALUATION REPORT
                Generated: 2026-05-17  16:07:14
══════════════════════════════════════════════════════════════

1 · NMF ROLE MINING
──────────────────────────────────────────────────────────────
  Clusters (k):                    15
  Reconstruction error (Frobenius): 92.8693
  Relative reconstruction error:    67.3%

  Mean access coverage rate:        35.1%
  Users fully covered (100%):       8.7%

  Mean cluster-weight entropy:      1.114
  Max possible entropy (ln 15):     2.708

2 · XGBOOST DRIFT CLASSIFIER  (5-fold CV)
──────────────────────────────────────────────────────────────
  ⚠  Labels are ACCESS DENIALS (ACTION=0), not confirmed anomalies.

  Training events:                  32,769
  Anomalous label rate:             5.8%

  ROC-AUC:    0.694  ± 0.010
  Precision:  0.098
  Recall:     0.664
  F1 Score:   0.171

  Feature importances:
    role_weight_dominant         0.248
    user_permission_count        0.227
    dominant_role                0.199
    resource_frequency           0.190
    drift_score                  0.135

3 · RULE-BASED DRIFT SCORER — FLEET DISTRIBUTION
──────────────────────────────────────────────────────────────
  Employees:               343
  Total system accesses:   19,043

  Normal   (0.0):   3,358  (17.6%)
  Minor    (0.3):   1,067   (5.6%)
  High     (1.0):  14,618  (76.8%)

  Mean anomaly rate / employee:  64.9%
  Mean Balanced Risk Score:      0.5965

  Risk category distribution (tertile-based):
    Low        114 employees  (33.2%)
    Medium     115 employees  (33.5%)
    High       114 employees  (33.2%)
══════════════════════════════════════════════════════════════
```

### Appendix C — Key Commands

```bash
make install     # Install all dependencies (Python 3.11)
make data        # Download and preprocess raw data
make train       # Train NMF miner and XGBoost classifier
make evaluate    # Generate model evaluation report
make api         # Start FastAPI on port 8000
make dashboard   # Start Streamlit on port 8501
make test        # Run pytest test suite
make lint        # Black formatting + flake8 linting
```

### Appendix D — Repository Structure

```
src/role_recommender/
├── config.py                    — paths, constants, random seed
├── analytics.py                 — fleet analytics computation (pure Python)
├── evaluation.py                — model evaluation report generator
├── mining/
│   └── probabilistic.py         — ProbabilisticRoleMiner (NMF)
├── drift/
│   ├── scorer.py                — rule-based drift scorer (0.0/0.3/1.0)
│   └── detector.py              — XGBoost drift classifier
├── api/
│   ├── main.py                  — FastAPI app, lifespan, router registration
│   └── routers/
│       ├── users.py
│       ├── roles.py
│       ├── drift.py
│       └── analytics.py
└── dashboard/
    ├── app.py                   — Streamlit entry point
    ├── cluster_utils.py         — cached data loaders
    └── pages/
        ├── 01_access_intelligence.py
        ├── 02_user_access_review.py
        └── 03_user_access_simulation.py
```

---

*Report generated May 2026 — Access Management Platform v0.2.0 — Shahul SHAIK*
