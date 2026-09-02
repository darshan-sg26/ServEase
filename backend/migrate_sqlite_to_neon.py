import asyncio
import json
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.database import Base
from app.models.domain import (
    User, WorkerProfile, ProviderProfile, WorkerSkill,
    Job, JobApplication, DirectOffer, Review,
    TrustScoreLog, FraudFlag,
    UserRole, AvailabilityStatus, VerificationStatus,
    JobUrgency, JobSource, JobStatus,
    ApplicationStatus, DirectOfferStatus, FraudFlagStatus
)

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise ValueError("DATABASE_URL not found in .env")

if db_url.startswith("postgres://"):
    async_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+asyncpg://"):
    async_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    async_url = db_url

if "sslmode=" in async_url:
    async_url = async_url.replace("sslmode=", "ssl=")
if "channel_binding=" in async_url:
    async_url = re.sub(r'[&?]channel_binding=[^&]+', '', async_url)

sqlite_db_path = Path(__file__).resolve().parent / "servease.db"

def parse_dt(val):
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    try:
        # Handles "2026-09-01 12:34:56.789000" or ISO
        return datetime.fromisoformat(str(val))
    except Exception:
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(str(val), fmt)
            except ValueError:
                pass
        return None

def parse_json(val, default):
    if val is None:
        return default
    if isinstance(val, (dict, list)):
        return val
    try:
        return json.loads(val)
    except Exception:
        return default

def parse_bool(val):
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    return str(val).lower() in ("true", "1", "yes")

def map_enum(enum_cls, val, default=None):
    if val is None:
        return default.name if default else None
    if isinstance(val, enum_cls):
        return val.name
    val_str = str(val).strip()
    for member in enum_cls:
        if member.value.lower() == val_str.lower() or member.name.lower() == val_str.lower():
            return member.name
    return default.name if default else val_str.upper()

