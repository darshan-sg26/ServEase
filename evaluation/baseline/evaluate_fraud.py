import sqlite3
import json
import numpy as np
import os
from sklearn.ensemble import IsolationForest

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend/servease.db'))

def evaluate_fraud_engine():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Fetch users
    cursor.execute("SELECT id, role, created_at FROM users")
    users = cursor.fetchall()
    print(f"Loaded {len(users)} users for anomaly detection audit.")

    features = []
    user_ids = []

    for u in users:
        uid = u[0]
        # Rating std
        cursor.execute("SELECT rating FROM reviews WHERE reviewee_id = ?", (uid,))
        ratings = [r[0] for r in cursor.fetchall()]
        rating_std = float(np.std(ratings)) if len(ratings) > 1 else 0.0

        # Cancellation rate
        cursor.execute("SELECT status FROM jobs WHERE worker_id = ? OR provider_id = ?", (uid, uid))
        jobs = [r[0] for r in cursor.fetchall()]
        cancelled = sum(1 for j in jobs if j == 'CANCELLED')
        cancellation_rate = cancelled / len(jobs) if jobs else 0.0

        # Jobs per day
        jobs_per_day = len(jobs) / 30.0

        # Account age (in production code, hardcoded to 15.0)
        account_age = 15.0

        # Distinct devices (in production code, hardcoded to 1.0)
        devices = 1.0

        features.append([rating_std, cancellation_rate, jobs_per_day, account_age, devices])
        user_ids.append(uid)

    conn.close()

    X = np.array(features)

    # Fit Isolation Forest
    clf = IsolationForest(contamination=0.1, random_state=42)
    clf.fit(X)
    raw_scores = clf.decision_function(X) # lower = more anomalous
    anomaly_scores = -raw_scores          # higher = more anomalous
    preds = clf.predict(X)                # -1 = anomaly, 1 = normal

    anomalies_detected = sum(1 for p in preds if p == -1)

    fraud_evaluation = {
        "engine": "Current ServEase Fraud Engine (scikit-learn IsolationForest)",
        "code_location": "backend/app/services/fraud_engine.py",
        "methodology": "Unsupervised Tabular Anomaly Detection",
        "contamination_parameter": 0.10,
        "input_features": [
            "rating_std (computed from reviews)",
            "cancellation_rate (computed from jobs)",
            "jobs_per_day (assigned jobs / 30.0)",
            "account_age (hardcoded constant: 15.0)",
            "distinct_devices (hardcoded constant: 1.0)"
        ],
        "dataset_statistics": {
            "total_users_evaluated": len(users),
            "users_flagged_as_anomalies": anomalies_detected,
            "anomaly_ratio": round(anomalies_detected / len(users), 4) if users else 0.0,
            "ground_truth_fraud_labels_count": 0,
            "ground_truth_legitimate_labels_count": 0
        },
        "score_distribution": {
            "min_anomaly_score": round(float(np.min(anomaly_scores)), 4),
            "max_anomaly_score": round(float(np.max(anomaly_scores)), 4),
            "mean_anomaly_score": round(float(np.mean(anomaly_scores)), 4),
            "std_anomaly_score": round(float(np.std(anomaly_scores)), 4),
            "median_anomaly_score": round(float(np.median(anomaly_scores)), 4),
            "90th_percentile_threshold": round(float(np.percentile(anomaly_scores, 90)), 4)
        },
        "scientific_evaluation_verdict": {
            "target_claim_auc": "0.85 - 0.90",
            "measured_auc": "NOT CURRENTLY VERIFIABLE",
            "justification": (
                "Supervised AUC-ROC / AUC-PR evaluation requires ground truth binary labels (y_true in {0, 1}). "
                "The ServEase database contains zero verified fraud labels. The Isolation Forest operates "
                "purely as an unsupervised anomaly filter, flagging the top 10% highest-variance outliers. "
                "Reporting an AUC without labeled ground truth is mathematically invalid and rejected."
            )
        }
    }

    results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../results'))
    os.makedirs(results_dir, exist_ok=True)
    out_path = os.path.join(results_dir, 'baseline_fraud_results.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(fraud_evaluation, f, indent=2)

    print(f"\nSaved fraud evaluation audit to {out_path}")
    print(f"Evaluated {len(users)} users: {anomalies_detected} flagged as outliers (ratio: {anomalies_detected/len(users):.1%})")
    print(f"AUC Verification Status: {fraud_evaluation['scientific_evaluation_verdict']['measured_auc']}")
    print(f"Reason: {fraud_evaluation['scientific_evaluation_verdict']['justification']}")

    return fraud_evaluation

if __name__ == "__main__":
    evaluate_fraud_engine()
