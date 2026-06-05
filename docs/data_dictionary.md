# Data Dictionary — UCI Amazon Access Samples (id=216)

Source: [UCI ML Repository](https://archive.ics.uci.edu/dataset/216/amazon+access+samples)  
Original context: Amazon internal IAM system, 2010–2011

---

## Raw Dataset Columns (`data/raw/amazon_access_samples.csv`)

| Column | Type | Description |
|---|---|---|
| `ACTION` | int (0/1) | 1 = access granted; 0 = access request refused |
| `RESOURCE` | int | Unique identifier for the resource (system/application) |
| `MGR_ID` | int | Manager's employee ID |
| `ROLE_ROLLUP_1` | int | Broad department / business unit code |
| `ROLE_ROLLUP_2` | int | Sub-department code |
| `ROLE_DEPTNAME` | int | Encoded department name |
| `ROLE_TITLE` | int | Encoded job title |
| `ROLE_FAMILY_DESC` | int | Encoded role family description |
| `ROLE_FAMILY` | int | Encoded role family |
| `ROLE_CODE` | int | Unique employee role code — used as the user identifier in this project |

All categorical fields are integer-encoded (original string values were anonymised by Amazon).

**Note on `ACTION=0`:** These rows represent provisioning *refusals* — requests
that were denied at submission time. They are not access-revocation events. They
carry no anomaly signal and are excluded from all modelling steps.

---

## Processed Files

### `data/interim/cleaned.parquet`
- Duplicates removed, rows with null `RESOURCE`, `MGR_ID`, or `ROLE_ROLLUP_1` dropped.
- Same schema as raw (both `ACTION=0` and `ACTION=1` rows retained for reference).

### `data/processed/user_permission_matrix.parquet`
- Index: `ROLE_CODE` (unique users — `ACTION=1` rows only)
- Columns: `RESOURCE` (unique resources with at least one granted access)
- Values: 1.0 (has access) or 0.0 (no access) — binary
- Built from `ACTION=1` rows only; refused accesses are excluded.

### `audit/audit.db` (SQLite)

Created automatically at API startup. Persisted via Docker named volume `audit_db`.

**Table: `simulations`**

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `employee_id` | INTEGER | ROLE_CODE of the employee being simulated |
| `system_id` | INTEGER | RESOURCE ID of the system being simulated |
| `drift_score` | NUMERIC(5,4) | NMF cosine drift score at simulation time |
| `risk_label` | VARCHAR(20) | `Safe` / `Review` / `Escalate` |
| `explanation` | TEXT | Plain-language explanation from DriftScorer |
| `requested_at` | DATETIME | Timestamp of simulation (server default) |
| `review_status` | VARCHAR(20) | `pending` / `approved` / `denied` |
| `reviewed_by` | VARCHAR(255) | Reviewer identifier (set via PATCH) |
| `reviewed_at` | DATETIME | Timestamp of review decision |
| `notes` | TEXT | Reviewer notes |

**Table: `audit_log`**

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `action` | VARCHAR(100) | `simulation_created` / `simulation_approved` / `simulation_denied` / `access_revoked` |
| `employee_id` | INTEGER | Employee involved |
| `system_id` | INTEGER | System involved |
| `drift_score` | NUMERIC(5,4) | Score at time of event (nullable for revocations) |
| `performed_at` | DATETIME | Timestamp (server default) |
| `details` | TEXT | JSON-encoded metadata (risk label, reviewer, reason) |

---

### `data/processed/fleet_analytics.parquet`
- Pre-computed per-employee risk summary (cached; recomputed when stale).
- Columns: `employee_id`, `dominant_cluster`, `n_systems`, `n_high`, `n_minor`,
  `n_normal`, `balanced_risk_score`, `anomaly_rate`, `risk_category`, `computed_at`

---

## Key Statistics

| Metric | Value |
|---|---|
| Total rows (raw) | ~32,769 |
| Granted rows (ACTION=1) | ~30,857 (~94%) |
| Refused rows (ACTION=0) | ~1,912 (~6%) — excluded from modelling |
| Unique employees (ROLE_CODE, granted only) | 340 |
| Unique resources (granted only) | 7,226 |
| Matrix sparsity | ~99% |
| NMF reconstruction MSE | 0.0033 |

---

## Known Limitations

- All categorical values are anonymised integers — no business meaning can be recovered.
- Timestamps have day-level granularity only; intra-day ordering is unknown.
- `ACTION=0` rows are refusals, not revocations. True access-revocation events
  (grants that were later removed) are not distinguishable in this dataset.
- The user identifier is `ROLE_CODE`, not a unique employee ID — employees who
  changed roles during the period may appear as separate users.
