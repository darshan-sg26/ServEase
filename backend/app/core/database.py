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
                res = await conn.execute(text("PRAGMA table_info(reviews);"))
                existing_cols = [row[1] for row in res.fetchall()]
                if existing_cols:
                    if "reviewer_role" not in existing_cols:
                        await conn.execute(text("ALTER TABLE reviews ADD COLUMN reviewer_role VARCHAR;"))
                    if "overall_rating" not in existing_cols:
                        await conn.execute(text("ALTER TABLE reviews ADD COLUMN overall_rating INTEGER;"))
                        await conn.execute(text("UPDATE reviews SET overall_rating = rating WHERE overall_rating IS NULL;"))
                    if "category_ratings" not in existing_cols:
                        await conn.execute(text("ALTER TABLE reviews ADD COLUMN category_ratings JSON;"))
            except Exception:
                pass
