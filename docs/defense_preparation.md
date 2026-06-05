# Defense Preparation — Projet 13
## OpenClassrooms · Data Scientist ML · Shahul SHAIK

**Format:** 30 minutes total — Presentation (15 min) · Discussion (10 min) · Debrief (5 min)  
**Evaluator role:** Charlotte, your manager  
**Hard limits:** Under 10 min or over 20 min → may be rejected

---

## SLIDE STRUCTURE (15 minutes)

### Slide 1 — Who I Am (1 min)
**Talking points:**
- "I am Shahul SHAIK. 15 years across IT Audit, SAP GRC, and ERP controls — CISA-certified, pursuing the AAIA™ Advanced in AI Audit credential."
- "This portfolio represents a deliberate extension of that career: I wanted to understand AI systems deeply enough to audit them, govern them, and design controls around them."
- "So rather than pivoting away from audit, I was building deeper technical credibility for it."

**Visual:** Name · CISA · AAIA™ in progress · RNCP Level 7

---

### Slide 2 — My Portfolio: 3 Layers (1.5 min)
**Talking points:**
- "My portfolio has three layers. The foundation is 15 years of professional experience in audit and GRC."
- "On top of that: a Master-level qualification in AI/ML with 12 production projects — not notebooks, but deployed systems with APIs, tests, and audit trails."
- "The bridge between the two: my capstone project, the Access Management Platform — which applies data science to exactly the access review workflows I audited at Alstom."

**Visual:** Three concentric rings — Career · AI/ML Projects · Capstone Bridge

---

### Slide 3 — Competency Map (2 min)
**Talking points:**
- "The programme evaluated five core competencies. Let me show you where each one lives in my work."
- Walk through table below.

| Competency | Where demonstrated |
|---|---|
| 1. Collect business requirements | Capstone PM report §1 — IAM stakeholder mapping, MoSCoW analysis |
| 2. Audit existing data solution | Capstone PM report §2 — gap analysis of manual access review process |
| 3. Identify technical solution | Capstone PM report §3 — NMF vs K-Means vs LDA comparison table |
| 4. Strategic & methodological support | Capstone PM report §4 — CRISP-DM roadmap, risk/opportunity synthesis |
| 5. Control & monitor the project | Capstone PM report §5 — KPI dashboard, delivery phase tracking |

---

### Slide 4 — The Capstone: Why This Project (2 min)
**Talking points:**
- "At Alstom, I spent 4 years auditing access control — manually reviewing spreadsheets of SAP permissions, trying to spot privilege creep. I knew what the problem cost in audit hours and compliance risk."
- "My capstone asks: can data science automate what I was doing by hand?"
- "The answer is yes — with important caveats that are themselves the interesting audit findings."

**Visual:** Before (manual audit) vs After (automated scoring dashboard)

---

### Slide 5 — Technical Approach (2.5 min)
**Talking points:**
- "The dataset is Amazon's internal IAM data — 32,769 access events, 340 employees, 7,226 systems."
- "Step 1: Role Mining. I used Non-negative Matrix Factorization to infer 15 implicit organisational roles from the access patterns — without any org chart. This is a standard approach in the IAM research literature (Frank & Basin, 2012). NMF gives soft membership — an employee can belong to multiple roles, which reflects reality."
- "Step 2: Drift Scoring. For each (employee, system) pair, I compute a continuous drift score: 1 minus the cosine similarity between the employee's role membership vector and the system's role profile. No training labels needed — the NMF decomposition itself is the anomaly detector."
- "Step 3: Dashboard and API. Security teams can see fleet-level risk rankings, drill into individual employees, and simulate access requests before granting them."

**Visual:** Architecture diagram from README + key metrics

---

### Slide 6 — Results and Honest Limitations (2 min)
**Talking points:**
- "The model is fully unsupervised — it requires no labelled anomalies. I evaluated it with four domain-appropriate metrics."
- "Cluster separation: 0.74. Same-cluster access requests score 0.18 on average; cross-cluster requests score 0.92. The model cleanly discriminates role-appropriate from role-inappropriate access."
- "Self-consistency gap: 0.52. Systems an employee already has access to score 0.34 on average; systems they have never accessed score 0.86. That's the signal we need."
- "The honest limitation: 13.9% of an employee's own legitimate accesses are flagged as High Drift. This reflects the 74% of employees with weak role membership — mixed profiles that genuinely span multiple clusters. A reviewer should interpret those flags as 'worth understanding', not 'definitely wrong'."
- "I am transparent about this because that transparency is itself an audit quality. A model that cannot explain its own limitations is not production-ready."

