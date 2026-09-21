# Baseline Evaluation Report: Current ServEase System

**Evaluation Date**: September 2026  
**System Evaluated**: Production ServEase Baseline Matcher (`backend/app/services/ml_matching.py`) & Fraud Engine (`backend/app/services/fraud_engine.py`)  
**Data Source**: Active SQLite Relational Database (`backend/servease.db`)  
**Random Seed**: `42` (Fixed for 100% deterministic reproducibility)  

---

## 1. Executive Summary

This report documents the empirical baseline performance of the existing ServEase platform prior to any research modernization. All numbers represent actual measured outcomes against real historical user interactions (accepted applications and accepted direct offers).

### Key Findings
1. **Target Claims vs Measured Reality**:
   - **Matching Precision**: Presentation claimed `~0.86`. Measured baseline achieves **$0.5000$ (50.0%) Precision@1** on the held-out test split, and **$0.6833$ (68.33%)** across all historical interactions.
   - **Recall@5**: Measured baseline achieves **$0.5000$ (50.0%)** on held-out test queries, with a 95% bootstrap confidence interval of $[0.2778, 0.7222]$.
   - **MRR (Mean Reciprocal Rank)**: Measured at **$0.5000$** on test queries.
   - **Fraud Detection AUC**: Formally determined as **NOT CURRENTLY VERIFIABLE**. The database contains zero verified fraud ground truth labels; the existing engine is an unsupervised Isolation Forest.
   - **Latency**: Highly efficient at **$1.238$ ms** average execution latency per matching request.

---

## 2. Recommendation Ranking Baseline Metrics

### 2.1 Dataset Partitioning
- **Total Worker Pool**: 47 active worker profiles.
- **Total Ground-Truth Interactions**: 60 positive interactions (19 Accepted Job Applications + 41 Accepted Direct Offers).
- **Split Strategy**: 70% Train/Validation (42 queries), 30% Held-Out Test (18 queries).

### 2.2 Empirical Baseline Results Table

| Metric | Held-Out Test Split ($N=18$) | 95% Bootstrap CI (Test) | Full Dataset ($N=60$) | Presentation Target Claim | Gap / Deficit |
|---|:---:|:---:|:---:|:---:|:---:|
| **Precision@1** | **0.5000** (50.0%) | [0.2778, 0.7222] | 0.6833 (68.33%) | ~0.86 (86.0%) | -36.0% (Test) |
| **Precision@3** | **0.1667** (16.7%) | [0.0926, 0.2407] | 0.2278 (22.8%) | N/A | — |
| **Precision@5** | **0.1000** (10.0%) | [0.0556, 0.1444] | 0.1367 (13.7%) | N/A | — |
| **Recall@1** | **0.5000** (50.0%) | [0.2778, 0.7222] | 0.6833 (68.33%) | 85% – 90% | -35.0% (Test) |
| **Recall@3** | **0.5000** (50.0%) | [0.2778, 0.7222] | 0.6833 (68.33%) | 85% – 90% | -35.0% (Test) |
| **Recall@5** | **0.5000** (50.0%) | [0.2778, 0.7222] | 0.6833 (68.33%) | 85% – 90% | -35.0% (Test) |
| **NDCG@3** | **0.5000** | [0.2778, 0.7222] | 0.6833 | N/A | — |
| **NDCG@5** | **0.5000** | [0.2778, 0.7222] | 0.6833 | N/A | — |
| **MRR** | **0.5000** | [0.2778, 0.7222] | 0.6833 | N/A | — |
| **Latency (ms)** | **1.516 ms** | [1.32, 1.75] | 2.110 ms | < 100 ms | Within Target |

---

## 3. Fraud / Anomaly Detection Baseline

### 3.1 Unsupervised Anomaly Scoring
- **Algorithm**: Scikit-learn `IsolationForest(contamination=0.1, random_state=42)`
- **Input Features**: `[rating_std, cancellation_rate, jobs_per_day, account_age=15.0, devices=1.0]`
- **Users Evaluated**: 66 users across all platform roles.
- **Anomalies Flagged**: 5 users (7.6% outlier rate).
- **Anomaly Score Range**: Min = $-0.1341$, Max = $0.0502$, Mean = $-0.0487$, Std = $0.0461$.

### 3.2 Scientific Status on AUC
- **Status**: **NOT CURRENTLY VERIFIABLE**
- **Deficit**: No human-verified fraud labels exist in the database. Computing ROC-AUC without binary ground truth is impossible. The presentation target of `0.85 – 0.90 Fraud AUC` cannot be validated on current data.

---

## 4. Operational Efficiency Baseline

- **Average Candidate Space Pruning**: **$96.49\%$** of irrelevant/out-of-bounds candidates are filtered prior to presentation.
- **Execution Latency**: Mean: **$1.238$ ms**, Median: **$1.201$ ms**, p95: **$1.642$ ms**.
- **Geographic Proximity Optimization**: Top-ranked candidates are on average $0.0$ km to $4.2$ km from the job site, achieving proximity clustering relative to unranked workers within the 15 km radius.

---

## 5. Architectural Weaknesses of Current Baseline Matcher

1. **Rigid Keyword Gating**: The matcher drops qualified workers if their profile does not contain exact keyword matches from the static 6-category dictionary (`SKILL_ALIASES`). If a worker writes "pipe fitting" or "leak specialist" without the root "plumb", the gate returns `False` and excludes them entirely.
2. **Hardcoded Behavioral Scores**: `completion_rate` and `acceptance_rate` default to $0.90$ and $0.85$ respectively, making the behavioral component virtually identical across all candidates.
3. **Absence of Semantic Vector Space**: Job descriptions and worker biographical narratives are never embedded into semantic vector space.
4. **Opaque Scalar Outputs**: Output percentages (e.g. `85%`) do not provide transparent factor-level explanations to users.
