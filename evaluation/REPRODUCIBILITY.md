# Reproducibility Guide: ServEase Evaluation & Benchmark Suite

This guide provides end-to-end instructions for independently reproducing every empirical metric, baseline measurement, modernized evaluation, anomaly benchmark, and ablation study in the ServEase evaluation suite.

---

## 1. Execution Environment & Dependencies

### 1.1 Hardware & Operating System
- **Operating System**: Windows 10/11, macOS, or Ubuntu Linux (tested on Windows 11 AMD64)
- **Memory**: $\ge 512$ MB RAM (Runs safely within free cloud hosting tiers such as Render Free)
- **Compute**: Standard CPU (No GPU or CUDA acceleration required)

### 1.2 Software Requirements
- **Python Version**: Python 3.10, 3.11, 3.12, or 3.14
- **Required Libraries** (Specified in `requirements.txt`):
  ```bash
  scikit-learn>=1.5.0
  numpy>=2.0.0
  scipy>=1.14.0
  pandas>=2.0.0
  pypdf>=5.0.0
  aiosqlite>=0.20.0
  sqlalchemy>=2.0.0
  ```

---

## 2. Database & Data Partitioning

### 2.1 Database Setup
The benchmark executes against the local relational SQLite database:
```
backend/servease.db
```
Set the environment flag in `backend/.env` to ensure local execution:
```env
USE_LOCAL_SQLITE=true
```

### 2.2 Dataset Splitting Strategy
- **Ground-Truth Positive Interactions**: 60 total user interactions (19 Accepted Job Applications + 41 Accepted Direct Offers).
- **Candidate Pool**: 47 active worker profiles.
- **Partitioning**: 70% Train/Validation ($N = 42$ queries) and 30% Held-Out Test ($N = 18$ queries).
- **Deterministic Seed**: Fixed `random.seed(42)` applied universally across all shuffle and split routines.

---

## 3. Step-by-Step Reproduction Commands

Run the following commands from the project root (`c:\Users\DARSHAN\Downloads\Servease`):

### Step 1: Database Entity & Schema Audit
```powershell
python -u evaluation/baseline/audit_runner.py
```
- **Expected Output**: JSON summary confirming 66 users, 47 workers, 64 jobs, 20 job applications, and 55 direct offers.

### Step 2: Baseline System Evaluation
```powershell
# 1. Matching & Recommendation Baseline
python -u evaluation/baseline/evaluate_matching.py

# 2. Anomaly Detection & Fraud Engine Baseline
python -u evaluation/baseline/evaluate_fraud.py

# 3. Latency & Candidate Pruning Efficiency Baseline
python -u evaluation/baseline/evaluate_efficiency.py
```
- **Generated Artifacts**:
  - `evaluation/results/baseline_results.json`
  - `evaluation/results/baseline_fraud_results.json`
  - `evaluation/results/baseline_efficiency_results.json`

### Step 3: Modernized Hybrid System Evaluation
```powershell
python -u evaluation/modernized/evaluate_hybrid_matching.py
```
- **Generated Artifacts**:
  - `evaluation/results/modernized_results.json`
  - `evaluation/results/comparison_results.json`

### Step 4: Component Ablation Study
```powershell
python -u evaluation/modernized/ablation_study.py
```
- **Generated Artifacts**:
  - `evaluation/results/ablation_results.json`

### Step 5: Unsupervised Anomaly Detection Benchmark
```powershell
python -u evaluation/modernized/evaluate_anomaly_models.py
```
- **Generated Artifacts**:
  - `evaluation/results/anomaly_benchmark_results.json`

---

## 4. Expected Metric Ranges

| Evaluation Stage | Script | Primary Metric | Expected Value Range |
|---|---|---|:---:|
| **Baseline Matcher** | `evaluate_matching.py` | Precision@1 (Test) | $0.5000$ |
| | | Recall@5 (Test) | $0.5000$ |
| | | MRR (Test) | $0.5000$ |
| | | 95% CI Recall@5 | $[0.2778, 0.7222]$ |
| | | Avg Latency | $1.2 - 2.2$ ms |
| **Modernized Matcher**| `evaluate_hybrid_matching.py` | Precision@1 (Test) | $0.5000$ |
| | | Recall@5 (Test) | $0.5000$ |
| | | MRR (Test) | **$0.5254$** (+5.08%) |
| | | 95% CI MRR | $[0.3121, 0.7375]$ |
| | | Avg Latency | $5.0 - 7.5$ ms |
| **Fraud Engine** | `evaluate_fraud.py` | Supervised AUC | **NOT CURRENTLY VERIFIABLE** |
| | | Flagged Outliers | 5 users ($7.6\%$) |
| **Efficiency** | `evaluate_efficiency.py` | Search Pruning | $96.49\%$ candidate reduction |
| | | Latency | $< 3.0$ ms |

---

## 5. Security & Privacy Notice
All scripts and logs are strictly sanitized:
- No user passwords, bcrypt hashes, or JWT tokens are accessed or saved.
- No personal phone numbers or email addresses are stored in evaluation output.
- All evaluation logs use anonymous integer IDs.
