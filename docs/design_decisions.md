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

## 4. Drift scoring: overlap-based threshold, then classifier upgrade

**Stage 1 (rule-based):** If a newly requested resource is NOT in the top-50
permissions of the user's dominant role (or any secondary role with weight >5%),
the drift score is 1.0. This is interpretable and requires no training data.

**Stage 2 (classifier):** XGBoost trained on historical access-removal events
as implicit negative labels (a permission that was later revoked is a weak
signal that it was anomalous). This requires careful treatment of the severe
class imbalance (removals << grants).

**Why not only a classifier:** A black-box classifier alone cannot explain
*why* an access event is flagged. The rule-based score gives the primary
signal; SHAP on the classifier provides the secondary explanation layer.

---

## 5. Drift threshold: cost-weighted, not arbitrary

**Framing:**
- False positive (flag a legitimate grant) = analyst time wasted; user frustrated
- False negative (miss a malicious grant) = potential data breach

**Formula used:**
```
optimal_threshold = argmax F_beta where beta = cost(FN) / cost(FP)
```

In a typical IAM context, a missed over-provisioning event is 5–10× more
costly than a false alert. Hence beta > 1, favouring recall.

**Default threshold: 0.5** — to be tuned per deployment context.
Document your organisation's cost ratio in `config.py` before deploying.

---

## 6. Why FastAPI over Flask

FastAPI provides automatic OpenAPI docs at `/docs`, native Pydantic
validation, and async support. For a portfolio project serving a Streamlit
frontend, this gives a better developer experience and is what most
production security-data teams actually use (2024–2026 job postings).

---

## 7. What this project does NOT do (and why)

| Omission | Reason |
|---|---|
| Real-time Kafka/streaming ingestion | Out of scope for a 6-week portfolio project; noted as a future extension |
| Multi-tenancy / auth on the API | Not needed for a demo; add OAuth2 before production |
| LDAP/AD integration | No public LDAP dataset available; simulated via role attributes |
| Temporal drift (comparing week-over-week) | Dataset lacks fine-grained timestamps; flagged as a known limitation |
