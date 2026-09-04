from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, Field, model_validator
from app.models.domain import (
    UserRole, AvailabilityStatus, VerificationStatus, JobUrgency,
    JobSource, JobStatus, ApplicationStatus, DirectOfferStatus, FraudFlagStatus
)

# Auth Schemas
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    role: UserRole = UserRole.WORKER
    full_name: str
    phone: Optional[str] = None
    gender: Optional[str] = "prefer_not_to_say"
    latitude: Optional[float] = 12.9716
    longitude: Optional[float] = 77.5946

class UserRegisterResponse(BaseModel):
    success: bool = True
    message: str = "Verification code sent to your email"
    requires_verification: bool = True
    email: str

class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str

class ResendOtpRequest(BaseModel):
    email: EmailStr

class SimpleResponse(BaseModel):
    success: bool
    message: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int

class UserResponse(BaseModel):
    id: int
    email: str
    phone: Optional[str]
    role: UserRole
    is_verified: bool
    created_at: datetime
    class Config:
        from_attributes = True

# Skill Schemas
class WorkerSkillBase(BaseModel):
    skill_name: str
    years_experience: float = 1.0
    hourly_rate: float = 300.0
    skill_tags: List[str] = []

class WorkerSkillCreate(WorkerSkillBase):
    pass

class WorkerSkillResponse(WorkerSkillBase):
    id: int
    worker_id: int
    class Config:
        from_attributes = True

# Worker Profile Schemas
class WorkerProfileBase(BaseModel):
    full_name: str
    bio: Optional[str] = None
    gender: Optional[str] = "prefer_not_to_say"
    phone: Optional[str] = None
    profile_photo_url: Optional[str] = None
    latitude: float = 12.9716
    longitude: float = 77.5946
    service_radius_km: float = 15.0
    location_name: Optional[str] = None
    location_updated_at: Optional[datetime] = None
    hourly_rate: float = 350.0
    completed_jobs_count: int = 0
    languages_spoken: List[str] = ["English", "Kannada", "Hindi"]
    availability_status: AvailabilityStatus = AvailabilityStatus.AVAILABLE

class WorkerProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    profile_photo_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    service_radius_km: Optional[float] = None
    location_name: Optional[str] = None
    hourly_rate: Optional[float] = None
    languages_spoken: Optional[List[str]] = None
    availability_status: Optional[AvailabilityStatus] = None

class WorkerLocationUpdate(BaseModel):
    latitude: float
    longitude: float
    location_name: Optional[str] = None

class WorkerProfileResponse(WorkerProfileBase):
    id: int
    user_id: int
    trust_score: float
    verification_status: VerificationStatus
    skills: List[WorkerSkillResponse] = []
    avg_rating: Optional[float] = None
    rating_count: int = 0
    created_at: datetime
    class Config:
        from_attributes = True

# Provider Profile Schemas
class ProviderProfileResponse(BaseModel):
    id: int
    user_id: int
    full_name: str
    phone: Optional[str] = None
    profile_photo_url: Optional[str] = None
    default_latitude: float
    default_longitude: float
    location_name: Optional[str] = None
    avg_rating: Optional[float] = None
    rating_count: int = 0
    class Config:
        from_attributes = True

class ProviderProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    profile_photo_url: Optional[str] = None
    default_latitude: Optional[float] = None
    default_longitude: Optional[float] = None
    location_name: Optional[str] = None

# Job Schemas (Path A & Shared)
class JobCreate(BaseModel):
    title: str
    description: str
    required_skill: str
    workers_needed: int = 1
    budget_min: float
    budget_max: float
    latitude: Optional[float] = 12.9716
    longitude: Optional[float] = 77.5946
    search_radius_km: Optional[float] = 10.0
    location_name: Optional[str] = None
    urgency: JobUrgency = JobUrgency.IMMEDIATE
    scheduled_date: Optional[str] = None

