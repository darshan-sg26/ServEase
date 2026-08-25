from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.domain import User, WorkerProfile, WorkerSkill, AvailabilityStatus, VerificationStatus, Job, JobStatus
from app.schemas.domain import WorkerProfileResponse, WorkerProfileUpdate, WorkerSkillCreate, WorkerSkillResponse
from app.services.ml_matching import calculate_haversine_distance

router = APIRouter(prefix="/workers", tags=["Workers"])

@router.get("/me", response_model=WorkerProfileResponse)
async def get_my_worker_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(WorkerProfile)
        .options(selectinload(WorkerProfile.skills))
        .where(WorkerProfile.user_id == current_user.id)
    )
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Worker profile not found for logged in user")

    # Update completed_jobs_count dynamically
    jobs_res = await db.execute(
        select(Job).where((Job.worker_id == profile.id) & (Job.status == JobStatus.COMPLETED))
    )
    completed_jobs = jobs_res.scalars().all()
    profile.completed_jobs_count = len(completed_jobs)

    return profile

@router.get("", response_model=List[WorkerProfileResponse])
async def list_workers(
    skill: Optional[str] = Query(None, description="Filter by skill keyword"),
    near_lat: Optional[float] = Query(None, description="Provider latitude"),
    near_lng: Optional[float] = Query(None, description="Provider longitude"),
    max_distance_km: Optional[float] = Query(30.0, description="Max distance in km"),
    min_trust_score: Optional[float] = Query(0.0, description="Minimum trust score filter"),
    availability: Optional[AvailabilityStatus] = Query(None, description="Availability status"),
    db: AsyncSession = Depends(get_db)
):
    """
    Path B Browse & Offer requirement (Section 8 & Section 7.3):
    Searchable worker directory for providers with skill, geo, trust score, and availability filters.
    """
    stmt = select(WorkerProfile).options(selectinload(WorkerProfile.skills))
    
    if availability:
        stmt = stmt.where(WorkerProfile.availability_status == availability)
    
    if min_trust_score and min_trust_score > 0:
        stmt = stmt.where(WorkerProfile.trust_score >= min_trust_score)

    result = await db.execute(stmt)
    profiles = result.scalars().all()

    filtered = []
    for p in profiles:
        # Skill filter
        if skill and skill.strip():
            skill_matched = False
            for s in p.skills:
                if skill.lower() in s.skill_name.lower() or any(skill.lower() in t.lower() for t in s.skill_tags):
                    skill_matched = True
                    break
            if not skill_matched:
                continue

        # Geo distance filter
        if near_lat is not None and near_lng is not None:
            dist = calculate_haversine_distance(near_lat, near_lng, p.latitude, p.longitude)
            if dist > max_distance_km:
                continue

        filtered.append(p)

    return filtered

@router.get("/{worker_id}/profile", response_model=WorkerProfileResponse)
async def get_worker_profile(worker_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WorkerProfile)
        .options(selectinload(WorkerProfile.skills))
        .where(WorkerProfile.id == worker_id)
    )
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Worker profile not found")

    # Update completed_jobs_count dynamically
    jobs_res = await db.execute(
        select(Job).where((Job.worker_id == profile.id) & (Job.status == JobStatus.COMPLETED))
    )
    completed_jobs = jobs_res.scalars().all()
    profile.completed_jobs_count = len(completed_jobs)

    return profile

@router.put("/me", response_model=WorkerProfileResponse)
async def update_my_profile(
    data: WorkerProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(WorkerProfile)
        .options(selectinload(WorkerProfile.skills))
        .where(WorkerProfile.user_id == current_user.id)
    )
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Worker profile not found")

    if data.full_name is not None:
        profile.full_name = data.full_name
    if data.bio is not None:
        profile.bio = data.bio
    if data.gender is not None:
        profile.gender = data.gender
    if data.phone is not None:
        profile.phone = data.phone
    if data.profile_photo_url is not None:
        profile.profile_photo_url = data.profile_photo_url
    if data.latitude is not None:
        profile.latitude = data.latitude
    if data.longitude is not None:
        profile.longitude = data.longitude
    if data.service_radius_km is not None:
        profile.service_radius_km = data.service_radius_km
    if data.hourly_rate is not None:
        profile.hourly_rate = data.hourly_rate
    if data.languages_spoken is not None:
        profile.languages_spoken = data.languages_spoken
    if data.availability_status is not None:
        profile.availability_status = data.availability_status

    await db.commit()
    await db.refresh(profile)
    return profile

@router.post("/me/skills", response_model=WorkerSkillResponse)
async def add_skill(
    skill: WorkerSkillCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(WorkerProfile).where(WorkerProfile.user_id == current_user.id))
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Worker profile not found")

    new_skill = WorkerSkill(
        worker_id=profile.id,
        skill_name=skill.skill_name,
        years_experience=skill.years_experience,
        hourly_rate=skill.hourly_rate,
        skill_tags=skill.skill_tags
    )
    db.add(new_skill)
    await db.commit()
    await db.refresh(new_skill)
    return new_skill

@router.put("/me/availability", response_model=WorkerProfileResponse)
async def toggle_availability(
    status: AvailabilityStatus,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(WorkerProfile)
        .options(selectinload(WorkerProfile.skills))
        .where(WorkerProfile.user_id == current_user.id)
    )
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Worker profile not found")

    profile.availability_status = status
    await db.commit()
    await db.refresh(profile)
    return profile
