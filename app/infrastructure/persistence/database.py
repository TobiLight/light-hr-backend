#!usr/bin/env python3
# File: app/infrastructure/persistence/database.py
# Author: Oluwatobiloba Light Agunloye
"""LIGHT HRMS DATABASE -- SQLAlchemy engine/session lifecycle. Domain code must not
import this module."""

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


@lru_cache
def get_engine():
    settings = get_settings()
    return create_async_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        # echo emits SQL with bound parameters. On an HR system those literals
        # are names, emails, salaries and national IDs, so it is gated on the
        # environment as well as debug -- T4 already makes debug=True outside
        # dev a validation error, so this is belt-and-braces if that is ever
        # relaxed.
        echo=settings.debug and settings.app_env == "dev",
    )


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency. Transaction ownership belongs to the use case/UoW."""
    async with get_session_factory()() as session:
        yield session


async def dispose_database() -> None:
    """Dispose the connection pool during application shutdown."""
    if get_engine.cache_info().currsize:
        await get_engine().dispose()
        get_engine.cache_clear()
        get_session_factory.cache_clear()
