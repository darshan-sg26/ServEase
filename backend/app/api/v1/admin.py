import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.domain import (
    User, UserRole, WorkerProfile, ProviderProfile, Job, JobSource, JobStatus,
    DirectOffer, FraudFlag, FraudFlagStatus, WorkerSkill, SkillStatus
)
from app.schemas.domain import (
    FraudFlagResponse, PlatformAnalyticsResponse,
    PendingSkillApprovalResponse, SkillRejectRequest
)
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

@router.get("/skill-approvals", response_model=List[PendingSkillApprovalResponse])
async def get_pending_skill_approvals(
    current_user: User = Depends(verify_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin Queue: Retrieve all worker-submitted skills awaiting manual verification.
    Strictly restricted to Admin role.
    """
    result = await db.execute(
        select(WorkerSkill)
        .options(selectinload(WorkerSkill.worker))
        .where(WorkerSkill.status == SkillStatus.PENDING)
        .order_by(WorkerSkill.submitted_at.desc())
    )
    skills = result.scalars().all()

    out = []
    for s in skills:
        w_profile = s.worker
        out.append(PendingSkillApprovalResponse(
            id=s.id,
            worker_id=s.worker_id,
            worker_name=w_profile.full_name if w_profile else f"Worker #{s.worker_id}",
            worker_trust_score=w_profile.trust_score if w_profile else 30.5,
            skill_name=s.skill_name,
            years_experience=s.years_experience,
            hourly_rate=s.hourly_rate,
            skill_tags=s.skill_tags or [],
            status=s.status.value if hasattr(s.status, "value") else str(s.status),
            submitted_at=s.submitted_at,
            created_at=s.created_at
        ))
    return out

@router.post("/skill-approvals/{skill_id}/approve")
async def approve_skill(
    skill_id: int,
    current_user: User = Depends(verify_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin Action: Approve a pending worker skill.
    Transitions status to VERIFIED and records audit timestamp & admin id.
    """
    result = await db.execute(
        select(WorkerSkill)
        .options(selectinload(WorkerSkill.worker))
        .where(WorkerSkill.id == skill_id)
    )
    skill = result.scalars().first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill submission not found")

    skill.status = SkillStatus.VERIFIED
    skill.reviewed_at = datetime.datetime.utcnow()
    skill.reviewed_by = current_user.id
    skill.rejection_reason = None
    skill.updated_at = datetime.datetime.utcnow()

    await db.commit()
    await db.refresh(skill)
    return {
        "success": True,
        "message": f"Skill '{skill.skill_name}' approved and verified successfully",
        "id": skill.id,
        "status": "verified"
    }

@router.post("/skill-approvals/{skill_id}/reject")
async def reject_skill(
    skill_id: int,
    data: Optional[SkillRejectRequest] = Body(default=None),
    current_user: User = Depends(verify_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin Action: Reject a pending worker skill.
    Transitions status to REJECTED and records audit timestamp, admin id, and optional reason.
    """
    result = await db.execute(
        select(WorkerSkill)
        .options(selectinload(WorkerSkill.worker))
        .where(WorkerSkill.id == skill_id)
    )
    skill = result.scalars().first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill submission not found")

    reason = data.reason.strip() if data and data.reason else None

    skill.status = SkillStatus.REJECTED
    skill.reviewed_at = datetime.datetime.utcnow()
    skill.reviewed_by = current_user.id
    skill.rejection_reason = reason
    skill.updated_at = datetime.datetime.utcnow()

    await db.commit()
    await db.refresh(skill)
    return {
        "success": True,
        "message": f"Skill '{skill.skill_name}' rejected",
        "id": skill.id,
        "status": "rejected",
        "rejection_reason": reason
    }