**Visual:** Unsupervised evaluation results table

---

### Slide 7 — Project Management Highlights (1.5 min)
**Talking points:**
- "I followed CRISP-DM with six delivery phases. Phases 1–5 are complete: data pipeline, role miner, drift scorer, the API + dashboard, and the full Docker stack with SQLite audit trail and Redis."
- "The full production architecture — Nginx reverse proxy, FastAPI with gunicorn workers, Streamlit dashboard, SQLite audit trail, Redis fleet cache — is containerised and runs with a single `make docker-restart`."
- "The audit trail logs every simulation and access revocation event, with a full approval workflow (pending / approved / denied). This is accessible through the User Access Review page."
- "Phase 6 (authentication, LDAP integration, retraining schedule) is correctly deferred — those are hardening concerns once the core system is validated."
- "All decisions are documented with rationale in the PM report — including risks, budget scenarios, and ethical considerations (GDPR Article 22 compliance)."

**Visual:** Phase tracker — green/orange/grey

---

### Slide 8 — What This Work Taught Me (1.5 min)
**Talking points:**
- "Three things I would not have said before this programme:"
- "First: method selection is an ethical decision, not just a technical one. I initially built an XGBoost classifier — then realised the labels (access denials) were provisioning refusals, not confirmed anomalies. Using them as anomaly labels would have been a methodological error that a reviewer might never catch. Removing the classifier and going fully unsupervised was the right audit call."
- "Second: the gap between a notebook and a production system is larger than I expected. Async APIs, cache invalidation, health checks, reproducible pipelines — these are not cosmetic. They determine whether a system can actually be deployed and maintained."
- "Third: building the system I used to audit made me a better auditor. I now understand exactly where an ML-based IAM system can fail — and I know how to design controls around those failure modes."

---

### Slide 9 — Professional Objectives (30 sec)
**Talking points:**
- "My target: Senior AI Governance, AI Audit, or IT Audit roles with significant AI dimension — primarily in Switzerland."
- "The combination of CISA, AAIA™, and this technical qualification is designed for one specific thing: being the person who can both evaluate an organisation's AI risk governance framework AND understand technically whether the controls are effective."
- "Available July 2026."

---

## CHARLOTTE DISCUSSION PREP (10 min)

### Expected questions and model answers

**Q: Why NMF rather than a simpler clustering approach?**
A: "Two reasons. First, employees in real organisations belong to multiple functional roles — an engineer who also sits on a finance committee has access that spans two clusters. K-Means forces a hard assignment; NMF gives soft membership weights that reflect that reality. Second, NMF has a rigorous theoretical grounding — it's a MAP approximation of the probabilistic role mining model from Frank & Basin (2012), which means I can defend the choice to an auditor or regulator."

**Q: You have no labelled anomalies. How do you know the model is working?**
A: "I evaluated it with four unsupervised metrics that are appropriate for this context. The key one is cluster separation: access requests that involve a system from the same role cluster as the employee score 0.18 on average; cross-cluster requests score 0.92. That's a gap of 0.74 — the model cleanly discriminates role-appropriate from role-inappropriate access without ever seeing a labelled anomaly. The self-consistency gap (own systems score 0.34, non-access systems 0.86) confirms the same story from a different angle."

**Q: 13.9% of legitimate accesses are flagged as High Drift. Isn't that too many false positives?**
A: "It's a meaningful number, not an alarming one. It directly reflects the 74% of employees who have weak role membership — they genuinely span multiple clusters. When an employee with a mixed profile accesses a system from their secondary cluster, the model correctly scores it as partial drift. Those flags should be interpreted as 'worth a second look', not 'definitely wrong'. In a quarterly access review cycle, an analyst reviewing 14% of accesses for 114 High-risk employees is a manageable workload — far better than reviewing everything manually."

