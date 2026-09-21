# Implementation Audit: ServEase Matching, Fraud & Trust Engines

This document provides a line-by-line, code-level architectural audit of the algorithms implemented in the ServEase backend.

---

## 1. Matching Engine Audit: `backend/app/services/ml_matching.py`

### 1.1 Classification
- **Official Designation in Presentation**: "Hybrid Recommendation Engine (TF-IDF + Cosine Similarity)" / "Machine Learning Matching"
- **Actual Engineering Classification**: **Deterministic Rule-Based Weighted Scoring**
- **Evidence of ML**: **None**. There are no trained model weights, no vector embeddings, no scikit-learn models, no regression/classification heads, and no learning from historical interaction data.

### 1.2 Mathematical Formulation
The score computed by `rank_workers_for_job(...)` is given by:

$$\text{Match Score (\%)} = 100 \times \Big( 0.50 \cdot S_{\text{content}} + 0.25 \cdot S_{\text{geo}} + 0.15 \cdot F_{\text{trust}} + 0.10 \cdot S_{\text{behavioral}} \Big)$$

Where each component is computed as follows:

#### A. Skill Gate & Content Score ($S_{\text{content}}$)
The function `check_skill_relevance(job_skill, job_title, worker_skills)` acts as a strict eligibility gate:
1. **Token Extraction**: Concatenates `job_skill + " " + job_title`, converts to lowercase, and extracts word tokens (stripping English stop words: `the, a, an, and, or, for, in, to, of, with`).
2. **Worker Skill Extraction**: Collects `skill_name` tokens and `skill_tags` tokens from the worker profile.
3. **Condition 1 (Exact Token Overlap)**:
   $$\text{overlap} = \text{tokens}_{\text{job}} \cap \text{tokens}_{\text{worker}}$$
   If $|\text{overlap}| > 0$, returns `True` with score $\max(0.5, \frac{|\text{overlap}|}{\max(1, |\text{tokens}_{\text{job}}|)})$.
4. **Condition 2 (Hardcoded Domain Alias Dictionary)**:
   A dictionary of 6 static keyword domains (`plumbing`, `electrical`, `driving`, `cooking`, `housekeeping`, `carpentry`):
   - Example: `"plumbing": {"plumb", "plumber", "leak", "pipe", "drain", "sink", "sanitary", "faucet", "tap", "flush", "water", "toilet"}`
   - If the job text matches any keyword in a domain AND the worker has any token in that domain, returns `True` with fixed score `0.60`.
5. **Condition 3 (Substring Match)**:
   If any job word of $\ge 4$ characters is a substring of any worker token $\ge 4$ characters (or vice versa), returns `True` with fixed score `0.50`.
6. **Hard Gate Fallback**: If none match, returns `False, 0.0`. Workers failing this gate are dropped entirely from the recommendation list.

#### B. Geospatial Proximity Score ($S_{\text{geo}}$)
1. Calculates Haversine spherical distance $d$ in km using Earth radius $R = 6371.0$ km:
   $$a = \sin^2\left(\frac{\Delta\text{lat}}{2}\right) + \cos(\text{lat}_1)\cos(\text{lat}_2)\sin^2\left(\frac{\Delta\text{lon}}{2}\right)$$
   $$d = 2R \cdot \text{atan2}(\sqrt{a}, \sqrt{1-a})$$
2. Checks dual radius constraint: $d \le \min(\text{service\_radius}_{\text{worker}}, \text{search\_radius}_{\text{job}})$.
3. Normalized linear distance score:
   $$S_{\text{geo}} = \max\left(0.0, 1.0 - \frac{d}{\text{effective\_radius}}\right)$$

#### C. Trust Factor ($F_{\text{trust}}$)
Normalized from the worker profile's scalar `trust_score` (defaulting to 75.0 if unset):
$$F_{\text{trust}} = \min\left(1.0, \max\left(0.0, \frac{\text{trust\_score}}{100.0}\right)\right)$$

#### D. Behavioral Score ($S_{\text{behavioral}}$)
The code reads:
```python
completion_rate = worker.get("completion_rate", 0.90)
acceptance_rate = worker.get("acceptance_rate", 0.85)
behavioral_score = (completion_rate + acceptance_rate) / 2.0
```
- **Audit Finding**: In `jobs.py` (lines 249–250), `completion_rate` is hardcoded to `0.95` and `acceptance_rate` to `0.90`.
- In `ml_matching.py` (lines 108–109), the fallbacks are hardcoded to `0.90` and `0.85`.
- **Result**: $S_{\text{behavioral}}$ is practically constant ($0.875$ to $0.925$) across all workers, contributing a fixed $\approx 0.09$ points to every worker's score without reflecting actual empirical differences.

### 1.3 Runtime Integration & Calling Path
- **API Route**: `GET /api/v1/jobs/{job_id}/matches` (`backend/app/api/v1/jobs.py` line 225)
- **Execution Flow**:
  1. Fetches `Job` by `job_id`.
  2. Fetches all `WorkerProfile` records with eager-loaded `skills`.
  3. Prepares `workers_data` dictionaries.
  4. Calls `rank_workers_for_job(...)`.
  5. Filters matches where $\text{match\_score} \ge 30.0\%$.
  6. Returns a list of `MatchedWorkerResponse` sorted descending by `match_score`.
- **Mobile Client Usage**: `mobile_app/lib/screens/provider/provider_shell.dart` line 1347 (`ApiService.fetchJobMatches(jobId)`), invoked when the provider taps the **"ML Matches"** button on an active job card.

---

## 2. Fraud Engine Audit: `backend/app/services/fraud_engine.py`

