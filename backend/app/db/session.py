"""
Async SQLAlchemy setup — sessions, base model, init
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings
# Main engine (data + pipeline state)
engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
# Auth engine (separate DB for user credentials)
auth_engine = create_async_engine(settings.AUTH_DATABASE_URL, echo=False, future=True)
AuthSessionLocal = async_sessionmaker(auth_engine, expire_on_commit=False, class_=AsyncSession)
class Base(DeclarativeBase):
    pass
class AuthBase(DeclarativeBase):
    pass
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
async def get_auth_db() -> AsyncSession:
    async with AuthSessionLocal() as session:
        yield session
async def init_db():
    """Create all tables on startup."""
    from app.models import Dataset, Chart, ChunkEmbedding, PipelineRun  # noqa
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with auth_engine.begin() as conn:
        await conn.run_sync(AuthBase.metadata.create_all)
