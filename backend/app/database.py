"""Database configuration and session management."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from .config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    # Import all models to ensure they are registered with Base.metadata
    from .models import User, QueryLog, ChatSession  # noqa: F401
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        # Ignore errors from concurrent workers trying to create tables
        print(f"init_db warning (safe to ignore if tables exist): {e}")


async def close_db():
    await engine.dispose()