### 2.1 Classification
- **Official Designation in Presentation**: "Isolation Forest ML for Anomaly Identification" / "Fraud Detection AUC: 0.85–0.90"
- **Actual Engineering Classification**: **Unsupervised Tabular Anomaly Detection** using scikit-learn `IsolationForest`.

### 2.2 Feature Vector & Algorithm
Evaluates every registered `User` on a 5-dimensional feature vector $\mathbf{x} = [x_1, x_2, x_3, x_4, x_5]$:
1. $x_1$ = `rating_std`: Sample standard deviation of ratings received from `Review` records ($\text{std} = 0.0$ if $\le 1$ review).
2. $x_2$ = `cancellation_rate`: Fraction of assigned jobs with status `JobStatus.CANCELLED`.
3. $x_3$ = `jobs_per_day`: Count of total assigned jobs divided by a fixed window of 30.0 days.
4. $x_4$ = `account_age`: **Hardcoded constant** `15.0` days (not dynamically derived from `user.created_at`).
5. $x_5$ = `distinct_devices`: **Hardcoded constant** `1.0` (no IP/device tracking table exists).

### 2.3 Detector Execution
```python
clf = IsolationForest(contamination=0.1, random_state=42)
clf.fit(X)
scores = clf.decision_function(X)  # Negative anomaly score
preds = clf.predict(X)              # -1 for anomaly, 1 for normal
```
- For users where `pred == -1`, an entry is recorded in `fraud_flags` with `status = 'OPEN'`.

### 2.4 Ground Truth Deficit & Scientific Implications on Fraud AUC
- **Ground Truth Audit**: The database contains **zero ground truth fraud labels** (`y_true`). There is no verified `is_fraud: bool` column, no external fraud chargeback dataset, and no manual dispute annotation table.
- **Scientific Conclusion**: In unsupervised anomaly detection without ground truth binary labels, **calculating ROC-AUC or AUC-PR is mathematically impossible**.
- **Audit Verdict**: The presentation claim of **"0.85–0.90 Fraud Detection AUC"** was an unvalidated target hypothesis (or a misattribution of academic literature benchmarks). It is **NOT CURRENTLY VERIFIABLE** on Servease data.

---

## 3. Trust Engine Audit: `backend/app/services/trust_engine.py`

### 3.1 Classification
- **Engineering Classification**: **Deterministic Bayesian Smoothed Rating + Reliability Volume Weighting**.

### 3.2 Mathematical Formulation
The trust score (scale 0.0 to 100.0) is computed by:

$$\text{trust\_score} = 100 \times \Big( 0.35 \cdot R_{\text{rating}} + 0.25 \cdot R_{\text{reliability}} + 0.15 \cdot V_{\text{volume}} + 0.15 \cdot B_{\text{verification}} + 0.10 \cdot F_{\text{response}} \Big)$$

Where:
1. **Bayesian Smoothed Rating Factor ($R_{\text{rating}}$)**:
   - Prior rating $C = 3.0$ stars, confidence weight $m = 5.0$ reviews.
   - For actual average rating $R$ from $N$ provider reviews:
     $$R_{\text{smoothed}} = \frac{N \cdot R + m \cdot C}{N + m}$$
     $$R_{\text{rating}} = \min\left(1.0, \max\left(0.0, \frac{R_{\text{smoothed}}}{5.0}\right)\right)$$
2. **Reliability Factor ($R_{\text{reliability}}$)**:
   - For $N_{\text{completed}}$ completed jobs out of $N_{\text{assigned}}$ total jobs:
     $$\text{completion\_ratio} = \frac{N_{\text{completed}}}{N_{\text{assigned}}}$$
     $$\text{volume\_confidence} = \min\left(1.0, \frac{N_{\text{completed}}}{3.0}\right)$$
     $$R_{\text{reliability}} = \text{completion\_ratio} \cdot \text{volume\_confidence}$$
3. **Experience Volume Factor ($V_{\text{volume}}$)**:
   $$V_{\text{volume}} = \min\left(1.0, \frac{N_{\text{completed}}}{10.0}\right)$$
4. **Verification Bonus ($B_{\text{verification}}$)**:
   $$B_{\text{verification}} = 1.0 \text{ if verified else } 0.0$$
5. **Response Factor ($F_{\text{response}}$)**: Fixed constant $0.95$.

### 3.3 Audit Logging
Every trust computation is persisted to `trust_score_log` with an audit payload of all intermediate components (136 logs recorded in SQLite).

---

## 4. Summary Matrix of Audited Algorithms

| Component | Code Location | Claimed Method | Actual Implementation | Machine Learning? | Status |
|---|---|---|---|:---:|---|
| **Job Matching** | `backend/app/services/ml_matching.py` | TF-IDF + Cosine Similarity Hybrid ML | Rule-based keyword overlap + static aliases + weighted sum | **No** | Verified Rule-Based |
| **Anomaly / Fraud** | `backend/app/services/fraud_engine.py` | Supervised Fraud Classifier (AUC 0.85-0.90) | Unsupervised Isolation Forest (contamination=0.1) | **Yes (Unsupervised)** | Ground Truth Missing |
| **Trust Scoring** | `backend/app/services/trust_engine.py` | Dynamic ML Trust Scoring | Bayesian Smoothed Rating + Volume Weighting | **No** | Verified Heuristic |
| **Geospatial Distance** | `backend/app/services/ml_matching.py` | Haversine Proximity Optimization | Spherical Haversine calculation (R=6371.0 km) | **No (Deterministic Geometry)** | Verified Geometric |
