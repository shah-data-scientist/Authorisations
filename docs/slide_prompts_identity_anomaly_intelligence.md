# Slide Modification Prompts — "Identity Anomaly Intelligence"
## ML-Based Access Anomaly Detection: Project Report & Technical Solution
### Projet 13 · Soutenance preparation · Shahul SHAIK

This deck is the **technical project deep-dive** presentation (14 slides, image-based).
The existing slides are already consistent with the final NMF architecture. Changes below are one verification, one metric fix, and one optional backup slide to add.

---

## Verification 1 — XGBoost AUC must not appear anywhere

**Status:** ✅ No change needed in this deck.

The current Slide 3 (Unsupervised Performance Metrics) correctly shows:
- Reconstruction MSE: 0.0033
- Cluster Separation: +0.740
- Self-Consistency Gap: +0.519

XGBoost AUC 0.694 does **not** appear in this deck. This is correct — XGBoost was explicitly rejected as methodologically flawed (ACTION=0 rows are provisioning refusals, not confirmed anomalies). The inconsistency existed only in `projects.ts` and `defense_preparation.md`, both of which have been fixed separately.

**Action:** Before the soutenance, do a final visual pass of all 14 slides to confirm no XGBoost metric crept in from an earlier version.

---

## Verification 2 — High Drift rate must be 13.9% throughout

**Status:** ✅ No change needed in this deck.

Slide 3 correctly shows 13.9% High Drift on own systems. The stale figure of 76.8% existed only in `defense_preparation.md` (now fixed).

**Talking point to prepare:** When Charlotte challenges this number, the answer is: *"13.9% of an employee's own accesses score as High Drift. This reflects the 74% of employees with weak single-role membership — they legitimately span multiple clusters. High Drift means 'worth understanding', not 'confirmed anomalous'. I surface this honestly in the dashboard UI."*

---

## Add Slide — "What I Would Do Differently" (backup / appendix)
*Hidden slide — not part of the main flow. Pull up only if Charlotte asks "que feriez-vous différemment ?"*
*Add as Slide 15, after the current Slide 14 (Target Production Architecture).*

**Title:** "What I would do differently."

**Layout:** Dark background. Three bullet points, each two lines. Simple and direct.

---

**Bullet 1**
Partner with a security expert from day one.
50 validated incident labels would enable a supervised enrichment layer on top of the NMF cosine score.

**Bullet 2**
Build Docker in Phase 1, not Phase 5.
Running in production containers from the start surfaces integration issues before they accumulate.

**Bullet 3**
Apply RAGAS retrieval evaluation to all RAG projects from sprint 1.
The context precision gap found in SportsSee (0.399) would have been caught in week 2, not week 10 — pointing directly to the FAISS chunking strategy as the fix.

---

**Design notes:**
- Same dark background and typography as the rest of the deck
- No icons or charts needed — this is a spoken slide with minimal text
- Add a subtle "Appendix" or "Backup" label in the corner so it reads as supplementary material
- Slide number visible so you can navigate to it quickly during Q&A

---

*Prompts generated May 2026 — Projet 13 soutenance preparation · Shahul SHAIK*