**Q: You removed the XGBoost classifier. Wasn't that a step backward?**
A: "No — it was a methodological correction. The classifier was trained on `ACTION=0` rows as anomaly labels. But in the Amazon dataset, `ACTION=0` means a provisioning request was *refused at submission time* — it's not an access that was granted and later revoked. Using refusals as anomaly labels is like training a fraud model on declined credit card applications rather than confirmed fraudulent transactions. The NMF cosine score is cleaner: it's trained only on granted accesses and scores any new access against that learned structure."

**Q: How does this compare to what SailPoint or Saviynt actually does?**
A: "SailPoint and Saviynt use role engineering based on declared organisational charts. My approach mines roles from observed access behaviour — which catches privilege creep that the declared org chart doesn't reflect. That's actually an audit advantage: you discover what people are actually doing, not what HR says they should be doing. The trade-off is that behaviour-derived roles are harder to name and explain to business owners."

**Q: How do you evaluate the quality of your AI systems — not just model metrics, but LLM output quality?**
A: "For the RAG systems I used RAGAS — the standard evaluation framework for retrieval-augmented generation. On SportsSee NBA I ran 210 queries across 21 batches. Faithfulness scored 0.900 and Answer Correctness 0.880 — both strong. The interesting finding was Context Precision at 0.399: the LLM was generating good answers but the vector retrieval was not always surfacing the most relevant context. That's an architectural insight — it pointed to the FAISS index chunking strategy as the place to improve, not the generation layer. That kind of systematic evaluation is what separates a governed AI system from one that just works most of the time."

**Q: What would you do differently?**
A: "Three things. First, I would validate the label semantics before building any supervised model — the `ACTION=0` issue cost me iteration time that I could have avoided with one extra question about what those rows actually mean. Second, I would build the Docker stack in Phase 1 rather than deferring it — running in production containers from day one would have surfaced integration issues earlier. Third, I would apply RAGAS evaluation to all RAG projects from the start rather than adding it later — the context precision gap I found in SportsSee would have been caught much earlier in development."

**Q: How has your perception of the Data Scientist role changed?**
A: "I came in thinking data science was primarily about model selection and metrics. I leave understanding that it is primarily about system design — how you structure data pipelines, how you make results explainable to non-technical stakeholders, how you design for reproducibility and audit trails. Those concerns were familiar to me from audit. What surprised me is how rarely they are prioritised in ML practice — and how much of a competitive advantage they become when they are."

**Q: You have a 15-year career in audit. Why did you need this qualification?**
A: "Because the AI risk assessments I will be asked to do in the next 5 years require me to evaluate whether a model is fit for purpose — not just whether the governance process around it is documented. Without this qualification, I can audit the governance framework but I cannot evaluate the model itself. With it, I can do both. The EU AI Act is pushing organisations to have that capability internally. I want to be the person who provides it."

**Q: What are your professional objectives?**
A: "Senior AI Governance or AI Audit roles, ideally in Switzerland — financial sector, international organisations, or technology. I want to help organisations build AI governance that actually works: not compliance theatre, but systems where the controls match the technical reality of the AI being governed. The combination of CISA, the AAIA™ credential, and 12 ML projects is designed specifically for that."

---

## TIMING GUIDE

| Section | Target | Hard limit |
|---|---|---|
| Slides 1–2 (intro + portfolio) | 2.5 min | 3 min |
| Slide 3 (competencies) | 2 min | 2.5 min |
| Slides 4–6 (capstone) | 6.5 min | 8 min |
| Slides 7–8 (PM + reflections) | 3 min | 3.5 min |
| Slide 9 (objectives) | 30 sec | 1 min |
| **TOTAL** | **14.5 min** | **18 min** |

**If running short:** expand Slide 6 (results + limitations — this is where evaluators want depth)  
**If running long:** cut Slide 2 (portfolio layers) — it is scene-setting, not evaluated content

---

## SUBMISSION CHECKLIST

- [ ] Portfolio deployed and accessible online (URL ready)
- [ ] PM report uploaded / linked from portfolio
- [ ] Technical project (GitHub repo) linked from portfolio
- [ ] ZIP prepared: `Shaik_Shahul_1_portfolio_052026.zip`
  - [ ] Portfolio URL in a `README.txt`
  - [ ] `project_management_report.md` (or PDF export)
  - [ ] GitHub repo link
- [ ] Mentor sign-off on competency map

---

*Defense prep document — Projet 13 · Shahul SHAIK · May 2026*
