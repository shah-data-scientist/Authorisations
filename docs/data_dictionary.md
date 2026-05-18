# Data Dictionary — UCI Amazon Access Samples (id=216)

Source: [UCI ML Repository](https://archive.ics.uci.edu/dataset/216/amazon+access+samples)  
Original context: Amazon internal IAM system, 2010–2011

---

## Raw Dataset Columns (`data/raw/amazon_access_samples.csv`)

| Column | Type | Description |
|---|---|---|
| `ACTION` | int (0/1) | 1 = access granted; 0 = access revoked |
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

---

## Processed Files

### `data/interim/cleaned.parquet`
- Duplicates removed, rows with null `RESOURCE`, `MGR_ID`, or `ROLE_ROLLUP_1` dropped.
- Same schema as raw.

### `data/processed/user_permission_matrix.parquet`
- Index: `ROLE_CODE` (unique users)
- Columns: `RESOURCE` (unique resources)
- Values: 1.0 (has access) or 0.0 (no access) — binary

### `data/processed/access_events.parquet`
- Same as cleaned, kept in row format for drift detector training
- `ACTION = 0` rows (revocations) serve as implicit negative labels

---

## Key Statistics (approximate, full dataset)

| Metric | Value |
|---|---|
| Total rows | ~32,769 |
| Unique employees (ROLE_CODE) | ~3,874 |
| Unique resources (RESOURCE) | ~7,518 |
| Access-grant rate (ACTION=1) | ~94% |
| Access-revoke rate (ACTION=0) | ~6% |
| Matrix sparsity | ~99% |

---

## Known Limitations

- All categorical values are anonymised integers — no business meaning can be recovered.
- Timestamps have day-level granularity only; intra-day ordering is unknown.
- The revocation rate (6%) creates severe class imbalance for the drift classifier.
