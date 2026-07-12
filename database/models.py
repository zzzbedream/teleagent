import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def normalize_async_db_url(url: str) -> str:
    """Normaliza la URL de Postgres al driver async (asyncpg).

    Railway/Heroku entregan `postgres://` o `postgresql://`; SQLAlchemy async
    necesita `postgresql+asyncpg://`. Si ya viene con un driver, no la toca.
    """
    if not url:
        return url
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    return url


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    discord_id = Column(String, unique=True, index=True, nullable=False)
    wallet_address = Column(String, unique=True, index=True, nullable=False)
    # Saldo en wei. Numeric(78, 0) cubre el rango completo de uint256 (1 AVAX = 10^18 wei).
    api_credits = Column(Numeric(precision=78, scale=0), default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

async def init_db(database_url: str):
    engine = create_async_engine(normalize_async_db_url(database_url), echo=False)
    async_session = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    async with engine.begin() as conn:
        # Create all tables in the database.
        await conn.run_sync(Base.metadata.create_all)
    
    return engine, async_session