class JobResponse(BaseModel):
    id: int
    provider_id: int
    worker_id: Optional[int] = None
    title: str
    description: str
    required_skill: str
    workers_needed: int = 1
    accepted_count: int = 0
    budget_min: float
    budget_max: float
    latitude: float
    longitude: float
    search_radius_km: float = 10.0
    location_name: Optional[str] = None
    distance_km: Optional[float] = None
    urgency: JobUrgency
    scheduled_date: Optional[str]
    source: JobSource
    status: JobStatus
    provider_completed: bool = False
    worker_completed: bool = False
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    provider: Optional[ProviderProfileResponse] = None
    worker: Optional[WorkerProfileResponse] = None
    class Config:
        from_attributes = True

class MatchedWorkerResponse(BaseModel):
    worker: WorkerProfileResponse
    match_score: float
    distance_km: float
    content_score: float
    geo_score: float
    behavioral_score: float
    trust_score_factor: float

class JobApplicationResponse(BaseModel):
    id: int
    job_id: int
    worker_id: int
    status: ApplicationStatus
    match_score: float
    distance_km: float
    applied_at: datetime
    worker: Optional[WorkerProfileResponse] = None
    class Config:
        from_attributes = True

# Direct Offer Schemas (Path B)
class DirectOfferCreate(BaseModel):
    worker_id: int
    title: str
    description: str
    required_skill: str
    proposed_budget: float
    latitude: Optional[float] = 12.9716
    longitude: Optional[float] = 77.5946
    scheduled_date: Optional[str] = None

class DirectOfferResponse(BaseModel):
    id: int
    provider_id: int
    worker_id: int
    title: str
    description: str
    required_skill: str
    proposed_budget: float
    latitude: float
    longitude: float
    scheduled_date: Optional[str]
    status: DirectOfferStatus
    job_id: Optional[int]
    sent_at: datetime
    responded_at: Optional[datetime]
    provider: Optional[ProviderProfileResponse] = None
    worker: Optional[WorkerProfileResponse] = None
    class Config:
        from_attributes = True

class DirectOfferRespond(BaseModel):
    action: str  # "accept" or "decline"

# Review & Rating Schemas
class ReviewCreate(BaseModel):
    job_id: int
    overall_rating: Optional[int] = Field(None, ge=1, le=5)
    rating: Optional[int] = Field(None, ge=1, le=5)
    reviewee_id: Optional[int] = None
    category_ratings: Optional[dict] = Field(default_factory=dict)
    comment: Optional[str] = None

    @model_validator(mode="after")
    def populate_rating_fields(self):
        if self.overall_rating is None and self.rating is not None:
            self.overall_rating = self.rating
        elif self.rating is None and self.overall_rating is not None:
            self.rating = self.overall_rating
        elif self.overall_rating is None and self.rating is None:
            raise ValueError("Either overall_rating or rating must be provided (1-5)")
        return self

class ReviewResponse(BaseModel):
    id: int
    job_id: int
    reviewer_id: int
    reviewee_id: int
    reviewer_role: UserRole
    overall_rating: int
    rating: int
    category_ratings: Optional[dict] = None
    comment: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True

class JobRatingsStatusResponse(BaseModel):
    job_id: int
    is_completed: bool
    worker_rated_provider: bool
    provider_rated_worker: bool
    worker_review: Optional[ReviewResponse] = None
    provider_review: Optional[ReviewResponse] = None

class RatingSummaryResponse(BaseModel):
    user_id: int
    role: UserRole
    avg_rating: Optional[float] = None
    rating_count: int = 0
    category_averages: Optional[dict] = None
    recent_reviews: List[ReviewResponse] = []

# Admin & Analytics Schemas
class FraudFlagResponse(BaseModel):
    id: int
    user_id: int
    anomaly_score: float
    reason: str
    status: FraudFlagStatus
    flagged_at: datetime
    user_email: Optional[str] = None
    class Config:
        from_attributes = True

class PlatformAnalyticsResponse(BaseModel):
    total_users: int
    total_workers: int
    total_providers: int
    total_jobs: int
    completed_jobs: int
    path_a_jobs_count: int
    path_b_jobs_count: int
    total_direct_offers: int
    open_fraud_flags: int
