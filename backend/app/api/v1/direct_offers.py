import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.domain import (
    User, UserRole, DirectOffer, DirectOfferStatus, Job, JobStatus, JobSource,
    ProviderProfile, WorkerProfile
)
from app.schemas.domain import DirectOfferCreate, DirectOfferResponse, DirectOfferRespond
from app.services.rating_service import build_worker_profile_response, build_provider_profile_response

router = APIRouter(prefix="/direct-offers", tags=["Direct Job Offers (Path B)"])

async def _build_offer_response(offer: DirectOffer, db: AsyncSession) -> DirectOfferResponse:
    resp = DirectOfferResponse.model_validate(offer)
    if offer.provider:
        resp.provider = await build_provider_profile_response(offer.provider, db)
    if offer.worker:
        resp.worker = await build_worker_profile_response(offer.worker, db)
    return resp

@router.post("", response_model=DirectOfferResponse)
async def create_direct_offer(
    data: DirectOfferCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != UserRole.PROVIDER and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only job providers can send direct job offers")

    p_res = await db.execute(select(ProviderProfile).where(ProviderProfile.user_id == current_user.id))
    provider = p_res.scalars().first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider profile not found")

    w_res = await db.execute(select(WorkerProfile).where(WorkerProfile.id == data.worker_id))
    worker = w_res.scalars().first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker profile not found")

    offer = DirectOffer(
        provider_id=provider.id,
        worker_id=worker.id,
        title=data.title,
        description=data.description,
        required_skill=data.required_skill,
        proposed_budget=data.proposed_budget,
        latitude=data.latitude or provider.default_latitude,
        longitude=data.longitude or provider.default_longitude,
        scheduled_date=data.scheduled_date,
        status=DirectOfferStatus.PENDING
    )
    db.add(offer)
    await db.commit()

    res = await db.execute(
        select(DirectOffer)
        .options(
            selectinload(DirectOffer.provider),
            selectinload(DirectOffer.worker).selectinload(WorkerProfile.skills)
        )
        .where(DirectOffer.id == offer.id)
    )
    o = res.scalars().first()
    return await _build_offer_response(o, db)

@router.get("", response_model=List[DirectOfferResponse])
async def list_direct_offers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(DirectOffer)
        .options(
            selectinload(DirectOffer.provider),
            selectinload(DirectOffer.worker).selectinload(WorkerProfile.skills)
        )
    )

    if current_user.role == UserRole.WORKER:
        w_res = await db.execute(select(WorkerProfile).where(WorkerProfile.user_id == current_user.id))
        worker = w_res.scalars().first()
        if worker:
            stmt = stmt.where(DirectOffer.worker_id == worker.id)
    elif current_user.role == UserRole.PROVIDER:
        p_res = await db.execute(select(ProviderProfile).where(ProviderProfile.user_id == current_user.id))
        provider = p_res.scalars().first()
        if provider:
            stmt = stmt.where(DirectOffer.provider_id == provider.id)

    stmt = stmt.order_by(DirectOffer.sent_at.desc())
    result = await db.execute(stmt)
    offers = result.scalars().all()

    resp_list = []
    for o in offers:
        resp_list.append(await _build_offer_response(o, db))
    return resp_list

@router.patch("/{offer_id}", response_model=DirectOfferResponse)
async def respond_to_offer(
    offer_id: int,
    data: DirectOfferRespond,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(DirectOffer)
        .options(
            selectinload(DirectOffer.provider),
            selectinload(DirectOffer.worker).selectinload(WorkerProfile.skills)
        )
        .where(DirectOffer.id == offer_id)
    )
    offer = result.scalars().first()
    if not offer:
        raise HTTPException(status_code=404, detail="Direct offer not found")

    action = data.action.lower()
    offer.responded_at = datetime.datetime.utcnow()
    if action == "accept":
        offer.status = DirectOfferStatus.ACCEPTED
        # Auto-create assigned Job requirement with started_at timestamp
        job = Job(
            provider_id=offer.provider_id,
            worker_id=offer.worker_id,
            title=offer.title,
            description=offer.description,
            required_skill=offer.required_skill,
            workers_needed=1,
            budget_min=offer.proposed_budget,
            budget_max=offer.proposed_budget,
            latitude=offer.latitude,
            longitude=offer.longitude,
            scheduled_date=offer.scheduled_date,
            source=JobSource.DIRECT_OFFER,
            status=JobStatus.ASSIGNED,
            started_at=datetime.datetime.utcnow()
        )
        db.add(job)
        await db.flush()
        offer.job_id = job.id

    elif action == "decline":
        offer.status = DirectOfferStatus.DECLINED

    await db.commit()
    await db.refresh(offer)
    return await _build_offer_response(offer, db)
