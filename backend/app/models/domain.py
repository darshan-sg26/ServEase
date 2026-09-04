import datetime
import enum
import uuid
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum, Text, JSON, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.core.database import Base

class UserRole(str, enum.Enum):
    WORKER = "worker"
    PROVIDER = "provider"
    ADMIN = "admin"

class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"

class AvailabilityStatus(str, enum.Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"

class VerificationStatus(str, enum.Enum):
    UNVERIFIED = "unverified"
    PENDING = "pending"
    VERIFIED = "verified"

class JobUrgency(str, enum.Enum):
    IMMEDIATE = "immediate"
    SCHEDULED = "scheduled"

class JobSource(str, enum.Enum):
    POSTED = "posted"
    DIRECT_OFFER = "direct_offer"

class JobStatus(str, enum.Enum):
    OPEN = "open"
    MATCHED = "matched"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class ApplicationStatus(str, enum.Enum):
    APPLIED = "applied"
    SHORTLISTED = "shortlisted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class DirectOfferStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"

class FraudFlagStatus(str, enum.Enum):
    OPEN = "open"
    REVIEWED = "reviewed"
    DISMISSED = "dismissed"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.WORKER, nullable=False)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    worker_profile = relationship("WorkerProfile", back_populates="user", uselist=False)
    provider_profile = relationship("ProviderProfile", back_populates="user", uselist=False)
    fraud_flags = relationship("FraudFlag", back_populates="user")

class WorkerProfile(Base):
    __tablename__ = "worker_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    bio = Column(Text, nullable=True)
    gender = Column(String, default="prefer_not_to_say")
    phone = Column(String, nullable=True)
    profile_photo_url = Column(String, nullable=True)
    latitude = Column(Float, nullable=False, default=12.9716)
    longitude = Column(Float, nullable=False, default=77.5946)
    service_radius_km = Column(Float, nullable=False, default=15.0)
    location_name = Column(String, nullable=True)
    location_updated_at = Column(DateTime, nullable=True)
    hourly_rate = Column(Float, default=350.0)
    completed_jobs_count = Column(Integer, default=0)
    languages_spoken = Column(JSON, default=lambda: ["English", "Kannada", "Hindi"])
    availability_status = Column(SQLEnum(AvailabilityStatus), default=AvailabilityStatus.AVAILABLE)
    trust_score = Column(Float, default=30.5)
    verification_status = Column(SQLEnum(VerificationStatus), default=VerificationStatus.UNVERIFIED)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User", back_populates="worker_profile")
    skills = relationship("WorkerSkill", back_populates="worker", cascade="all, delete-orphan")
    applications = relationship("JobApplication", back_populates="worker")
    direct_offers = relationship("DirectOffer", back_populates="worker")
    trust_logs = relationship("TrustScoreLog", back_populates="worker")

class WorkerSkill(Base):
    __tablename__ = "worker_skills"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("worker_profiles.id"), nullable=False)
    skill_name = Column(String, nullable=False)
    years_experience = Column(Float, default=1.0)
    hourly_rate = Column(Float, default=300.0)
    skill_tags = Column(JSON, default=list)

    worker = relationship("WorkerProfile", back_populates="skills")

class ProviderProfile(Base):
    __tablename__ = "provider_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    profile_photo_url = Column(String, nullable=True)
    default_latitude = Column(Float, default=12.9716)
    default_longitude = Column(Float, default=77.5946)
    location_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User", back_populates="provider_profile")
    jobs = relationship("Job", back_populates="provider")
    direct_offers = relationship("DirectOffer", back_populates="provider")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("provider_profiles.id"), nullable=False)
    worker_id = Column(Integer, ForeignKey("worker_profiles.id"), nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    required_skill = Column(String, nullable=False)
    workers_needed = Column(Integer, nullable=False, default=1)
    budget_min = Column(Float, nullable=False)
    budget_max = Column(Float, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    search_radius_km = Column(Float, nullable=False, default=10.0)
    location_name = Column(String, nullable=True)
    urgency = Column(SQLEnum(JobUrgency), default=JobUrgency.IMMEDIATE)
    scheduled_date = Column(String, nullable=True)
    source = Column(SQLEnum(JobSource), default=JobSource.POSTED)
    status = Column(SQLEnum(JobStatus), default=JobStatus.OPEN)
    provider_completed = Column(Boolean, default=False)
    worker_completed = Column(Boolean, default=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    provider = relationship("ProviderProfile", back_populates="jobs")
    worker = relationship("WorkerProfile")
    applications = relationship("JobApplication", back_populates="job")
    reviews = relationship("Review", back_populates="job")

class JobApplication(Base):
    __tablename__ = "job_applications"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    worker_id = Column(Integer, ForeignKey("worker_profiles.id"), nullable=False)
    status = Column(SQLEnum(ApplicationStatus), default=ApplicationStatus.APPLIED)
    match_score = Column(Float, default=0.0)
    distance_km = Column(Float, default=0.0)
    applied_at = Column(DateTime, default=datetime.datetime.utcnow)

    job = relationship("Job", back_populates="applications")
    worker = relationship("WorkerProfile", back_populates="applications")

class DirectOffer(Base):
    __tablename__ = "direct_offers"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("provider_profiles.id"), nullable=False)
    worker_id = Column(Integer, ForeignKey("worker_profiles.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    required_skill = Column(String, nullable=False)
    proposed_budget = Column(Float, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    scheduled_date = Column(String, nullable=True)
    status = Column(SQLEnum(DirectOfferStatus), default=DirectOfferStatus.PENDING)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    sent_at = Column(DateTime, default=datetime.datetime.utcnow)
    responded_at = Column(DateTime, nullable=True)

    provider = relationship("ProviderProfile", back_populates="direct_offers")
    worker = relationship("WorkerProfile", back_populates="direct_offers")

class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("job_id", "reviewer_id", name="uq_job_reviewer_rating"),
    )

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reviewee_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reviewer_role = Column(SQLEnum(UserRole), nullable=False)
    overall_rating = Column(Integer, nullable=False)
    rating = Column(Integer, nullable=False)  # Backward compatible alias for overall_rating
    category_ratings = Column(JSON, default=dict)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    job = relationship("Job", back_populates="reviews")

class TrustScoreLog(Base):
    __tablename__ = "trust_score_log"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("worker_profiles.id"), nullable=False)
    score = Column(Float, nullable=False)
    computed_at = Column(DateTime, default=datetime.datetime.utcnow)
    factors = Column(JSON, nullable=False)

    worker = relationship("WorkerProfile", back_populates="trust_logs")

class FraudFlag(Base):
    __tablename__ = "fraud_flags"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    anomaly_score = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(SQLEnum(FraudFlagStatus), default=FraudFlagStatus.OPEN)
    user = relationship("User", back_populates="fraud_flags")

class PendingRegistration(Base):
    __tablename__ = "pending_registrations"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    otp_hash = Column(String, nullable=False)
    otp_expires_at = Column(DateTime, nullable=False)
    registration_data = Column(JSON, nullable=False)  # Contains password_hash, full_name, role, phone, etc.
    attempts = Column(Integer, default=0, nullable=False)
    last_resend_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

