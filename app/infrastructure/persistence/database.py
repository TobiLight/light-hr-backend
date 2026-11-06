#!usr/bin/env python3
# File: app/infrastructure/persistence/database.py
# Author: Oluwatobiloba Light Agunloye
"""LIGHT HRMS DATABASE -- SQLAlchemy engine/session lifecycle. Domain code must not
import this module."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from functools import lru_cache
from weakref import WeakKeyDictionary

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

# Readiness must answer fast enough for an orchestrator's probe interval, and
# slow enough to cover a normal round trip to a database on the same host.
DB_PING_TIMEOUT_SECONDS = 2.0

# An orchestrator that restarts on a flapping probe can itself become the
# load, so one probe is shared across a short window. Two seconds is below the
# usual 5-10s probe cadence, so a genuine recovery is still picked up quickly.
DB_PING_CACHE_TTL_SECONDS = 2.0


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


@dataclass
class _PingResult:
    checked_at: float | None = None
    reachable: bool = False


_ping_result = _PingResult()

# Keyed by event loop because an asyncio.Lock binds to the loop that first
# awaits it and then refuses to be used from another one. The suite builds a
# fresh loop per test client, so a single module-level lock would raise
# "is bound to a different event loop" on the second test that probes.
_ping_locks: WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Lock] = WeakKeyDictionary()


def _ping_lock() -> asyncio.Lock:
    loop = asyncio.get_running_loop()
    lock = _ping_locks.get(loop)
    if lock is None:
        lock = _ping_locks[loop] = asyncio.Lock()
    return lock


async def _probe_database() -> bool:
    """Run one trivial round trip. Reports failure instead of raising.

    SQLAlchemy wraps asyncpg's connection errors, so an unreachable host, a
    missing database and a refused password all surface as SQLAlchemyError.
    Configuration errors are not caught here on purpose: create_app validates
    settings at boot, so a missing DATABASE_URL fails the deploy rather than
    turning into a permanently unready instance.
    """
    try:
        async with asyncio.timeout(DB_PING_TIMEOUT_SECONDS):
            async with get_engine().connect() as connection:
                await connection.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError, TimeoutError):
        return False
    return True


async def ping_database() -> bool:
    """True when the database answered a trivial query within the timeout.

    Cached for DB_PING_CACHE_TTL_SECONDS and single-flighted, so a burst of
    probes produces one query per window rather than one per request.
    """
    cached = _cached_ping()
    if cached is not None:
        return cached
    async with _ping_lock():
        # Another probe may have completed while this one waited for the lock.
        cached = _cached_ping()
        if cached is not None:
            return cached
        reachable = await _probe_database()
        _ping_result.reachable = reachable
        _ping_result.checked_at = time.monotonic()
        return reachable


def _cached_ping() -> bool | None:
    """The cached verdict, or None when the window has expired."""
    if _ping_result.checked_at is None:
        return None
    if time.monotonic() - _ping_result.checked_at >= DB_PING_CACHE_TTL_SECONDS:
        return None
    return _ping_result.reachable


def reset_database_ping_cache() -> None:
    """Force the next ping_database() call to query the database."""
    _ping_result.checked_at = None
    _ping_result.reachable = False
