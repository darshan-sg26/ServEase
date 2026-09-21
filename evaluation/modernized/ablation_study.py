import json
import time
import math
import random
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend')))
from baseline.evaluate_matching import load_data, evaluate_queries
from modernized.hybrid_matcher import ModernizedHybridMatcher
from app.services.ml_matching import rank_workers_for_job as baseline_rank_func

def run_ablation_study():
    workers_data, queries = load_data()
    print(f"Loaded {len(workers_data)} workers and {len(queries)} queries for Ablation Study.")

    class MockProfile:
        def __init__(self, w_id):
            self.id = w_id
    for w in workers_data:
        w["profile_obj"] = MockProfile(w["id"])

    random.seed(42)
    shuffled_queries = list(queries)
    random.shuffle(shuffled_queries)
    split_idx = int(0.70 * len(shuffled_queries))
    test_queries = shuffled_queries[split_idx:]
    print(f"Running Ablation on {len(test_queries)} held-out test queries.")

    ablation_results = {}

    # Model A: Baseline Matcher (ml_matching.py)
    res_a, _ = evaluate_queries(test_queries, workers_data, baseline_rank_func)
    ablation_results["Model A (Baseline Matcher)"] = {
        "description": "Rule-based keyword gate + deterministic 0.50/0.25/0.15/0.10 weighting",
        "metrics": res_a
    }

    # Model B: Baseline + Semantic Similarity
    matcher_b = ModernizedHybridMatcher(weight_semantic=0.35, weight_skill=0.30, weight_geo=0.25, weight_trust=0.10, weight_availability=0.0)
    def rank_b(job_title, job_description, job_skill, job_lat, job_lng, workers_data, search_radius_km):
        return matcher_b.rank_workers_for_job(job_title, job_description, job_skill, job_lat, job_lng, workers_data, search_radius_km, use_semantic=True, use_skill_norm=False, use_availability_gate=False)
    res_b, _ = evaluate_queries(test_queries, workers_data, rank_b)
    ablation_results["Model B (+ Semantic Similarity)"] = {
        "description": "Baseline structure + TF-IDF vector cosine similarity between job & worker",
        "metrics": res_b
    }

    # Model C: Baseline + Semantic + Skill Normalization
    matcher_c = ModernizedHybridMatcher(weight_semantic=0.35, weight_skill=0.30, weight_geo=0.25, weight_trust=0.10, weight_availability=0.0)
    def rank_c(job_title, job_description, job_skill, job_lat, job_lng, workers_data, search_radius_km):
        return matcher_c.rank_workers_for_job(job_title, job_description, job_skill, job_lat, job_lng, workers_data, search_radius_km, use_semantic=True, use_skill_norm=True, use_availability_gate=False)
    res_c, _ = evaluate_queries(test_queries, workers_data, rank_c)
    ablation_results["Model C (+ Skill Normalization)"] = {
        "description": "Model B + Canonical skill taxonomy normalization (ESCO/O*NET lightweight)",
        "metrics": res_c
    }

    # Model D: Baseline + Semantic + Skill Norm + Availability Gating
    matcher_d = ModernizedHybridMatcher(weight_semantic=0.35, weight_skill=0.30, weight_geo=0.20, weight_trust=0.10, weight_availability=0.05)
    def rank_d(job_title, job_description, job_skill, job_lat, job_lng, workers_data, search_radius_km):
        return matcher_d.rank_workers_for_job(job_title, job_description, job_skill, job_lat, job_lng, workers_data, search_radius_km, use_semantic=True, use_skill_norm=True, use_availability_gate=True)
    res_d, _ = evaluate_queries(test_queries, workers_data, rank_d)
    ablation_results["Model D (+ Availability Gating)"] = {
        "description": "Model C + Operational availability status penalty for BUSY workers",
        "metrics": res_d
    }

    # Model E: Full Hybrid Matcher with Factor-Wise Explainability
    matcher_e = ModernizedHybridMatcher(weight_semantic=0.35, weight_skill=0.30, weight_geo=0.20, weight_trust=0.10, weight_availability=0.05)
    def rank_e(job_title, job_description, job_skill, job_lat, job_lng, workers_data, search_radius_km):
        return matcher_e.rank_workers_for_job(job_title, job_description, job_skill, job_lat, job_lng, workers_data, search_radius_km, use_semantic=True, use_skill_norm=True, use_availability_gate=True)
    res_e, _ = evaluate_queries(test_queries, workers_data, rank_e)
    ablation_results["Model E (Full Hybrid Matcher)"] = {
        "description": "Full research-backed hybrid system: Semantic + Canonical Skills + Geo + Trust + Availability + Explainability",
        "metrics": res_e
    }

    base_metrics = res_a
    summary_table = []
    for model_name, model_info in ablation_results.items():
        m = model_info["metrics"]
        delta_p1 = round(m["precision_at_1"] - base_metrics["precision_at_1"], 4)
        delta_p5 = round(m["precision_at_5"] - base_metrics["precision_at_5"], 4)
        delta_r5 = round(m["recall_at_5"] - base_metrics["recall_at_5"], 4)
        delta_mrr = round(m["mrr"] - base_metrics["mrr"], 4)
        summary_table.append({
            "model": model_name,
            "precision_at_1": m["precision_at_1"],
            "delta_p1": delta_p1,
            "precision_at_5": m["precision_at_5"],
            "delta_p5": delta_p5,
            "recall_at_5": m["recall_at_5"],
            "delta_r5": delta_r5,
            "ndcg_at_5": m["ndcg_at_5"],
            "mrr": m["mrr"],
            "delta_mrr": delta_mrr,
            "avg_latency_ms": m["avg_latency_ms"]
        })

    ablation_payload = {
        "test_split_size": len(test_queries),
        "random_seed": 42,
        "models": ablation_results,
        "comparative_summary": summary_table
    }

    results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../results'))
    os.makedirs(results_dir, exist_ok=True)
    out_path = os.path.join(results_dir, 'ablation_results.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(ablation_payload, f, indent=2)

    print(f"\nSaved ablation study results to {out_path}")
    print("\n--- ABLATION SUMMARY (HELD-OUT TEST SET) ---")
    print(f"{'Model':<42} | {'P@1':<6} | {'Δ P@1':<8} | {'R@5':<6} | {'Δ R@5':<8} | {'MRR':<6} | {'Δ MRR':<8} | {'Latency':<8}")
    print("-" * 105)
    for row in summary_table:
        print(f"{row['model']:<42} | {row['precision_at_1']:<6.4f} | {row['delta_p1']:<+8.4f} | {row['recall_at_5']:<6.4f} | {row['delta_r5']:<+8.4f} | {row['mrr']:<6.4f} | {row['delta_mrr']:<+8.4f} | {row['avg_latency_ms']:<6.2f}ms")

    return ablation_payload

if __name__ == "__main__":
    run_ablation_study()
