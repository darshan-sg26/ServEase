# Ground Truth Audit: Prediction Inputs vs Outcome Relevance Signals

A critical principle of scientific evaluation in recommender systems is the rigorous separation of **features available prior to prediction** from **downstream outcome signals** that constitute ground truth.

---

## 1. Separation of Inputs and Outcomes

```
PRE-PREDICTION INPUTS (Features)                  POST-DECISION OUTCOMES (Ground Truth)
┌──────────────────────────────────────┐          ┌──────────────────────────────────────┐
│ Worker Profile:                      │          │ User Interactions:                   │
│ - Skills & Skill Tags                │          │ - JobApplication (APPLIED)           │
│ - Bio / Self-description             │    ──►   │ - JobApplication (ACCEPTED / REJECT) │
│ - Coordinates (Lat, Lon)             │          │ - DirectOffer (ACCEPTED / DECLINED)  │
│ - Service Radius (km)                │          │                                      │
│ - Trust Score (Bayesian prior)       │          │ Work Completion:                     │
│ - Availability Status (AVAILABLE)    │          │ - Job (COMPLETED / CANCELLED)        │
│                                      │          │ - Review Rating (1 - 5 stars)        │
│ Job Posting:                         │          └──────────────────────────────────────┘
│ - Title, Description, Required Skill │
│ - Coordinates (Lat, Lon)             │
│ - Search Radius (km)                 │
└──────────────────────────────────────┘
```

### 1.1 Valid Input Features (Pre-Prediction)
These attributes represent state known at the exact instant a provider requests candidate matches:
- `job.title`, `job.description`, `job.required_skill`
- `job.latitude`, `job.longitude`, `job.search_radius_km`
- `worker.skills` (name, tags)
- `worker.bio`
- `worker.latitude`, `worker.longitude`, `worker.service_radius_km`
- `worker.trust_score` (historical prior calculated before the job assignment)
- `worker.availability_status`

### 1.2 Legitimate Ground Truth Signals (Post-Prediction)
These attributes represent empirical human judgment of candidate relevance:
1. **Strong Positive Signal ($y = 1$)**:
   - `JobApplication` with `status == 'ACCEPTED'`
   - `DirectOffer` with `status == 'ACCEPTED'`
   - `Job` completed with review rating $\ge 4.0$
2. **Negative Signal ($y = 0$)**:
   - `DirectOffer` with `status == 'DECLINED'`
   - `JobApplication` with `status == 'REJECTED'`
   - Unselected candidates in the candidate pool who were eligible by radius but not engaged

---

## 2. Recommendation Metric Formulations

Given a job $j$ and candidate pool $W_j$ of workers within the job's search radius, a matching algorithm outputs a ranked list of top-$K$ workers $\mathcal{R}_K(j) = [w_1, w_2, \dots, w_K]$.

Let $\mathcal{Y}_j^+$ be the set of true positive workers for job $j$ (workers who were accepted or hired).

### 2.1 Precision@K
$$\text{Precision@}K(j) = \frac{|\mathcal{R}_K(j) \cap \mathcal{Y}_j^+|}{K}$$

### 2.2 Recall@K
$$\text{Recall@}K(j) = \frac{|\mathcal{R}_K(j) \cap \mathcal{Y}_j^+|}{|\mathcal{Y}_j^+|}$$

### 2.3 Mean Reciprocal Rank (MRR)
$$\text{MRR} = \frac{1}{|J|} \sum_{j \in J} \frac{1}{\text{rank}(w_j^*)}$$
where $\text{rank}(w_j^*)$ is the rank of the first relevant worker in the recommendation list (or $0$ if not found).

### 2.4 Normalized Discounted Cumulative Gain (NDCG@K)
$$\text{DCG@}K(j) = \sum_{i=1}^K \frac{\mathbb{I}(w_i \in \mathcal{Y}_j^+)}{\log_2(i + 1)}, \quad \text{NDCG@}K(j) = \frac{\text{DCG@}K(j)}{\text{IDCG@}K(j)}$$

---

## 3. Ground Truth Audit for Fraud Detection

### 3.1 What Exists in ServEase
- `fraud_flags` table containing 5 records created by `run_isolation_forest_fraud_detection()`.
- These are **unsupervised model outputs**, NOT human-annotated or verified ground truth.

### 3.2 What Is Missing
- **No Ground Truth Fraud Column**: The `users` table has no `is_fraud: bool` field.
- **No External Chargeback / Abuse Dataset**: No confirmed fraudulent accounts exist.

### 3.3 The Impossibility of AUC Without Ground Truth
- Area Under the ROC Curve (AUC-ROC) requires comparing true positive rate against false positive rate across decision thresholds $\tau \in [0, 1]$:
  $$\text{TPR}(\tau) = \frac{\text{TP}(\tau)}{\text{TP}(\tau) + \text{FN}(\tau)}, \quad \text{FPR}(\tau) = \frac{\text{FP}(\tau)}{\text{FP}(\tau) + \text{TN}(\tau)}$$
- Without true binary labels $\{y_i\}_{i=1}^N$, $\text{TP}, \text{FP}, \text{FN}, \text{TN}$ cannot be computed.
- **Audit Conclusion**: Any claim of a specific AUC (e.g. 0.85–0.90) on ServEase data is mathematically unsubstantiated. We formally report this limitation rather than fabricating pseudo-labels.
