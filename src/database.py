from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from fastapi import Request

# DATABASE_URL = f'postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'


class Base(DeclarativeBase):
    __table_args__ = {'extend_existing': True}


# engine = create_async_engine(DATABASE_URL)
# db_sessionmaker = async_sessionmaker(engine, expire_on_commit=False)


async def get_async_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    async_session_maker = request.app.state.db_sessionmaker
    async with async_session_maker() as session:
        yield session