async def run_migration():
    print("=" * 70)
    print("SERVEASE SQLITE -> NEON POSTGRESQL FULL MIGRATION ENGINE")
    print("=" * 70)
    print(f"Source SQLite: {sqlite_db_path}")
    print(f"Target Neon DB: {async_url.split('@')[-1] if '@' in async_url else async_url}\n")

    if not sqlite_db_path.exists():
        raise FileNotFoundError(f"Source SQLite database not found at {sqlite_db_path}")

    # Step 1: Connect to SQLite and fetch all tables data
    sqlite_conn = sqlite3.connect(str(sqlite_db_path))
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    tables_order = [
        "users",
        "worker_profiles",
        "provider_profiles",
        "worker_skills",
        "jobs",
        "job_applications",
        "direct_offers",
        "reviews",
        "trust_score_log",
        "fraud_flags"
    ]

    sqlite_data = {}
    sqlite_counts = {}
    for table in tables_order:
        sqlite_cur.execute(f'SELECT * FROM "{table}" ORDER BY id ASC')
        rows = [dict(r) for r in sqlite_cur.fetchall()]
        sqlite_data[table] = rows
        sqlite_counts[table] = len(rows)
        print(f"[SQLite Source] Table '{table}': {len(rows)} records found.", flush=True)

    sqlite_conn.close()

    total_source_records = sum(sqlite_counts.values())
    print(f"\nTotal Source Records to Migrate: {total_source_records}\n", flush=True)

    # Step 2: Connect to Neon PostgreSQL
    engine = create_async_engine(
        async_url,
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0
        },
        pool_pre_ping=True
    )

    async with engine.begin() as conn:
        print("[Neon Step 1] Cleaning up existing tables for pristine 1:1 migration...", flush=True)
        await conn.execute(text("""
            DO $$ DECLARE
                r RECORD;
            BEGIN
                FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                    EXECUTE 'DROP TABLE IF EXISTS "' || r.tablename || '" CASCADE';
                END LOOP;
            END $$;
        """))
        print("[Neon Step 1] Existing tables cleared.", flush=True)

        print("[Neon Step 2] Creating all PostgreSQL tables, constraints, enums, indexes...", flush=True)
        await conn.run_sync(Base.metadata.create_all)

        # Ensure additional tables from migrate.py exist
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS conversations (
                id VARCHAR PRIMARY KEY,
                job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS conversation_members (
                conversation_id VARCHAR REFERENCES conversations(id) ON DELETE CASCADE,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (conversation_id, user_id)
            );
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id VARCHAR PRIMARY KEY,
                conversation_id VARCHAR REFERENCES conversations(id) ON DELETE CASCADE,
                sender_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                content TEXT NOT NULL,
                message_type VARCHAR DEFAULT 'text',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                read_at TIMESTAMP NULL
            );
        """))
        print("[Neon Step 2] Schema creation complete.", flush=True)

        print("\n[Neon Step 3] Transferring records in strict foreign-key dependency order...", flush=True)

        # 1. users
        for r in sqlite_data["users"]:
            await conn.execute(
                text("""
                    INSERT INTO users (id, email, phone, password_hash, role, is_verified, created_at, updated_at)
                    VALUES (:id, :email, :phone, :password_hash, :role, :is_verified, :created_at, :updated_at)
                """),
                {
                    "id": r["id"],
                    "email": r["email"],
                    "phone": r.get("phone"),
                    "password_hash": r["password_hash"],
                    "role": map_enum(UserRole, r["role"], UserRole.WORKER),
                    "is_verified": parse_bool(r.get("is_verified")),
                    "created_at": parse_dt(r.get("created_at")),
                    "updated_at": parse_dt(r.get("updated_at")),
                }
            )
        print(f" -> Migrated {len(sqlite_data['users'])} records to 'users'.", flush=True)

        # 2. worker_profiles
        for r in sqlite_data["worker_profiles"]:
            await conn.execute(
                text("""
                    INSERT INTO worker_profiles (
                        id, user_id, full_name, bio, gender, phone, profile_photo_url,
                        latitude, longitude, service_radius_km, hourly_rate,
                        completed_jobs_count, languages_spoken, availability_status,
                        trust_score, verification_status, created_at, updated_at
                    ) VALUES (
                        :id, :user_id, :full_name, :bio, :gender, :phone, :profile_photo_url,
                        :latitude, :longitude, :service_radius_km, :hourly_rate,
                        :completed_jobs_count, :languages_spoken, :availability_status,
                        :trust_score, :verification_status, :created_at, :updated_at
                    )
                """),
                {
                    "id": r["id"],
                    "user_id": r["user_id"],
                    "full_name": r["full_name"],
                    "bio": r.get("bio"),
                    "gender": r.get("gender") or "prefer_not_to_say",
                    "phone": r.get("phone"),
                    "profile_photo_url": r.get("profile_photo_url"),
                    "latitude": float(r["latitude"]),
                    "longitude": float(r["longitude"]),
                    "service_radius_km": float(r["service_radius_km"]),
                    "hourly_rate": float(r["hourly_rate"]) if r.get("hourly_rate") is not None else 350.0,
                    "completed_jobs_count": int(r.get("completed_jobs_count") or 0),
                    "languages_spoken": json.dumps(parse_json(r.get("languages_spoken"), ["English", "Kannada", "Hindi"])),
                    "availability_status": map_enum(AvailabilityStatus, r.get("availability_status"), AvailabilityStatus.AVAILABLE),
                    "trust_score": float(r["trust_score"]) if r.get("trust_score") is not None else 30.5,
                    "verification_status": map_enum(VerificationStatus, r.get("verification_status"), VerificationStatus.UNVERIFIED),
                    "created_at": parse_dt(r.get("created_at")),
                    "updated_at": parse_dt(r.get("updated_at")),
                }
            )
        print(f" -> Migrated {len(sqlite_data['worker_profiles'])} records to 'worker_profiles'.", flush=True)

        # 3. provider_profiles
        for r in sqlite_data["provider_profiles"]:
            await conn.execute(
                text("""
                    INSERT INTO provider_profiles (
                        id, user_id, full_name, phone, profile_photo_url,
                        default_latitude, default_longitude, created_at, updated_at
                    ) VALUES (
                        :id, :user_id, :full_name, :phone, :profile_photo_url,
                        :default_latitude, :default_longitude, :created_at, :updated_at
                    )
                """),
                {
                    "id": r["id"],
                    "user_id": r["user_id"],
                    "full_name": r["full_name"],
                    "phone": r.get("phone"),
                    "profile_photo_url": r.get("profile_photo_url"),
                    "default_latitude": float(r["default_latitude"]) if r.get("default_latitude") is not None else 12.9716,
                    "default_longitude": float(r["default_longitude"]) if r.get("default_longitude") is not None else 77.5946,
                    "created_at": parse_dt(r.get("created_at")),
                    "updated_at": parse_dt(r.get("updated_at")),
                }
            )
        print(f" -> Migrated {len(sqlite_data['provider_profiles'])} records to 'provider_profiles'.", flush=True)

        # 4. worker_skills
        for r in sqlite_data["worker_skills"]:
            await conn.execute(
                text("""
                    INSERT INTO worker_skills (
                        id, worker_id, skill_name, years_experience, hourly_rate, skill_tags
                    ) VALUES (
                        :id, :worker_id, :skill_name, :years_experience, :hourly_rate, :skill_tags
                    )
                """),
                {
                    "id": r["id"],
                    "worker_id": r["worker_id"],
                    "skill_name": r["skill_name"],
                    "years_experience": float(r.get("years_experience") or 1.0),
                    "hourly_rate": float(r.get("hourly_rate") or 300.0),
                    "skill_tags": json.dumps(parse_json(r.get("skill_tags"), [])),
                }
            )
        print(f" -> Migrated {len(sqlite_data['worker_skills'])} records to 'worker_skills'.", flush=True)

        # 5. jobs
        for r in sqlite_data["jobs"]:
            await conn.execute(
                text("""
                    INSERT INTO jobs (
                        id, provider_id, worker_id, title, description, required_skill,
                        workers_needed, budget_min, budget_max, latitude, longitude,
                        urgency, scheduled_date, source, status, provider_completed,
                        worker_completed, started_at, completed_at, created_at, updated_at
                    ) VALUES (
                        :id, :provider_id, :worker_id, :title, :description, :required_skill,
                        :workers_needed, :budget_min, :budget_max, :latitude, :longitude,
                        :urgency, :scheduled_date, :source, :status, :provider_completed,
                        :worker_completed, :started_at, :completed_at, :created_at, :updated_at
                    )
                """),
                {
                    "id": r["id"],
                    "provider_id": r["provider_id"],
                    "worker_id": r.get("worker_id"),
                    "title": r["title"],
                    "description": r["description"],
                    "required_skill": r["required_skill"],
                    "workers_needed": int(r.get("workers_needed") or 1),
                    "budget_min": float(r["budget_min"]),
                    "budget_max": float(r["budget_max"]),
                    "latitude": float(r["latitude"]),
                    "longitude": float(r["longitude"]),
                    "urgency": map_enum(JobUrgency, r.get("urgency"), JobUrgency.IMMEDIATE),
                    "scheduled_date": r.get("scheduled_date"),
                    "source": map_enum(JobSource, r.get("source"), JobSource.POSTED),
                    "status": map_enum(JobStatus, r.get("status"), JobStatus.OPEN),
                    "provider_completed": parse_bool(r.get("provider_completed")),
                    "worker_completed": parse_bool(r.get("worker_completed")),
                    "started_at": parse_dt(r.get("started_at")),
                    "completed_at": parse_dt(r.get("completed_at")),
                    "created_at": parse_dt(r.get("created_at")),
                    "updated_at": parse_dt(r.get("updated_at")),
                }
            )
        print(f" -> Migrated {len(sqlite_data['jobs'])} records to 'jobs'.", flush=True)

        # 6. job_applications
        for r in sqlite_data["job_applications"]:
            await conn.execute(
                text("""
                    INSERT INTO job_applications (
                        id, job_id, worker_id, status, match_score, distance_km, applied_at
                    ) VALUES (
                        :id, :job_id, :worker_id, :status, :match_score, :distance_km, :applied_at
                    )
                """),
                {
                    "id": r["id"],
                    "job_id": r["job_id"],
                    "worker_id": r["worker_id"],
                    "status": map_enum(ApplicationStatus, r.get("status"), ApplicationStatus.APPLIED),
                    "match_score": float(r.get("match_score") or 0.0),
                    "distance_km": float(r.get("distance_km") or 0.0),
                    "applied_at": parse_dt(r.get("applied_at")),
                }
            )
        print(f" -> Migrated {len(sqlite_data['job_applications'])} records to 'job_applications'.", flush=True)

        # 7. direct_offers
        for r in sqlite_data["direct_offers"]:
            await conn.execute(
                text("""
                    INSERT INTO direct_offers (
                        id, provider_id, worker_id, title, description, required_skill,
                        proposed_budget, latitude, longitude, scheduled_date, status,
                        job_id, sent_at, responded_at
                    ) VALUES (
                        :id, :provider_id, :worker_id, :title, :description, :required_skill,
                        :proposed_budget, :latitude, :longitude, :scheduled_date, :status,
                        :job_id, :sent_at, :responded_at
                    )
                """),
                {
                    "id": r["id"],
                    "provider_id": r["provider_id"],
                    "worker_id": r["worker_id"],
                    "title": r["title"],
                    "description": r["description"],
                    "required_skill": r["required_skill"],
                    "proposed_budget": float(r["proposed_budget"]),
                    "latitude": float(r["latitude"]),
                    "longitude": float(r["longitude"]),
                    "scheduled_date": r.get("scheduled_date"),
                    "status": map_enum(DirectOfferStatus, r.get("status"), DirectOfferStatus.PENDING),
                    "job_id": r.get("job_id"),
                    "sent_at": parse_dt(r.get("sent_at")),
                    "responded_at": parse_dt(r.get("responded_at")),
                }
            )
        print(f" -> Migrated {len(sqlite_data['direct_offers'])} records to 'direct_offers'.", flush=True)

        # 8. reviews
        for r in sqlite_data["reviews"]:
            overall = r.get("overall_rating") if r.get("overall_rating") is not None else r.get("rating", 5)
            rating_val = r.get("rating") if r.get("rating") is not None else overall
            cat_ratings = parse_json(r.get("category_ratings"), {})
            await conn.execute(
                text("""
                    INSERT INTO reviews (
                        id, job_id, reviewer_id, reviewee_id, reviewer_role,
                        overall_rating, rating, category_ratings, comment, created_at
                    ) VALUES (
                        :id, :job_id, :reviewer_id, :reviewee_id, :reviewer_role,
                        :overall_rating, :rating, :category_ratings, :comment, :created_at
                    )
                """),
                {
                    "id": r["id"],
                    "job_id": r["job_id"],
                    "reviewer_id": r["reviewer_id"],
                    "reviewee_id": r["reviewee_id"],
                    "reviewer_role": map_enum(UserRole, r.get("reviewer_role"), UserRole.WORKER),
                    "overall_rating": int(overall),
                    "rating": int(rating_val),
                    "category_ratings": json.dumps(cat_ratings),
                    "comment": r.get("comment"),
                    "created_at": parse_dt(r.get("created_at")),
                }
            )
        print(f" -> Migrated {len(sqlite_data['reviews'])} records to 'reviews'.", flush=True)

        # 9. trust_score_log
        for r in sqlite_data["trust_score_log"]:
            factors_val = parse_json(r.get("factors"), {})
            await conn.execute(
                text("""
                    INSERT INTO trust_score_log (
                        id, worker_id, score, computed_at, factors
                    ) VALUES (
                        :id, :worker_id, :score, :computed_at, :factors
                    )
                """),
                {
                    "id": r["id"],
                    "worker_id": r["worker_id"],
                    "score": float(r["score"]),
                    "computed_at": parse_dt(r.get("computed_at")),
                    "factors": json.dumps(factors_val),
                }
            )
        print(f" -> Migrated {len(sqlite_data['trust_score_log'])} records to 'trust_score_log'.", flush=True)

        # 10. fraud_flags
        for r in sqlite_data["fraud_flags"]:
            await conn.execute(
                text("""
                    INSERT INTO fraud_flags (
                        id, user_id, anomaly_score, reason, status, flagged_at
                    ) VALUES (
                        :id, :user_id, :anomaly_score, :reason, :status, :flagged_at
                    )
                """),
                {
                    "id": r["id"],
                    "user_id": r["user_id"],
                    "anomaly_score": float(r["anomaly_score"]),
                    "reason": r["reason"],
                    "status": map_enum(FraudFlagStatus, r.get("status"), FraudFlagStatus.OPEN),
                    "flagged_at": parse_dt(r.get("flagged_at")),
                }
            )
        print(f" -> Migrated {len(sqlite_data['fraud_flags'])} records to 'fraud_flags'.", flush=True)

        print("\n[Neon Step 4] Synchronizing PostgreSQL serial sequences for all primary keys...", flush=True)
        for table in tables_order:
            await conn.execute(text(f"""
                SELECT setval(
                    pg_get_serial_sequence('{table}', 'id'),
                    COALESCE((SELECT MAX(id) FROM "{table}"), 1)
                );
            """))
            print(f" -> Sequence for '{table}.id' synced to MAX(id).", flush=True)

        print("\n[Neon Step 5] Running row-count audit against SQLite source...", flush=True)
        audit_success = True
        for table in tables_order:
            res = await conn.execute(text(f'SELECT COUNT(*) FROM "{table}";'))
            pg_count = res.scalar()
            sq_count = sqlite_counts[table]
            match = (pg_count == sq_count)
            status = "[MATCH]" if match else "[MISMATCH]"
            print(f" {status} Table '{table}': SQLite={sq_count} vs Neon PostgreSQL={pg_count}", flush=True)
            if not match:
                audit_success = False

        if not audit_success:
            raise RuntimeError("Row count audit failed! One or more tables do not match SQLite source.")

        print("\n" + "=" * 70, flush=True)
        print("MIGRATION COMPLETED SUCCESSFULLY WITH 100% AUDIT MATCH!", flush=True)
        print("=" * 70, flush=True)

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_migration())
