import os
from collections.abc import AsyncIterator
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Load environment variables from .env file
load_dotenv()

# Retrieve database URL from environment or fallback to default asyncpg connection
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:postgres@relational_db:5432/postgres"
)

# Create high-performance asynchronous SQLAlchemy engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
)

# Create asynchronous session factory
async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncIterator[AsyncSession]:
    """Dependency that yields a database session and ensures proper cleanup/closure."""
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
