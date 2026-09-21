import sqlite3
import json
import time
import math
import random
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend')))
from app.services.ml_matching import rank_workers_for_job, calculate_haversine_distance

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend/servease.db'))

def load_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, full_name, bio, latitude, longitude, service_radius_km, trust_score, availability_status
        FROM worker_profiles
    """)
    worker_rows = cursor.fetchall()
    workers_dict = {}
    for r in worker_rows:
        w_id = r[0]
        workers_dict[w_id] = {
            "id": w_id,
            "full_name": r[1] or f"Worker {w_id}",
            "bio": r[2] or "",
            "latitude": r[3],
            "longitude": r[4],
            "service_radius_km": r[5] or 15.0,
            "trust_score": r[6] if r[6] is not None else 75.0,
            "availability_status": r[7] or "AVAILABLE",
            "skills": [],
            "profile_obj": None
        }

    cursor.execute("SELECT worker_id, skill_name, skill_tags FROM worker_skills")
    for r in cursor.fetchall():
        w_id, s_name, s_tags_raw = r
        if w_id in workers_dict:
            try:
                s_tags = json.loads(s_tags_raw) if s_tags_raw else []
            except Exception:
                s_tags = []
            workers_dict[w_id]["skills"].append({
                "skill_name": s_name,
                "skill_tags": s_tags
            })

    cursor.execute("""
        SELECT a.id, j.id, j.title, j.description, j.required_skill, j.latitude, j.longitude, 
               j.search_radius_km, a.worker_id, a.status, a.applied_at
        FROM job_applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE a.status = 'ACCEPTED'
    """)
    app_queries = []
    for r in cursor.fetchall():
        app_queries.append({
            "interaction_id": f"app_{r[0]}",
            "source": "job_application",
            "job_id": r[1],
            "title": r[2] or "",
            "description": r[3] or "",
            "required_skill": r[4] or "",
            "latitude": r[5],
            "longitude": r[6],
            "search_radius_km": r[7] or 15.0,
            "target_worker_id": r[8],
            "status": r[9],
            "timestamp": r[10]
        })

    cursor.execute("""
        SELECT id, title, description, required_skill, latitude, longitude, worker_id, status, sent_at
        FROM direct_offers
        WHERE status = 'ACCEPTED'
    """)
    offer_queries = []
    for r in cursor.fetchall():
        offer_queries.append({
            "interaction_id": f"offer_{r[0]}",
            "source": "direct_offer",
            "job_id": None,
            "title": r[1] or "",
            "description": r[2] or "",
            "required_skill": r[3] or "",
            "latitude": r[4],
            "longitude": r[5],
            "search_radius_km": 15.0,
            "target_worker_id": r[6],
            "status": r[7],
            "timestamp": r[8]
        })

    conn.close()
    return list(workers_dict.values()), app_queries + offer_queries

def evaluate_queries(queries, workers_data, rank_func):
    """
    Evaluates recommendation queries and returns aggregate metrics + per-query metric records.
    """
    precisions_at_1 = []
    precisions_at_3 = []
    precisions_at_5 = []
    recalls_at_1 = []
    recalls_at_3 = []
    recalls_at_5 = []
    ndcg_at_3 = []
    ndcg_at_5 = []
    mrr_list = []
    latencies_ms = []

    for q in queries:
        target_w_id = q["target_worker_id"]
        t0 = time.perf_counter()
        ranked = rank_func(
            job_title=q["title"],
            job_description=q["description"],
            job_skill=q["required_skill"],
            job_lat=q["latitude"],
            job_lng=q["longitude"],
            workers_data=workers_data,
            search_radius_km=q["search_radius_km"]
        )
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000.0)

        ranked_ids = []
        for item in ranked:
            p_obj = item.get("worker_profile")
            if p_obj and hasattr(p_obj, "id"):
                ranked_ids.append(p_obj.id)
            elif isinstance(item.get("worker_profile"), dict) and "id" in item["worker_profile"]:
                ranked_ids.append(item["worker_profile"]["id"])
            elif "id" in item:
                ranked_ids.append(item["id"])
            elif "worker_id" in item:
                ranked_ids.append(item["worker_id"])

        def p_at_k(k):
            top_k = ranked_ids[:k]
            return 1.0 / k if target_w_id in top_k else 0.0

        def r_at_k(k):
            top_k = ranked_ids[:k]
            return 1.0 if target_w_id in top_k else 0.0

        def ndcg_at_k(k):
            top_k = ranked_ids[:k]
            if target_w_id in top_k:
                rank = top_k.index(target_w_id) + 1
                return (1.0 / math.log2(rank + 1)) / (1.0 / math.log2(1 + 1))
            return 0.0

        if target_w_id in ranked_ids:
            rank = ranked_ids.index(target_w_id) + 1
            mrr_list.append(1.0 / rank)
        else:
            mrr_list.append(0.0)

        precisions_at_1.append(p_at_k(1))
        precisions_at_3.append(p_at_k(3))
        precisions_at_5.append(p_at_k(5))
        recalls_at_1.append(r_at_k(1))
        recalls_at_3.append(r_at_k(3))
        recalls_at_5.append(r_at_k(5))
        ndcg_at_3.append(ndcg_at_k(3))
        ndcg_at_5.append(ndcg_at_k(5))

    def avg(lst):
        return sum(lst) / len(lst) if lst else 0.0

    summary = {
        "sample_count": len(queries),
        "precision_at_1": round(avg(precisions_at_1), 4),
        "precision_at_3": round(avg(precisions_at_3), 4),
        "precision_at_5": round(avg(precisions_at_5), 4),
        "recall_at_1": round(avg(recalls_at_1), 4),
        "recall_at_3": round(avg(recalls_at_3), 4),
        "recall_at_5": round(avg(recalls_at_5), 4),
        "ndcg_at_3": round(avg(ndcg_at_3), 4),
        "ndcg_at_5": round(avg(ndcg_at_5), 4),
        "mrr": round(avg(mrr_list), 4),
        "avg_latency_ms": round(avg(latencies_ms), 3),
        "median_latency_ms": round(sorted(latencies_ms)[len(latencies_ms)//2], 3) if latencies_ms else 0.0
    }

    per_query = {
        "precision_at_5": precisions_at_5,
        "recall_at_5": recalls_at_5,
        "mrr": mrr_list
    }

    return summary, per_query

def bootstrap_confidence_interval(metric_values, n_bootstraps=1000, seed=42):
    """
    Standard IR bootstrap resampling on query-level metric distributions.
    """
    if not metric_values:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(metric_values)
    means = []
    for _ in range(n_bootstraps):
        sample = [rng.choice(metric_values) for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    low = means[int(0.025 * n_bootstraps)]
    high = means[int(0.975 * n_bootstraps)]
    return (round(low, 4), round(high, 4))

def run_baseline_evaluation():
    workers_data, queries = load_data()
    print(f"Loaded {len(workers_data)} workers and {len(queries)} ground-truth interaction queries.")

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

    print(f"Split: Train={len(train_queries)}, Test={len(test_queries)}")

    overall_metrics, _ = evaluate_queries(queries, workers_data, rank_workers_for_job)
    train_metrics, _ = evaluate_queries(train_queries, workers_data, rank_workers_for_job)
    test_metrics, test_per_query = evaluate_queries(test_queries, workers_data, rank_workers_for_job)

    ci_p5 = bootstrap_confidence_interval(test_per_query["precision_at_5"])
    ci_r5 = bootstrap_confidence_interval(test_per_query["recall_at_5"])
    ci_mrr = bootstrap_confidence_interval(test_per_query["mrr"])

    baseline_results = {
        "model": "Current ServEase Baseline Matcher (Deterministic Weighted Scoring)",
        "code_location": "backend/app/services/ml_matching.py",
        "random_seed": 42,
        "dataset": {
            "total_workers": len(workers_data),
            "total_queries": len(queries),
            "train_queries": len(train_queries),
            "test_queries": len(test_queries),
            "positive_interaction_types": ["job_application_accepted", "direct_offer_accepted"]
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
    out_path = os.path.join(results_dir, 'baseline_results.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(baseline_results, f, indent=2)

    print(f"\nSaved baseline evaluation results to {out_path}")
    print("\n--- BASELINE TEST SET PERFORMANCE ---")
    for k, v in test_metrics.items():
        print(f"  {k}: {v}")
    print("\n95% Bootstrap Confidence Intervals (Test Split):")
    print(f"  Precision@5: [{ci_p5[0]} - {ci_p5[1]}]")
    print(f"  Recall@5:    [{ci_r5[0]} - {ci_r5[1]}]")
    print(f"  MRR:         [{ci_mrr[0]} - {ci_mrr[1]}]")

    return baseline_results

if __name__ == "__main__":
    run_baseline_evaluation()
