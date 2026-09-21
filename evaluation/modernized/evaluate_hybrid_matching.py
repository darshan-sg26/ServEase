import json
import time
import math
import random
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from baseline.evaluate_matching import load_data, evaluate_queries, bootstrap_confidence_interval
from modernized.hybrid_matcher import ModernizedHybridMatcher

def run_modernized_evaluation():
    workers_data, queries = load_data()
    print(f"Loaded {len(workers_data)} workers and {len(queries)} ground-truth interaction queries for Modernized Matcher.")

    class MockProfile:
        def __init__(self, w_id):
            self.id = w_id
    for w in workers_data:
        w["profile_obj"] = MockProfile(w["id"])

    random.seed(42)
    shuffled_queries = list(queries)
    random.shuffle(shuffled_queries)

    split_idx = int(0.70 * len(shuffled_queries))
    train_queries = shuffled_queries[:split_idx]
    test_queries = shuffled_queries[split_idx:]

    matcher = ModernizedHybridMatcher(
        weight_semantic=0.35,
        weight_skill=0.30,
        weight_geo=0.20,
        weight_trust=0.10,
        weight_availability=0.05
    )

    def hybrid_rank_func(job_title, job_description, job_skill, job_lat, job_lng, workers_data, search_radius_km):
        return matcher.rank_workers_for_job(
            job_title=job_title,
            job_description=job_description,
            job_skill=job_skill,
            job_lat=job_lat,
            job_lng=job_lng,
            workers_data=workers_data,
            search_radius_km=search_radius_km,
            use_semantic=True,
            use_skill_norm=True,
            use_availability_gate=True
        )

    overall_metrics, _ = evaluate_queries(queries, workers_data, hybrid_rank_func)
    train_metrics, _ = evaluate_queries(train_queries, workers_data, hybrid_rank_func)
    test_metrics, test_per_query = evaluate_queries(test_queries, workers_data, hybrid_rank_func)

    ci_p5 = bootstrap_confidence_interval(test_per_query["precision_at_5"])
    ci_r5 = bootstrap_confidence_interval(test_per_query["recall_at_5"])
    ci_mrr = bootstrap_confidence_interval(test_per_query["mrr"])

    modernized_results = {
        "model": "Modernized Hybrid Matcher (Semantic TF-IDF + Skill Norm + Geo + Trust + Availability)",
        "code_location": "evaluation/modernized/hybrid_matcher.py",
        "random_seed": 42,
        "dataset": {
            "total_workers": len(workers_data),
            "total_queries": len(queries),
            "train_queries": len(train_queries),
            "test_queries": len(test_queries)
        },
        "overall_metrics": overall_metrics,
        "train_metrics": train_metrics,
        "test_metrics": test_metrics,
        "test_confidence_intervals_95": {
            "precision_at_5": ci_p5,
            "recall_at_5": ci_r5,
            "mrr": ci_mrr
        }
    }

    results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../results'))
    os.makedirs(results_dir, exist_ok=True)
    out_path = os.path.join(results_dir, 'modernized_results.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(modernized_results, f, indent=2)

    print(f"\nSaved modernized evaluation results to {out_path}")
    print("\n--- MODERNIZED TEST SET PERFORMANCE ---")
    for k, v in test_metrics.items():
        print(f"  {k}: {v}")
    print("\n95% Bootstrap Confidence Intervals (Test Split):")
    print(f"  Precision@5: [{ci_p5[0]} - {ci_p5[1]}]")
    print(f"  Recall@5:    [{ci_r5[0]} - {ci_r5[1]}]")
    print(f"  MRR:         [{ci_mrr[0]} - {ci_mrr[1]}]")

    # Generate Side-by-Side Comparison with Baseline
    baseline_path = os.path.join(results_dir, 'baseline_results.json')
    if os.path.exists(baseline_path):
        with open(baseline_path, 'r', encoding='utf-8') as f:
            baseline_data = json.load(f)
        b_test = baseline_data["test_metrics"]
        m_test = test_metrics

        comparison = {
            "evaluation_conditions": "Identical held-out test split (18 queries, seed=42, 47 candidate workers)",
            "metrics_comparison": {}
        }
        for metric in ["precision_at_1", "precision_at_3", "precision_at_5", "recall_at_1", "recall_at_3", "recall_at_5", "ndcg_at_3", "ndcg_at_5", "mrr", "avg_latency_ms"]:
            b_val = b_test.get(metric, 0.0)
            m_val = m_test.get(metric, 0.0)
            diff = round(m_val - b_val, 4)
            pct_change = round(((m_val - b_val) / b_val * 100.0), 2) if b_val > 0 else None
            comparison["metrics_comparison"][metric] = {
                "baseline": b_val,
                "modernized": m_val,
                "delta": diff,
                "percentage_change": pct_change
            }

        comp_path = os.path.join(results_dir, 'comparison_results.json')
        with open(comp_path, 'w', encoding='utf-8') as f:
            json.dump(comparison, f, indent=2)
        print(f"Saved side-by-side comparison to {comp_path}")

    return modernized_results

if __name__ == "__main__":
    run_modernized_evaluation()
