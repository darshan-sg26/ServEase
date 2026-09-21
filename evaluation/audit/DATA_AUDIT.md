# Data Audit: Entity Counts, Distributions & Data Quality

This document provides a comprehensive statistical and data quality audit of the local relational database (`backend/servease.db`). All statistics reflect the current state of the database without synthetic modification.

---

## 1. Aggregate Entity Counts

| Table Name | Description | Total Rows | Quality / Usability Status |
|---|---|:---:|---|
| `users` | Core authentication accounts (Workers, Providers, Admins) | **66** | 100% complete; hashed credentials & roles valid |
| `worker_profiles` | Worker operational profiles (coords, trust, rates, radius) | **47** | 47 / 47 have valid lat/lng and trust scores |
| `provider_profiles` | Job provider profiles (coords, contact details) | **12** | 12 / 12 have valid coordinates |
| `worker_skills` | Structured skills (name, years_exp, hourly_rate, tags) | **9** | Associated with workers 1–6; workers 7–47 lack skill entries |
| `jobs` | Job postings (title, desc, required_skill, location, status) | **64** | 64 / 64 have valid coordinates and required skills |
| `job_applications` | Inbound worker applications for jobs | **20** | 19 ACCEPTED, 1 APPLIED; valid timestamps and scores |
| `direct_offers` | Outbound direct offers sent from providers to workers | **55** | 41 ACCEPTED, 12 DECLINED, 2 PENDING |
| `reviews` | Bidirectional 5-star ratings and text feedback | **55** | 55 / 55 have overall ratings (mean rating = 4.89 / 5.0) |
| `fraud_flags` | Unsupervised anomaly detections from Isolation Forest | **5** | 5 flagged user anomaly events |
| `trust_score_log` | Bayesian trust score update audit logs | **136** | 136 historical computation checkpoints with factor payloads |
| `pending_registrations` | Pending OTP verification staging table | **1** | Temporary staging entry |

---

## 2. Field-Level Data Quality & Completeness

### 2.1 Worker Profiles ($N = 47$)
- **Geographic Coordinates**: 47 / 47 (100.0%) possess valid floating-point `latitude` and `longitude` values centered in Bengaluru (e.g. Lat: 12.92 to 13.04, Lon: 77.58 to 77.64).
- **Trust Scores**: Mean: $52.68$, Median: $42.70$, Min: $30.50$, Max: $94.20$.
- **Availability Status**: 46 workers marked `AVAILABLE`, 1 worker marked `BUSY`.
- **Bio Text Completeness**: Workers 1–5 have rich biographical narratives with explicit skill statements (e.g. Master Plumber, Licensed ITI Electrician, Commercial Driver, Home Cook, Carpenter). Workers 6–47 have `bio = None` as they were generated during integration and lifecycle testing.
- **Structured Skills**: Workers 1–6 have 9 relational entries in `worker_skills`. Workers 7–47 have empty skill arrays in the relational table.

### 2.2 Jobs ($N = 64$)
- **Geographic Coordinates**: 64 / 64 (100.0%) possess valid latitude and longitude coordinates.
- **Skill Requirements**:
  - `Plumbing`: 63 jobs (98.4%)
  - `Electrical Wiring`: 1 job (1.6%)
- **Job Status Distribution**:
  - `COMPLETED`: 19 jobs
  - `IN_PROGRESS`: 1 job
  - `OPEN`: 44 jobs
- **Search Radius**: All jobs specify `search_radius_km = 15.0` km.

### 2.3 Interaction Graph Density (Bipartite Graph Analysis)
- **Potential Edges**: $|W| \times |J| = 47 \text{ workers} \times 64 \text{ jobs} = 3,008 \text{ potential bipartite pairs}$.
- **Observable Positive Interactions**:
  - 19 Accepted Job Applications
  - 41 Accepted Direct Offers
  - **Total Positive Edges**: 60 unique worker-job positive pairs.
- **Negative / Rejection Interactions**:
  - 12 Declined Direct Offers
- **Graph Density**:
  $$\text{Density} = \frac{|E|}{|W| \cdot |J|} = \frac{72}{3,008} \approx 2.39\%$$
- **Implication for Advanced Deep Learning (GNNs)**:
  A graph density of $2.39\%$ across 47 workers and 64 jobs is **far too sparse** for high-capacity Graph Neural Networks (e.g. LightGCN or GCMC) without severe overfitting or memorization. This confirms the guideline in Section 27: **GNNs must not be forced and should remain documented as future work**.

---

## 3. Data Privacy & Anonymization Audit
- In accordance with academic data privacy standards:
  - No passwords, bcrypt hashes, or JWT tokens are included in evaluation datasets.
  - No private phone numbers or personal emails are logged.
  - Evaluation logs use anonymous integer identifiers (`worker_id`, `job_id`).
