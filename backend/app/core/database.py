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
            except Exception:
                pass
        else:
            # PostgreSQL safe migrations
            try:
                await conn.execute(text("ALTER TABLE worker_profiles ADD COLUMN IF NOT EXISTS location_name VARCHAR;"))
                await conn.execute(text("ALTER TABLE worker_profiles ADD COLUMN IF NOT EXISTS location_updated_at TIMESTAMP;"))
                await conn.execute(text("ALTER TABLE provider_profiles ADD COLUMN IF NOT EXISTS location_name VARCHAR;"))
                await conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS search_radius_km FLOAT DEFAULT 10.0;"))
                await conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS location_name VARCHAR;"))
            except Exception:
                pass
