from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.domain import (
    User, UserRole, WorkerProfile, ProviderProfile, Job, JobSource, JobStatus,
    DirectOffer, FraudFlag, FraudFlagStatus
)
from app.schemas.domain import FraudFlagResponse, PlatformAnalyticsResponse
from app.services.fraud_engine import run_isolation_forest_fraud_detection

router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])

def verify_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin authorization required")
    return current_user

@router.get("/analytics", response_model=PlatformAnalyticsResponse)
async def get_analytics(
    current_user: User = Depends(verify_admin),
    db: AsyncSession = Depends(get_db)
):
    users_res = await db.execute(select(User))
    users = users_res.scalars().all()

    workers_res = await db.execute(select(WorkerProfile))
    workers = workers_res.scalars().all()

    providers_res = await db.execute(select(ProviderProfile))
    providers = providers_res.scalars().all()

    jobs_res = await db.execute(select(Job))
    jobs = jobs_res.scalars().all()

    offers_res = await db.execute(select(DirectOffer))
    offers = offers_res.scalars().all()

    flags_res = await db.execute(select(FraudFlag).where(FraudFlag.status == FraudFlagStatus.OPEN))
    open_flags = flags_res.scalars().all()

    path_a_count = sum(1 for j in jobs if j.source == JobSource.POSTED)
    path_b_count = sum(1 for j in jobs if j.source == JobSource.DIRECT_OFFER)
    completed_count = sum(1 for j in jobs if j.status == JobStatus.COMPLETED)

    return PlatformAnalyticsResponse(
        total_users=len(users),
        total_workers=len(workers),
        total_providers=len(providers),
        total_jobs=len(jobs),
        completed_jobs=completed_count,
        path_a_jobs_count=path_a_count,
        path_b_jobs_count=path_b_count,
        total_direct_offers=len(offers),
        open_fraud_flags=len(open_flags)
    )

@router.get("/fraud-flags", response_model=List[FraudFlagResponse])
async def get_fraud_flags(
    current_user: User = Depends(verify_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(FraudFlag).order_by(FraudFlag.flagged_at.desc()))
    flags = result.scalars().all()

    out = []
    for f in flags:
        u_res = await db.execute(select(User).where(User.id == f.user_id))
        user_obj = u_res.scalars().first()
        out.append(FraudFlagResponse(
            id=f.id,
            user_id=f.user_id,
            anomaly_score=f.anomaly_score,
            reason=f.reason,
            status=f.status,
            flagged_at=f.flagged_at,
            user_email=user_obj.email if user_obj else "unknown"
        ))
    return out

@router.patch("/fraud-flags/{id}")
async def update_fraud_flag(
    id: int,
    action: str,  # "dismiss" or "review"
    current_user: User = Depends(verify_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(FraudFlag).where(FraudFlag.id == id))
    flag = result.scalars().first()
    if not flag:
        raise HTTPException(status_code=404, detail="Fraud flag not found")

    if action == "dismiss":
        flag.status = FraudFlagStatus.DISMISSED
    elif action == "review":
        flag.status = FraudFlagStatus.REVIEWED

    await db.commit()
    return {"message": f"Fraud flag marked as {action}", "id": flag.id}

@router.post("/run-fraud-detection")
async def trigger_fraud_job(
    current_user: User = Depends(verify_admin),
    db: AsyncSession = Depends(get_db)
):
    count = await run_isolation_forest_fraud_detection(db)
    return {"message": "Isolation Forest fraud model batch executed", "new_anomalies_flagged": count}
