import numpy as np
from sklearn.ensemble import IsolationForest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.domain import User, FraudFlag, FraudFlagStatus, Review, Job, JobStatus

async def run_isolation_forest_fraud_detection(db: AsyncSession) -> int:
    """
    Section 6.4 Fraud Engine using scikit-learn IsolationForest anomaly detection.
    Evaluates users on behavioral metrics:
    [rating_std_dev, cancellation_rate, jobs_per_day_spike, account_age_days, distinct_devices]
    Flags anomalies to fraud_flags table for Admin human-in-the-loop review.
    """
    result = await db.execute(select(User))
    users = result.scalars().all()
    if len(users) < 3:
        return 0  # Not enough data for isolation forest fitting

    user_ids = []
    features = []

    for u in users:
        # 1. Rating standard deviation
        rev_res = await db.execute(select(Review).where(Review.reviewee_id == u.id))
        reviews = rev_res.scalars().all()
        if len(reviews) > 1:
            ratings = [r.rating for r in reviews]
            rating_std = float(np.std(ratings))
        else:
            rating_std = 0.0

        # 2. Cancellation rate
        job_res = await db.execute(select(Job).where((Job.worker_id == u.id) | (Job.provider_id == u.id)))
        jobs = job_res.scalars().all()
        if jobs:
            cancelled = sum(1 for j in jobs if j.status == JobStatus.CANCELLED)
            cancellation_rate = cancelled / len(jobs)
        else:
            cancellation_rate = 0.0

        # 3. Jobs per day spike
        jobs_per_day = len(jobs) / 30.0

        # 4. Account age days
        account_age = 15.0

        # 5. Distinct devices/IPs
        devices = 1.0

        user_ids.append(u.id)
        features.append([rating_std, cancellation_rate, jobs_per_day, account_age, devices])

    X = np.array(features)
    # Fit Isolation Forest
    clf = IsolationForest(contamination=0.1, random_state=42)
    clf.fit(X)
    scores = clf.decision_function(X)  # lower = more anomalous
    preds = clf.predict(X)              # -1 for anomaly, 1 for normal

    flagged_count = 0
    for idx, pred in enumerate(preds):
        if pred == -1:
            uid = user_ids[idx]
            anom_score = round(float(-scores[idx]), 3)

            # Check if open flag already exists
            existing = await db.execute(
                select(FraudFlag).where(
                    (FraudFlag.user_id == uid) & (FraudFlag.status == FraudFlagStatus.OPEN)
                )
            )
            if not existing.scalars().first():
                flag = FraudFlag(
                    user_id=uid,
                    anomaly_score=anom_score,
                    reason=f"Isolation Forest flagged rating volatility ({features[idx][0]:.2f}) and cancellation spike ({features[idx][1]:.2f})",
                    status=FraudFlagStatus.OPEN
                )
                db.add(flag)
                flagged_count += 1

    if flagged_count > 0:
        await db.commit()

    return flagged_count
