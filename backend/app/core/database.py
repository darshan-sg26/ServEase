from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
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
