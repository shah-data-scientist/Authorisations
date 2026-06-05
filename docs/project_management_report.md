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

0. [Portfolio Overview](#0-portfolio-overview)
1. [Context and Needs Analysis](#1-context-and-needs-analysis)
2. [Audit of the Existing Data Solution](#2-audit-of-the-existing-data-solution)
3. [Identification of a Target Technical Solution](#3-identification-of-a-target-technical-solution)
4. [Strategic and Methodological Support](#4-strategic-and-methodological-support)
5. [Project Control and Monitoring](#5-project-control-and-monitoring)
6. [Conclusion and Recommendations](#6-conclusion-and-recommendations)
7. [Appendices](#7-appendices)

---

## 0. Portfolio Overview

This report covers the capstone project (Projet 13) in full. It is submitted alongside a portfolio of **nine production-grade ML projects** completed during the OpenClassrooms Data Scientist programme. The table below positions the capstone within that broader body of work and maps each project to the competency it primarily illustrates.

| # | Project | Domain | Key Achievement | Primary Competency |
|---|---|---|---|---|
| 1 | **Access Management Platform** *(Capstone)* | Cybersecurity / IAM | NMF k=15, cluster separation 0.74, full 4-service Docker stack | All 5 competencies — see Sections 1–5 |
| 2 | **SportsSee NBA Analyst AI** | Sports Analytics / Agentic AI | LangGraph 4-agent system; RAGAS faithfulness 0.900, correctness 0.875; 688 automated tests | Technical solution identification; production system design |
| 3 | **IAM Policy Generator** | Cloud Security / AI Governance | QLoRA fine-tune Llama 3.2 3B; NIST recall +53.3 pp; red-team benchmark (8% FP rate) | Strategic support; ethical AI evaluation |
| 4 | **CropWise** | AgTech / MLOps | Ridge regression R²=0.913 on 666K records; GitHub Actions CI/CD; MLflow tracking | Control & monitoring; reproducible pipelines |
| 5 | **Credit Scoring MLOps** | Financial Services / AI Governance | LightGBM ROC-AUC 0.832; ONNX 55× speedup; EU AI Act Annex III conformity assessment | Regulatory & ethical compliance; drift detection |
| 6 | **BrainScanAI** | Medical Imaging / Deep Learning | ResNet50 semi-supervised; F2 96.43% with only 100 labelled MRI scans | Data audit; handling severe label scarcity |
| 7 | **Cultural Events RAG** | LLM / RAG | Mistral embeddings + FAISS; live OpenAgenda API; RAGAS-evaluated; FR/EN auto-detection | Needs analysis; iterative evaluation |
| 8 | **Employee Attrition System** | HR Analytics | Logistic Regression + SMOTE; ROC-AUC 0.824; SHAP explanations; PostgreSQL audit trail | Explainability; stakeholder-facing deliverables |
| 9 | **FashionInsta Vision PoC** | Computer Vision / Fashion Tech | CLIP + ResNet-50 visual similarity; FAISS; Azure AI Search scalability path | Feasibility study; business scoping |

**Portfolio coherence:** Every project shares three design principles inherited from the author's professional background in IT Audit — (1) results must be explainable to a non-technical reviewer, (2) pipelines must be reproducible end-to-end, and (3) every automated decision must leave an auditable trace. The capstone project operationalises all three principles in the domain the author knows best: Identity and Access Management.

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
| `data/processed/user_permission_matrix.parquet` | Binary matrix 340 × 7,226 (granted-only users × systems) |
| `data/processed/fleet_analytics.parquet` | Pre-computed per-employee risk scores (24 h TTL) |

**Key dataset statistics**

| Metric | Value |
|---|---|
| Total events (raw) | 32,769 |
| Granted rows used (ACTION=1) | ~30,857 (~94%) |
| Refused rows excluded (ACTION=0) | ~1,912 (~6%) |
| Unique employees (ROLE_CODE, granted only) | 340 |
| Unique systems (granted only) | 7,226 |
| Matrix sparsity | ~99% |

**Data flow**

```
data/raw/train.csv
      │
      ▼  preprocess.py  (ACTION=1 only)
data/interim/cleaned.parquet
      │
      └──► user_permission_matrix.parquet   (340 × 7,226 binary)
                    │
                    ▼  analytics.py + DriftScorer
         fleet_analytics.parquet
         (per-employee risk scores, 24 h TTL)
```

---

### 2.2 Adequacy Assessment

**Criteria and findings**

| Criterion | Assessment | Gap identified |
|---|---|---|
| **Coverage** | All 340 employees and 7,226 systems captured | No temporal dimension — accesses are static snapshots |
| **Label quality** | ACTION=0 rows excluded — they are refusals, not revocations | No supervised anomaly labels available; unsupervised approach adopted |
| **Scalability** | Parquet + NMF scales well to ~10k employees | Beyond ~50k employees, incremental NMF or LSH needed |
| **Business relevance** | Role mining produces interpretable clusters; cosine score is continuous | 74% of employees have weak role membership (mixed profiles) |
| **Explainability** | Drift score accompanied by plain-language category and explanation | Score is a similarity measure, not a probability — interpretation requires context |
| **Security** | No authentication on API | Not production-ready for external exposure |

**Identified gaps**

1. **No validated anomaly labels** — `ACTION=0` rows represent provisioning refusals, not confirmed anomalies. The unsupervised NMF cosine score avoids this dependency entirely but cannot be evaluated against ground truth without expert-labelled incidents.
2. **Weak role membership** — 74% of employees have a dominant role weight below 30%, spanning multiple clusters. High Drift flags for these employees may reflect legitimate cross-functional access rather than anomalies.
3. **Static model** — The NMF is trained once; access patterns evolve. No retraining schedule or incremental update mechanism exists yet.
4. **No persistence layer (v1)** — Simulation results and access review decisions were not stored in v1; this has been resolved in the current version with a SQLite audit trail (`audit/audit.db`) covering simulation history, approval workflow, and access revocation events.

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
| **NMF cosine score (selected)** | Fully unsupervised; continuous 0–1; no labels needed; same model as role mining | Score is a similarity measure, not a probability | **Selected** |
| **Rule-based overlap** | Fully explainable, fast | Discrete (0/0.3/1.0), no gradient, threshold-sensitive | Superseded by NMF cosine |
| **XGBoost on denial labels** | Contextual features, cross-validated | `ACTION=0` rows are refusals not revocations — invalid labels | Rejected (methodological flaw) |
| **Isolation Forest** | Unsupervised, no labels needed | No role structure; harder to explain | Considered, deferred |
| **Autoencoder** | Captures complex patterns | GPU typically required, black box | Rejected (CPU constraint) |

**Rationale for the unsupervised NMF cosine approach**

The NMF decomposition already encodes the relationship between employees and systems through the W (users × roles) and H (roles × systems) matrices. The cosine similarity between a user's role vector and a system's role vector is a direct, interpretable measure of role-profile alignment. No additional training is required, and no labelled anomalies are needed. The score is continuous (not discrete) and automatically inherits any improvement in the NMF model quality.

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
                 │ │ DriftScorer   │  │  continuous 0–1
                 │ │ (NMF cosine)  │  │  1 − cos(W[u], H[:,s])
                 │ └───────────────┘  │
                 └────────────────────┘
                           │
              ┌────────────▼────────────┐
              │    Data Layer (Parquet) │
              │  user_permission_matrix  │
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
  │  SQLite  │  │  Redis  │
  │  audit/  │  │  cache  │
  │ audit.db │  │ (fleet) │
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
| Simulation persistence / audit trail | High — compliance | Medium | P2 ✅ Done |
| Real-time streaming | Medium | High | P3 |
| LDAP / Active Directory integration | High | High | P3 |

---

### Key Success Factors and Watch Points

**Success factors**
- NMF cluster quality validated through BIC minimisation and manual permission review.
- Balanced Risk Score provides a single comparable metric across all employees.
- Drift score is always accompanied by a plain-language explanation (no black box output exposed to end users).

**Watch points**
- 13.9% of an employee's own legitimate accesses score as High Drift — this reflects mixed-profile employees (74% weak role membership) and should be communicated to reviewers as "worth understanding", not "confirmed anomalous".
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
| Modelling | NMF (k=15 via BIC), NMF cosine drift scorer | `role_miner_*.joblib` |
| Evaluation | Unsupervised metrics: reconstruction MSE, self-consistency gap, cluster separation | `evaluate_model.py` |
| Deployment | FastAPI + Streamlit; `make` automation; evaluation script | Running platform at :8000 / :8501 |

**Implementation roadmap**

| Phase | Deliverable | Status |
|---|---|---|
| Phase 1 — Foundation | Data pipeline (granted-only), NMF role miner, NMF cosine drift scorer | ✅ Complete |
| Phase 2 — Detection layer | Continuous drift score, unsupervised evaluation (`evaluate_model.py`) | ✅ Complete |
| Phase 3 — Interfaces | FastAPI REST API, Streamlit 3-page dashboard | ✅ Complete |
| Phase 4 — Analytics | Fleet analytics, Balanced Risk Score, pre-computed parquet + Redis cache | ✅ Complete |
| Phase 5 — Production | Docker, SQLite audit trail, Redis, Nginx; 4-service stack | ✅ Complete |
| Phase 6 — Hardening | Authentication, retraining schedule, LDAP integration | 🔲 Deferred |

---

### 4.2 Decision-Making Support

**Risk and opportunity synthesis**

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Weak role membership (74% of employees) produces High Drift on legitimate access | Medium | Medium | Communicate to reviewers: High Drift = "worth understanding", not confirmed anomaly |
| Model staleness as access patterns evolve | Medium | High | Schedule periodic retraining; add incremental NMF option |
| No authentication — API exposed | High (if deployed) | Critical | Add OAuth2/JWT before any multi-user deployment |
| No ground-truth anomaly labels for validation | High | Medium | Partner with security team to label top-20 High Risk employees |

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
| NMF cluster separation | ≥ 0.60 (target; current: 0.740) | `python evaluate_model.py` |
| Self-consistency gap | ≥ 0.40 (target; current: 0.519) | `python evaluate_model.py` |
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
| NMF reconstruction MSE | `python evaluate_model.py` | Each model retrain |
| Cluster separation | `python evaluate_model.py` | Each model retrain |
| Self-consistency gap | `python evaluate_model.py` | Each model retrain |
| Fleet High Drift rate | `fleet_analytics.parquet` | Daily (24 h TTL) |
| Mean Balanced Risk Score | `fleet_analytics.parquet` | Daily |
| API health | `GET /health` | Continuous (health check) |
| API scoring latency | Uvicorn logs | Per-request |

**Project delivery tracking**

| Deliverable | Status | Notes |
|---|---|---|
| Data pipeline (`make data`) | ✅ Done | Reproducible; idempotent |
| Model training (`make train`) | ✅ Done | NMF only; granted-only matrix |
| Evaluation (`python evaluate_model.py`) | ✅ Done | Unsupervised metrics |
| REST API (`make api`) | ✅ Done | FastAPI, 11 endpoints |
| Dashboard (`make dashboard`) | ✅ Done | 3 pages; Plotly charts |
| Docker containerisation | ✅ Done | 4 services (Redis, API, Dashboard, Nginx); health checks |
| Simulation persistence + audit trail (SQLite) | ✅ Done | Full CRUD + approval workflow + access revocation log |

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
| NMF cosine drift score (unsupervised) | No labels required; continuous 0–1 score; grounded in the same decomposition as role mining |
| Granted-only matrix (ACTION=1) | ACTION=0 rows are refusals not revocations — including them inflated access rights and corrupted NMF |
| Balanced Risk Score via tertiles | Equal distribution (⅓ Low / ⅓ Medium / ⅓ High) allows prioritised review queues |
| FastAPI + Streamlit + Docker | Industry-standard async API; containerised 4-service production stack (Nginx, API, Dashboard, Redis) |
| SQLite for audit persistence | Zero external dependency; auto-created at startup; persisted via Docker named volume |
| Pre-computed fleet analytics (Redis + parquet, 24 h TTL) | Avoids 30 s recomputation on every dashboard load; shared across replicas |
| CPU-only ML configuration | Hardware constraint; ensures deployability on standard enterprise servers |

### Current Model Performance

| Metric | Value | Interpretation |
|---|---|---|
| NMF reconstruction MSE | 0.0033 | Excellent approximation of the user-permission matrix |
| Strong role membership (>70%) | 15.0% | 15% of employees belong cleanly to one role |
| Self-consistency gap | +0.519 | Own-system drift 0.34 vs non-access 0.86 — clear separation |
| Cluster separation | +0.740 | Same-cluster drift 0.18 vs cross-cluster 0.92 — strong discriminative power |
| High Drift on own systems | 13.9% | Reflects mixed-profile employees; expected, not a model failure |

### Recommended Next Steps

**Immediate (before operational deployment)**

1. **Add API authentication** — Implement OAuth2 bearer token or API key validation on FastAPI before exposing the service beyond localhost.

2. **Validate with a security expert** — Have a domain expert review the top-20 "High Risk" employees to confirm that High Drift flags correspond to genuinely anomalous accesses. Even 50–100 validated labels enable future supervised enrichment.

3. **CI/CD pipeline** — Add GitHub Actions to run `pytest` and `python evaluate_model.py` on every push, tracking reconstruction MSE and cluster separation across model versions.

**Short term (Phase 6 — 1–3 months)**

4. **Temporal drift** — Extend the model to detect changes in an employee's access pattern over time (not just deviation from cluster at a single point in time). Requires access log timestamps with finer granularity.

5. **LDAP / Active Directory integration** — Enrich employee attributes with organisational metadata (department, manager, seniority) to enable organisational-unit–level reporting.

6. **Incremental NMF** — Replace full retraining with an online update mechanism so the model can adapt to new access grants without reprocessing the full matrix.

### Personal Reflection: What This Portfolio Work Taught Me

Writing this report — and the nine projects behind it — forced a level of reflexivity that technical delivery alone does not require. Three things shifted in my understanding:

**1. Explainability is an audit prerequisite, not a bonus feature.**
Early in the programme I treated SHAP values and plain-language explanations as a nice-to-have layer added after the model was built. By the end, I understood that a model whose output cannot be explained to the reviewer is not operationally viable — it is a liability. This changed how I structure every project: the explanation mechanism is now designed before the model, not after. The NMF cosine drift score and its plain-language category were specified in the requirements (§1.2) before a single line of modelling code was written.

**2. The distance between a notebook and a production system is the entire problem.**
Twelve projects taught me that the hard work is not model selection — it is async APIs, cache invalidation, health checks, Docker volume mounts, reproducible `make` pipelines, and audit trails. These are not engineering cosmetics; they are what allows a system to be deployed, maintained, and trusted. My GRC background made me expect this. The programme gave me the technical vocabulary to implement it.

**3. Building the system I audit transformed how I audit.**
The methodological decision to reject XGBoost (§3) — because `ACTION=0` rows are provisioning refusals, not confirmed anomalies — is an insight that only emerged from building the system. A traditional auditor reviewing the same dataset would have accepted the label and trained the classifier. Having built the pipeline, I could see the flaw immediately. That builder's perspective is the durable outcome of this qualification.

---

### Personal Development Axes (Axes d'amélioration)

The following gaps are identified honestly, not as project limitations but as personal competency areas to develop further:

| Area | Current level | Development plan |
|---|---|---|
| **MLOps maturity** | CI/CD implemented in CropWise and Credit Scoring; absent in earlier projects | Apply GitHub Actions + evaluate_model.py regression check to every future project from day one, not as a Phase 5 add-on |
| **Domain validation of ML outputs** | All anomaly scoring is unsupervised; no security expert has validated the top-20 High Risk employees | Partner with a real SOC or IAM team to label 50–100 confirmed incidents; this is the single highest-leverage improvement for the capstone |
| **Temporal modelling** | All projects use single-snapshot data; no time-series anomaly detection has been implemented | Develop skills in sequence modelling (LSTM, temporal NMF) to extend the drift scorer from snapshot to longitudinal |
| **Stakeholder communication** | Dashboards built; no user testing with non-technical audiences | Run structured usability sessions with security reviewer personas; measure review-time reduction empirically |
| **LLM evaluation rigour** | RAGAS applied to SportsSee NBA and Cultural Events; context precision gap discovered late | Apply RAGAS evaluation from sprint 1 on every RAG project; treat retrieval quality as a first-class metric alongside generation quality |

---

### Perspectives for Evolution

The platform as built provides a solid, reproducible foundation. The core algorithm (NMF cosine drift scoring) is sound, fully unsupervised, and grounded in peer-reviewed literature (Frank & Basin, 2012). With a cluster separation of 0.74 and a self-consistency gap of 0.52, the model cleanly discriminates role-appropriate from role-inappropriate access without requiring any labelled anomalies. Given access to an enterprise's real IAM data with expert-validated incident labels, a supervised enrichment layer could be added on top of the existing cosine score — but the unsupervised foundation is operationally viable as a first-line access review tool today.

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

### Appendix B — Model Evaluation Report (generated 2026-05-22)

Run via `python evaluate_model.py` from the project root.

```
── 1. NMF Reconstruction Error ──
  MSE (X vs W·H):       0.0033
  Frobenius norm error: 90.65

── 2. Role Coverage ──
  Strong membership (>70%):    15.0% of employees
  Partial membership (30-70%): 10.6% of employees
  Weak membership (<30%):      74.4% of employees

── 3. Self-Consistency Gap ──
  (50 users × 20 systems sampled — own systems vs random non-access)
  Mean drift — own systems:        0.3390
  Mean drift — non-access systems: 0.8578
  Self-consistency gap:            0.5188  (higher = better)

── 4. Intra vs Inter-Cluster Separation ──
  (500 random (user, system) pairs)
  Mean drift — same cluster:      0.1761
  Mean drift — different cluster: 0.9157
  Cluster separation:             0.7396  (higher = better)

── 5. Score Distribution (own systems, 50 users × 20 systems) ──
  Normal      (< 0.3):   50.4%
  Minor Drift (0.3–0.7): 35.7%
  High Drift  (>= 0.7):  13.9%

── Summary ──
  Reconstruction MSE:      0.0033
  Strong role coverage:    15.0%
  Self-consistency gap:    0.5188
  Cluster separation:      0.7396
  Total own scores:        627
  Total random scores:     1000
```

### Appendix C — Key Commands

```bash
make install              # Install all dependencies (Python 3.11)
make data                 # Download and preprocess raw data (granted-only)
make train                # Train NMF role miner
python evaluate_model.py  # Run unsupervised evaluation metrics
make api                  # Start FastAPI on port 8000
make dashboard            # Start Streamlit on port 8501
make docker-restart       # Start full Docker stack (4 services: Nginx, API, Dashboard, Redis)
make test                 # Run pytest test suite
make lint                 # Black formatting + flake8 linting
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
│   └── scorer.py                — NMF cosine drift scorer (continuous 0–1)
├── db/
│   ├── models.py                — ORM models: Simulation + AuditLog (SQLite)
│   └── session.py               — Sync SQLite session factory; create_tables()
├── api/
│   ├── main.py                  — FastAPI app, lifespan, router registration
│   └── routers/
│       ├── users.py
│       ├── roles.py
│       ├── drift.py
│       ├── analytics.py
│       └── simulations.py       — Simulation CRUD + /revoke endpoint
└── dashboard/
    ├── app.py                   — Streamlit entry point
    ├── cluster_utils.py         — cached data loaders
    └── pages/
        ├── 01_access_intelligence.py
        ├── 02_user_access_review.py
        └── 03_user_access_simulation.py
```

---

*Report generated May 2026 — Access Management Platform v0.3.0 — Shahul SHAIK*
