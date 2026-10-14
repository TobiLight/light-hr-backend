"""Readiness against a real PostgreSQL (T14).

The unit tests inject the verdict, so they cannot prove the probe really
reaches a server. These do, and they skip unless TEST_DATABASE_URL is set, so
CI stays green without a database:

    docker compose up -d --wait db
    TEST_DATABASE_URL=postgresql+asyncpg://app:app@localhost:5432/light_hrms_db \
        uv run pytest tests/integration
"""

import os

import app.infrastructure.persistence.database as database
import pytest
from app.bootstrap import create_app
from app.core.config import get_settings
from app.infrastructure.persistence.database import (
    get_session_factory,
    reset_database_ping_cache,
)
from fastapi.testclient import TestClient

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL is unset; start the database with `docker compose up -d db`.",
)


@pytest.fixture(autouse=True)
def _isolate():
    reset_database_ping_cache()
    get_settings.cache_clear()
    database.get_engine.cache_clear()
    get_session_factory.cache_clear()
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    yield
    reset_database_ping_cache()
    get_settings.cache_clear()
    database.get_engine.cache_clear()
    get_session_factory.cache_clear()
    os.environ.pop("DATABASE_URL", None)


def test_readiness_ok_against_a_real_database():
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_ping_reaches_the_database_without_a_mock():
    from app.infrastructure.persistence.database import ping_database

    assert await ping_database() is True


async def test_ping_is_false_when_the_database_goes_away(monkeypatch):
    """Stop trusting the cache and answer with a dead port instead."""
    reset_database_ping_cache()
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://app:app@127.0.0.1:1/app")
    get_settings.cache_clear()
    database.get_engine.cache_clear()
    get_session_factory.cache_clear()

    from app.infrastructure.persistence.database import ping_database

    assert await ping_database() is False
