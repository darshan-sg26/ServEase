from typing import Optional, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.domain import Review, UserRole, WorkerProfile, ProviderProfile
from app.schemas.domain import WorkerProfileResponse, ProviderProfileResponse

async def get_user_rating_stats(
    user_id: int,
    role: UserRole,
    db: AsyncSession
) -> Tuple[Optional[float], int, Dict[str, float]]:
    """
    Computes public rating stats from completed jobs:
    - For Workers: ratings given by Providers
    - For Providers: ratings given by Workers
    """
    reviewer_role = UserRole.PROVIDER if role == UserRole.WORKER else UserRole.WORKER
    stmt = select(Review).where(
        Review.reviewee_id == user_id,
        Review.reviewer_role == reviewer_role
    )
    res = await db.execute(stmt)
    reviews = res.scalars().all()

    if not reviews:
        return (None, 0, {})

    count = len(reviews)
    avg_rating = round(sum(r.overall_rating or r.rating for r in reviews) / count, 1)

    # Category averages
    cat_totals: Dict[str, float] = {}
    cat_counts: Dict[str, int] = {}
    for r in reviews:
        if r.category_ratings and isinstance(r.category_ratings, dict):
            for cat_name, cat_val in r.category_ratings.items():
                if isinstance(cat_val, (int, float)):
                    cat_totals[cat_name] = cat_totals.get(cat_name, 0.0) + cat_val
                    cat_counts[cat_name] = cat_counts.get(cat_name, 0) + 1

    category_averages = {
        cat: round(cat_totals[cat] / cat_counts[cat], 1)
        for cat in cat_totals
        if cat_counts[cat] > 0
    }

    return (avg_rating, count, category_averages)

async def build_worker_profile_response(
    worker: WorkerProfile,
    db: AsyncSession
) -> WorkerProfileResponse:
    avg_rating, count, _ = await get_user_rating_stats(worker.user_id, UserRole.WORKER, db)
    resp = WorkerProfileResponse.model_validate(worker)
    resp.avg_rating = avg_rating
    resp.rating_count = count
    return resp

async def build_provider_profile_response(
    provider: ProviderProfile,
    db: AsyncSession
) -> ProviderProfileResponse:
    avg_rating, count, _ = await get_user_rating_stats(provider.user_id, UserRole.PROVIDER, db)
    resp = ProviderProfileResponse.model_validate(provider)
    resp.avg_rating = avg_rating
    resp.rating_count = count
    return resp
