from collections.abc import AsyncGenerator
from contextvars import ContextVar

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=not settings.is_production,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


# Holds the current tenant schema slug for the request lifecycle
current_tenant_slug: ContextVar[str | None] = ContextVar("current_tenant_slug", default=None)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency: yields an AsyncSession scoped to the current tenant's schema."""
    async with AsyncSessionLocal() as session:
        tenant = current_tenant_slug.get()
        if tenant:
            await session.execute(text(f"SET search_path TO {tenant}, public"))
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            # Reset search_path to default (important for connection pool reuse)
            await session.execute(text("SET search_path TO public"))


async def check_db_connection() -> bool:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
