import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.domain import User, WorkerProfile, WorkerSkill, AvailabilityStatus, VerificationStatus, Job, JobStatus
from app.schemas.domain import (
    WorkerProfileResponse, WorkerProfileUpdate, WorkerLocationUpdate,
    WorkerSkillCreate, WorkerSkillResponse
)
from app.services.ml_matching import calculate_haversine_distance
from app.services.rating_service import build_worker_profile_response

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

    return await build_worker_profile_response(profile, db)

@router.get("/nearby", response_model=List[WorkerProfileResponse])
async def list_nearby_workers(
    latitude: Optional[float] = Query(None, ge=-90.0, le=90.0, description="Provider latitude"),
    longitude: Optional[float] = Query(None, ge=-180.0, le=180.0, description="Provider longitude"),
    near_lat: Optional[float] = Query(None, ge=-90.0, le=90.0, description="Provider latitude alias"),
    near_lng: Optional[float] = Query(None, ge=-180.0, le=180.0, description="Provider longitude alias"),
    radius_km: float = Query(15.0, gt=0, le=100.0, description="Discovery radius in km"),
    skill: Optional[str] = Query(None, description="Optional skill filter"),
    query: Optional[str] = Query(None, description="Optional search query"),
    q: Optional[str] = Query(None, description="Optional search query alias"),
    db: AsyncSession = Depends(get_db)
):
    """
    Map-Based Worker Discovery:
    Finds nearby available workers within radius constraints.
    Computes accurate Haversine distance while applying a privacy-preserving
    micro-jitter to display coordinates to protect worker residential privacy.
    """
    lat = latitude if latitude is not None else near_lat
    lng = longitude if longitude is not None else near_lng
    if lat is None or lng is None:
        raise HTTPException(status_code=422, detail="Both latitude and longitude are required.")

    search_q = query or q
    stmt = (
        select(WorkerProfile)
        .options(selectinload(WorkerProfile.skills), selectinload(WorkerProfile.user))
        .where(WorkerProfile.availability_status == AvailabilityStatus.AVAILABLE)
    )

    result = await db.execute(stmt)
    profiles = result.scalars().all()

    nearby = []
    for p in profiles:
        # Exclude unverified or inactive users
        if p.user and not p.user.is_verified:
            continue

        # Check search query if provided
        if search_q and search_q.strip():
            tokens = [t.lower() for t in search_q.strip().split() if t.strip()]
            skills_str = " ".join([f"{s.skill_name} {' '.join(s.skill_tags or [])}" for s in p.skills]).lower()
            combined = f"{p.full_name.lower()} {p.bio.lower() if p.bio else ''} {skills_str}"
            if not all(tok in combined for tok in tokens):
                continue

        # Check skill filter if provided
        if skill and skill.strip():
            skill_matched = False
            for s in p.skills:
                if skill.lower() in s.skill_name.lower() or any(skill.lower() in t.lower() for t in s.skill_tags):
                    skill_matched = True
                    break
            if not skill_matched:
                continue

        # Calculate exact Haversine distance using true coordinates
        dist = calculate_haversine_distance(lat, lng, p.latitude, p.longitude)

        # Worker service radius constraint (matches ml_matching logic)
        worker_radius = p.service_radius_km or 15.0
        effective_radius = min(worker_radius, radius_km) if radius_km > 0 else worker_radius
        if dist > effective_radius:
            continue

        resp = await build_worker_profile_response(p, db)
        resp.distance_km = round(dist, 2)

        # Privacy protection: mask direct personal phone on discovery map
        resp.phone = None

        # Privacy protection: deterministic micro-jitter (shifts pin by ~150-250m so exact home is not pinpointed)
        jitter_lat = ((hash(f"{p.id}_lat") % 100) - 50) * 0.00004
        jitter_lng = ((hash(f"{p.id}_lng") % 100) - 50) * 0.00004
        resp.latitude = round(p.latitude + jitter_lat, 4)
        resp.longitude = round(p.longitude + jitter_lng, 4)

        nearby.append(resp)

    # Sort closest first
    nearby.sort(key=lambda w: w.distance_km if w.distance_km is not None else 9999.0)
    return nearby

@router.get("", response_model=List[WorkerProfileResponse])
async def list_workers(
    q: Optional[str] = Query(None, description="Free-text search query across worker name, skills, bio"),
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
    Searchable worker directory for providers with search query, skill, geo, trust score, and availability filters.
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
        # Free-text multi-token search (name, skills, tags, bio)
        if q and q.strip():
            tokens = [t.lower() for t in q.strip().split() if t.strip()]
            skills_str = " ".join([f"{s.skill_name} {' '.join(s.skill_tags or [])}" for s in p.skills]).lower()
            combined_search_text = f"{p.full_name.lower()} {p.bio.lower() if p.bio else ''} {skills_str}"
            
            # Every token must match at least one attribute of the worker
            if not all(tok in combined_search_text for tok in tokens):
                continue

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
        dist = None
        if near_lat is not None and near_lng is not None:
            dist = calculate_haversine_distance(near_lat, near_lng, p.latitude, p.longitude)
            if dist > max_distance_km:
                continue

        resp = await build_worker_profile_response(p, db)
        if dist is not None:
            resp.distance_km = round(dist, 2)
        filtered.append(resp)

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

    return await build_worker_profile_response(profile, db)

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
        profile.location_updated_at = datetime.datetime.utcnow()
    if data.longitude is not None:
        profile.longitude = data.longitude
        profile.location_updated_at = datetime.datetime.utcnow()
    if data.service_radius_km is not None:
        profile.service_radius_km = data.service_radius_km
    if data.location_name is not None:
        profile.location_name = data.location_name
    if data.hourly_rate is not None:
        profile.hourly_rate = data.hourly_rate
    if data.languages_spoken is not None:
        profile.languages_spoken = data.languages_spoken
    if data.availability_status is not None:
        profile.availability_status = data.availability_status

    await db.commit()
    await db.refresh(profile)
    return await build_worker_profile_response(profile, db)

@router.put("/me/location", response_model=WorkerProfileResponse)
async def update_my_location(
    data: WorkerLocationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Updates authenticated worker's live GPS coordinates, timestamp, and optional location name.
    """
    result = await db.execute(
        select(WorkerProfile)
        .options(selectinload(WorkerProfile.skills))
        .where(WorkerProfile.user_id == current_user.id)
    )
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Worker profile not found for logged in user")

    profile.latitude = data.latitude
    profile.longitude = data.longitude
    profile.location_updated_at = datetime.datetime.utcnow()
    if data.location_name:
        profile.location_name = data.location_name

    await db.commit()
    await db.refresh(profile)
    return await build_worker_profile_response(profile, db)

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
    return await build_worker_profile_response(profile, db)
