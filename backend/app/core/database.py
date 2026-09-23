from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import text
from app.core.config import settings

db_url = settings.ASYNC_DATABASE_URL
is_sqlite = db_url.startswith("sqlite")

connect_args = {}
engine_kwargs = {
    "echo": False,
    "future": True,
}

if is_sqlite:
    connect_args = {"check_same_thread": False}
else:
    # Disable asyncpg statement caching for PgBouncer transaction pooler (Neon) to prevent stalls & freezing
    connect_args = {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0
    }
    engine_kwargs.update({
        "pool_size": 20,
        "max_overflow": 10,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
    })

engine = create_async_engine(
    db_url,
    connect_args=connect_args,
    **engine_kwargs
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Safe schema migration for SQLite
        if is_sqlite:
            try:
                # reviews migrations
                res = await conn.execute(text("PRAGMA table_info(reviews);"))
                rev_cols = [row[1] for row in res.fetchall()]
                if rev_cols:
                    if "reviewer_role" not in rev_cols:
                        await conn.execute(text("ALTER TABLE reviews ADD COLUMN reviewer_role VARCHAR;"))
                    if "overall_rating" not in rev_cols:
                        await conn.execute(text("ALTER TABLE reviews ADD COLUMN overall_rating INTEGER;"))
                        await conn.execute(text("UPDATE reviews SET overall_rating = rating WHERE overall_rating IS NULL;"))
                    if "category_ratings" not in rev_cols:
                        await conn.execute(text("ALTER TABLE reviews ADD COLUMN category_ratings JSON;"))

                # worker_profiles migrations
                res = await conn.execute(text("PRAGMA table_info(worker_profiles);"))
                wp_cols = [row[1] for row in res.fetchall()]
                if wp_cols:
                    if "location_name" not in wp_cols:
                        await conn.execute(text("ALTER TABLE worker_profiles ADD COLUMN location_name VARCHAR;"))
                    if "location_updated_at" not in wp_cols:
                        await conn.execute(text("ALTER TABLE worker_profiles ADD COLUMN location_updated_at TIMESTAMP;"))

                # provider_profiles migrations
                res = await conn.execute(text("PRAGMA table_info(provider_profiles);"))
                pp_cols = [row[1] for row in res.fetchall()]
                if pp_cols:
                    if "location_name" not in pp_cols:
                        await conn.execute(text("ALTER TABLE provider_profiles ADD COLUMN location_name VARCHAR;"))

                # jobs migrations
                res = await conn.execute(text("PRAGMA table_info(jobs);"))
                job_cols = [row[1] for row in res.fetchall()]
                if job_cols:
                    if "search_radius_km" not in job_cols:
                        await conn.execute(text("ALTER TABLE jobs ADD COLUMN search_radius_km FLOAT DEFAULT 10.0;"))
                    if "location_name" not in job_cols:
                        await conn.execute(text("ALTER TABLE jobs ADD COLUMN location_name VARCHAR;"))

                # users migrations
                res = await conn.execute(text("PRAGMA table_info(users);"))
                user_cols = [row[1] for row in res.fetchall()]
                if user_cols:
                    if "google_id" not in user_cols:
                        await conn.execute(text("ALTER TABLE users ADD COLUMN google_id VARCHAR;"))
                    if "auth_provider" not in user_cols:
                        await conn.execute(text("ALTER TABLE users ADD COLUMN auth_provider VARCHAR DEFAULT 'email';"))

                # worker_skills migrations
                res = await conn.execute(text("PRAGMA table_info(worker_skills);"))
                ws_cols = [row[1] for row in res.fetchall()]
                if ws_cols:
                    if "status" not in ws_cols:
                        await conn.execute(text("ALTER TABLE worker_skills ADD COLUMN status VARCHAR DEFAULT 'pending';"))
                        # Preserve existing legacy skills as verified
                        await conn.execute(text("UPDATE worker_skills SET status = 'verified' WHERE status IS NULL OR status = 'pending';"))
                    if "submitted_at" not in ws_cols:
                        await conn.execute(text("ALTER TABLE worker_skills ADD COLUMN submitted_at TIMESTAMP;"))
                        await conn.execute(text("UPDATE worker_skills SET submitted_at = CURRENT_TIMESTAMP WHERE submitted_at IS NULL;"))
                    if "reviewed_at" not in ws_cols:
                        await conn.execute(text("ALTER TABLE worker_skills ADD COLUMN reviewed_at TIMESTAMP;"))
                    if "reviewed_by" not in ws_cols:
                        await conn.execute(text("ALTER TABLE worker_skills ADD COLUMN reviewed_by INTEGER REFERENCES users(id);"))
                    if "rejection_reason" not in ws_cols:
                        await conn.execute(text("ALTER TABLE worker_skills ADD COLUMN rejection_reason TEXT;"))
                    if "created_at" not in ws_cols:
                        await conn.execute(text("ALTER TABLE worker_skills ADD COLUMN created_at TIMESTAMP;"))
                        await conn.execute(text("UPDATE worker_skills SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL;"))
                    if "updated_at" not in ws_cols:
                        await conn.execute(text("ALTER TABLE worker_skills ADD COLUMN updated_at TIMESTAMP;"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_worker_skills_status ON worker_skills(status);"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_worker_skills_worker_id ON worker_skills(worker_id);"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_worker_skills_reviewed_by ON worker_skills(reviewed_by);"))
            except Exception:
                pass
        else:
            # PostgreSQL safe migrations
            try:
                await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id VARCHAR;"))
                await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_provider VARCHAR DEFAULT 'email';"))
                await conn.execute(text("ALTER TABLE worker_profiles ADD COLUMN IF NOT EXISTS location_name VARCHAR;"))
                await conn.execute(text("ALTER TABLE worker_profiles ADD COLUMN IF NOT EXISTS location_updated_at TIMESTAMP;"))
                await conn.execute(text("ALTER TABLE provider_profiles ADD COLUMN IF NOT EXISTS location_name VARCHAR;"))
                await conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS search_radius_km FLOAT DEFAULT 10.0;"))
                await conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS location_name VARCHAR;"))
                # worker_skills migrations
                await conn.execute(text("ALTER TABLE worker_skills ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'pending';"))
                await conn.execute(text("UPDATE worker_skills SET status = 'verified' WHERE status IS NULL;"))
                await conn.execute(text("ALTER TABLE worker_skills ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"))
                await conn.execute(text("ALTER TABLE worker_skills ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP;"))
                await conn.execute(text("ALTER TABLE worker_skills ADD COLUMN IF NOT EXISTS reviewed_by INTEGER REFERENCES users(id);"))
                await conn.execute(text("ALTER TABLE worker_skills ADD COLUMN IF NOT EXISTS rejection_reason TEXT;"))
                await conn.execute(text("ALTER TABLE worker_skills ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"))
                await conn.execute(text("ALTER TABLE worker_skills ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_worker_skills_status ON worker_skills(status);"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_worker_skills_worker_id ON worker_skills(worker_id);"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_worker_skills_reviewed_by ON worker_skills(reviewed_by);"))
            except Exception:
                pass
