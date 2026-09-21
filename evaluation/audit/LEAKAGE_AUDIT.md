# Data Leakage Audit: Target Leakage & Temporal Contamination Analysis

This document details the audit conducted to ensure that the evaluation and recommendation pipelines do not leak future information, downstream targets, or test-set knowledge into the candidate matching algorithms.

---

## 1. Target Leakage Analysis

### 1.1 Evaluated Leakage Vectors

| Potential Leakage Vector | Description | Inspected in Code? | Leakage Detected? | Resolution / Safeguard |
|---|---|:---:|:---:|---|
| **Downstream Application Status** | Using `job_application.status == 'ACCEPTED'` inside the matching scoring formula. | `ml_matching.py` line 74–137 | **No Leakage** | Matcher only receives worker profile, coordinates, skills, and prior trust score. Does not receive application record. |
| **Direct Offer Outcome** | Using `direct_offers.status` as an input feature. | `ml_matching.py` | **No Leakage** | Direct offer outcomes are completely absent from the matching service inputs. |
| **Post-Job Review Rating** | Feeding the review rating for the specific job being matched into the worker's match score. | `jobs.py` line 235–251 | **No Leakage** | Matcher uses `worker.trust_score`, which is stored on the profile and not tied to the current job's eventual review. |
| **Post-Job Completion Status** | Using whether the job was eventually completed as a feature to predict whether the worker should be recommended. | `ml_matching.py` | **No Leakage** | `job.status` is checked only at retrieval time to ensure the job is `OPEN`. |

### 1.2 Trust Score Contamination Risk
- **Audit Observation**: In `backend/app/services/trust_engine.py`, `compute_and_update_trust_score()` updates `worker.trust_score` whenever a new review is submitted.
- **Evaluation Safeguard**: When conducting historical backtesting of past job recommendations, the worker's trust score must reflect their historical prior score at or before the job's posting timestamp (`created_at`), rather than their current lifetime trust score.
- The `trust_score_log` table preserves 136 timestamped historical calculation checkpoints, enabling chronological back-point trust attribution.

---

## 2. Train-Test Contamination & Tuning Audit

### 2.1 Anti-Gaming Compliance
- In accordance with Section 0 and Section 35 of the specification:
  - **Zero Test-Set Tuning**: No hyperparameters, weights, or thresholds will be tuned on the test split.
  - **Fixed Train / Test Partitions**: 70% of historical job interactions are partitioned for training/validation, and 30% are strictly held out for final evaluation.
  - **Deterministic Seeds**: All splits and algorithms utilize a fixed seed (`seed = 42`) for 100% reproducibility.

### 2.2 Metric Integrity
- The definitions of `Precision@K`, `Recall@K`, `NDCG@K`, and `MRR` are frozen prior to running baseline and modernized evaluations.
- No metrics will be modified or substituted based on observed results.
