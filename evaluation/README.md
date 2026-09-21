# ServEase Scientific Research Validation & Modernization Benchmark

This repository directory contains the formal scientific engineering audit, empirical baseline evaluations, research-backed modernization experiments, and final performance comparison for **ServEase: A Scalable Platform for Aggregation of Local Skilled Workforce Services**.

---

## Structure of the Evaluation Suite

```
evaluation/
├── README.md                      # Overview and directory guide
├── EVALUATION_REPORT.md           # Comprehensive final report (25 sections + Teacher-Ready Summary)
├── BASELINE_REPORT.md             # Empirical baseline measurement report of existing system
├── REPRODUCIBILITY.md             # Complete environment, seed, and replication instructions
│
├── audit/                         # Phase 0: Non-modifying architectural and data audit
│   ├── IMPLEMENTATION_AUDIT.md    # Detailed audit of ml_matching.py, fraud_engine.py, trust_engine.py
│   ├── ARCHITECTURE_AUDIT.md      # Presentation architecture claims vs code reality
│   ├── CLAIM_MATRIX.md            # Target claims validation matrix (VERIFIED / PARTIALLY / NOT VERIFIED)
│   ├── DATA_AUDIT.md              # Aggregate statistics, distributions, and missing fields
│   ├── GROUND_TRUTH_AUDIT.md      # Input signals vs observable outcome ground truth
│   └── LEAKAGE_AUDIT.md           # Evaluation pipeline temporal and outcome data leakage audit
│
├── papers/                        # Research literature review & technical mapping
│   ├── PAPER_REVIEW.md            # Literature review of 8 reference papers + newer 2026 literature
│   └── PAPER_TO_SERVEASE.md       # 11-aspect technical comparison between literature and ServEase
│
├── baseline/                      # Phase 1: Standalone baseline measurement scripts
│   ├── audit_runner.py            # Automated data extraction and statistics compiler
│   ├── evaluate_matching.py       # Precision@K, Recall@K, NDCG@K, MRR evaluation on existing matcher
│   ├── evaluate_fraud.py          # Isolation Forest anomaly scoring analysis & AUC limitation report
│   └── evaluate_efficiency.py     # Latency (ms) and candidate retrieval efficiency evaluation
│
├── modernized/                    # Phase 2: Research-backed hybrid matching & anomaly benchmarking
│   ├── hybrid_matcher.py          # Additive semantic embedding + skill normalization + geo + trust reranker
│   ├── evaluate_hybrid_matching.py# Controlled re-evaluation on identical train/test splits
│   ├── evaluate_anomaly_models.py # Anomaly detector benchmark (Isolation Forest vs DIF / HF-DIF principles)
│   └── ablation_study.py          # Controlled ablation study across 5 architectural configurations
│
└── results/                       # Empirical experiment results (JSON artifacts)
    ├── baseline_results.json      # Raw baseline measurements
    ├── modernized_results.json    # Raw modernized hybrid measurements
    ├── comparison_results.json    # Side-by-side baseline vs modernized comparison
    └── ablation_results.json      # Component-level ablation deltas
```

---

## Core Scientific Principles Followed

1. **Zero Data Fabrication**: No synthetic users, jobs, ratings, or labels were manufactured to game results.
2. **Strict Ground Truth Adherence**: Where labels do not exist (specifically **Fraud Detection AUC**, due to lack of ground truth fraud annotations), the metric is explicitly recorded as **"NOT CURRENTLY VERIFIABLE"**.
3. **Controlled Comparison**: The baseline and modernized systems are evaluated under identical candidate pools, ground truth definitions, and train/test splits.
4. **Reproducibility**: All evaluation scripts run deterministically using fixed random seeds.
