import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.domain import WorkerProfile, Review, Job, JobStatus, VerificationStatus, TrustScoreLog

async def compute_and_update_trust_score(worker_id: int, db: AsyncSession) -> float:
    """
    Computes worker trust score (0-100) using Section 6.3 weighted formula:
    trust_score = 100 * (
        0.40 * avg_rating_normalized +
        0.25 * completion_rate +
        0.15 * verification_bonus +
        0.10 * response_rate +
        0.10 * tenure_factor
    )
    Logs every calculation to trust_score_log.
    """
    # Fetch worker profile
    result = await db.execute(select(WorkerProfile).where(WorkerProfile.id == worker_id))
    worker = result.scalars().first()
    if not worker:
        return 0.0

    # 1. Avg Rating Normalized (0 - 1)
    rev_result = await db.execute(
        select(Review).where(Review.reviewee_id == worker.user_id)
    )
    reviews = rev_result.scalars().all()
    if reviews:
        avg_rating = sum(r.rating for r in reviews) / len(reviews)
        avg_rating_norm = avg_rating / 5.0
    else:
        avg_rating_norm = 0.8  # Default 4/5 for cold-start new workers

    # 2. Completion Rate (0 - 1)
    job_result = await db.execute(
        select(Job).where(Job.worker_id == worker.id)
    )
    jobs = job_result.scalars().all()
    if jobs:
        completed = sum(1 for j in jobs if j.status == JobStatus.COMPLETED)
        total_accepted = len(jobs)
        completion_rate = completed / total_accepted if total_accepted > 0 else 1.0
    else:
        completion_rate = 1.0

    # 3. Verification Bonus (0 or 1)
    verification_bonus = 1.0 if worker.verification_status == VerificationStatus.VERIFIED else 0.0

    # 4. Response Rate (0 - 1)
    response_rate = 0.95  # Default SLA compliance factor

    # 5. Tenure Factor (min(months / 12, 1))
    months = (datetime.datetime.utcnow() - worker.created_at).days / 30.0
    tenure_factor = min(months / 12.0, 1.0)
    if tenure_factor < 0.1:
        tenure_factor = 0.5  # Boost initial onboarding tenure

    # Calculate score
    raw_score = 100.0 * (
        0.40 * avg_rating_norm +
        0.25 * completion_rate +
        0.15 * verification_bonus +
        0.10 * response_rate +
        0.10 * tenure_factor
    )
    trust_score = round(min(100.0, max(0.0, raw_score)), 1)

    # Update profile score
    worker.trust_score = trust_score

    # Log to trust_score_log for auditability
    factors = {
        "avg_rating_norm": round(avg_rating_norm, 2),
        "completion_rate": round(completion_rate, 2),
        "verification_bonus": verification_bonus,
        "response_rate": response_rate,
        "tenure_factor": round(tenure_factor, 2)
    }
    log_entry = TrustScoreLog(
        worker_id=worker.id,
        score=trust_score,
        factors=factors
    )
    db.add(log_entry)
    await db.commit()
    return trust_score
