# Claim-to-Implementation Matrix

This matrix provides a scientific audit of the four primary quantitative claims presented in the ServEase presentation slides (`Digital-Trust-and-Intelligent-Job-Matching-Platform-for-Informal-Workforce.pptx`, Slide 7).

---

## Target Claims Audit Matrix

| # | Presentation Claim | Target Metric | Actual Implementation | Code Location | Data Available | Ground Truth Available? | Measurable on ServEase? | Baseline Result | Scientific Status |
|:---:|---|---|---|---|---|:---:|:---:|:---:|:---:|
| **1** | **Matching Accuracy** | **85% – 90%** | Deterministic weighted scoring: $0.50\cdot\text{skill} + 0.25\cdot\text{geo} + 0.15\cdot\text{trust} + 0.10\cdot\text{behavioral}$ | `backend/app/services/ml_matching.py` | 64 jobs, 47 workers, 20 applications | **Yes** (Accepted applications / hires indicate true relevance) | **Yes** (via Top-K Recommendation Relevance & Accuracy) | Measured in Phase 1 Baseline | **NOT VERIFIED** (Target hypothesis; baseline must be empirically tested) |
| **2** | **Precision Score** | **~0.86** | Rule-based token intersection & keyword alias gate filtering | `backend/app/services/ml_matching.py` | 20 job applications, 55 direct offers | **Yes** (Provider acceptances vs rejections / offers) | **Yes** (via Precision@K for $K \in \{1, 3, 5\}$) | Measured in Phase 1 Baseline | **NOT VERIFIED** (Target hypothesis; not backed by prior formal evaluation) |
| **3** | **Fraud Detection AUC** | **0.85 – 0.90** | Unsupervised `IsolationForest(contamination=0.1)` on 5 behavioral features | `backend/app/services/fraud_engine.py` | 5 logged anomaly records in `fraud_flags` | **NO** (Zero verified fraud/non-fraud ground truth labels) | **NO** (Supervised ROC-AUC cannot be calculated without binary labels) | **NOT CURRENTLY VERIFIABLE** | **NOT VERIFIED** (Mathematically unmeasurable without synthetic labels) |
| **4** | **Efficiency Gain** | **15% – 20%** | Spatial Haversine distance bounding ($d \le \text{radius}$) & skill gate pruning | `backend/app/services/ml_matching.py`<br>`backend/app/api/v1/jobs.py` | Full geographic coordinates & latency traces | **Yes** (Latency in ms, candidate pool reduction ratio) | **Yes** (Measured as search effort and latency delta) | Measured in Phase 1 Baseline | **NOT VERIFIED** (Target hypothesis; baseline benchmark required) |

---

## Detailed Status Justifications

### 1. Matching Accuracy (85%–90%)
- **Status**: **NOT VERIFIED**
- **Justification**: The claim in Slide 7 states "85% - 90% Matching Accuracy: Skill-job alignment precision". However, prior to this audit, no systematic test script existed in the repository to evaluate the accuracy of `rank_workers_for_job` against historical applicant acceptance or hiring outcomes. In information retrieval and recommender systems, "accuracy" is typically formulated as Precision@K or Hit Rate@K. The 85%–90% figure was an unverified target claim.

### 2. Precision Score (~0.86)
- **Status**: **NOT VERIFIED**
- **Justification**: In recommendation systems literature, precision must be defined explicitly (e.g. Precision@1, Precision@5, or binary classification precision on application acceptance). No precision calculation was previously coded or logged in the repository. We will measure the true empirical Precision@K in Phase 1.

### 3. Fraud Detection AUC (0.85–0.90)
- **Status**: **NOT CURRENTLY VERIFIABLE (NOT VERIFIED)**
- **Justification**: Anomaly detection in `fraud_engine.py` uses scikit-learn's `IsolationForest`, an unsupervised algorithm that flags the top 10% outliers based on tree path isolation depth.
  - To calculate **AUC-ROC** (Area Under the Receiver Operating Characteristic) or **AUC-PR**, one must have true positive and true negative binary labels: $y \in \{0, 1\}$.
  - The ServEase database contains no table, column, or dataset of confirmed fraudulent vs legitimate users.
  - Fabricating labels to force an AUC score between 0.85 and 0.90 violates the fundamental anti-gaming mandate.
  - Therefore, this claim is formally classified as **NOT CURRENTLY VERIFIABLE**. Unsupervised anomaly distributions will be benchmarked instead.

### 4. Efficiency Gain (15%–20%)
- **Status**: **NOT VERIFIED**
- **Justification**: The presentation cited "15% - 20% Efficiency Gain: Allocation optimization" (referencing Chen & Liu 2020 who achieved a 14% improvement in a research paper). In ServEase, efficiency was never benchmarked against a baseline (such as unpruned brute-force search). We establish a formal latency and candidate-reduction metric to measure actual efficiency gain.
