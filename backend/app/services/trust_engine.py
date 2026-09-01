import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.domain import WorkerProfile, Review, Job, JobStatus, VerificationStatus, TrustScoreLog, UserRole

async def compute_and_update_trust_score(worker_id: int, db: AsyncSession) -> float:
    """
    Computes worker trust score (0-100) using Bayesian rating smoothing and volume-weighted reliability:
    trust_score = 100 * (
        0.35 * rating_factor +
        0.25 * reliability_factor +
        0.15 * volume_factor +
        0.15 * verification_bonus +
        0.10 * response_factor
    )
    Logs every calculation to trust_score_log.
    """
    # Fetch worker profile
    result = await db.execute(select(WorkerProfile).where(WorkerProfile.id == worker_id))
    worker = result.scalars().first()
    if not worker:
        return 0.0

    # 1. Bayesian Smoothed Provider Rating Factor (0.0 - 1.0)
    rev_result = await db.execute(
        select(Review).where(
            Review.reviewee_id == worker.user_id,
            Review.reviewer_role == UserRole.PROVIDER
        )
    )
    reviews = rev_result.scalars().all()
    rating_count = len(reviews)
    if rating_count > 0:
        actual_avg_rating = sum(r.overall_rating or r.rating for r in reviews) / rating_count
    else:
        actual_avg_rating = 3.0  # Neutral prior

    # Bayesian smoothed rating with prior C=3.0 and confidence threshold m=5
    prior_rating = 3.0
    confidence_weight = 5.0
    smoothed_rating = (rating_count * actual_avg_rating + confidence_weight * prior_rating) / (rating_count + confidence_weight)
    rating_factor = min(1.0, max(0.0, smoothed_rating / 5.0))

    # 2. Reliability & Completion Factor (0.0 - 1.0)
    job_result = await db.execute(
        select(Job).where(Job.worker_id == worker.id)
    )
    jobs = job_result.scalars().all()
    completed_jobs = sum(1 for j in jobs if j.status == JobStatus.COMPLETED)
    total_assigned = len(jobs)
    worker.completed_jobs_count = completed_jobs

    if total_assigned == 0:
        reliability_factor = 0.0
    else:
        completion_ratio = completed_jobs / total_assigned
        # Ramps confidence over first 3 completed jobs
        volume_confidence = min(1.0, completed_jobs / 3.0)
        reliability_factor = completion_ratio * volume_confidence

    # 3. Experience Volume Factor (0.0 - 1.0)
    # Scales smoothly from 0 to 10 completed jobs
    volume_factor = min(1.0, completed_jobs / 10.0)

    # 4. Verification Bonus (0.0 or 1.0)
    verification_bonus = 1.0 if worker.verification_status == VerificationStatus.VERIFIED else 0.0

    # 5. Response & Platform Standing Factor (0.0 - 1.0)
    response_factor = 0.95

    # Compute final weighted score (0.0 to 100.0)
    raw_score = 100.0 * (
        0.35 * rating_factor +
        0.25 * reliability_factor +
        0.15 * volume_factor +
        0.15 * verification_bonus +
        0.10 * response_factor
    )
    trust_score = round(min(100.0, max(0.0, raw_score)), 1)

    # Update profile score
    worker.trust_score = trust_score

    # Log to trust_score_log for auditability
    factors = {
        "rating_count": rating_count,
        "actual_avg_rating": round(actual_avg_rating, 2) if rating_count > 0 else None,
        "smoothed_rating": round(smoothed_rating, 2),
        "rating_factor": round(rating_factor, 3),
        "completed_jobs": completed_jobs,
        "total_assigned": total_assigned,
        "reliability_factor": round(reliability_factor, 3),
        "volume_factor": round(volume_factor, 3),
        "verification_bonus": verification_bonus,
        "response_factor": response_factor,
    }
    log_entry = TrustScoreLog(
        worker_id=worker.id,
        score=trust_score,
        factors=factors
    )
    db.add(log_entry)
    await db.commit()
    return trust_score
