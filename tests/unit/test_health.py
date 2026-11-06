"""Liveness and readiness (T14).

Readiness used to return {"status": "ok"} unconditionally, so an orchestrator
routed traffic to instances that could not reach the database. These tests pin
the behaviour the plan requires: readiness queries the database and answers 503
when it is unreachable, the verdict is cached so a probe storm cannot become a
connection storm, and liveness stays free of dependencies so a database outage
never gets the process killed and restarted.
"""

import contextlib

import app.infrastructure.persistence.database as database
import pytest
from app.bootstrap import create_app
from app.core.config import get_settings
from app.infrastructure.persistence.database import (
    get_session_factory,
    ping_database,
    reset_database_ping_cache,
)
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _clear_ping_cache():
    """The verdict is module state; one test must not decide the next.

    The settings and engine caches go with it: a test that points DATABASE_URL
    at a dead port would otherwise keep using the engine built for the previous
    DSN and answer 200.
    """
    reset_database_ping_cache()
    yield
    reset_database_ping_cache()
    get_settings.cache_clear()
    database.get_engine.cache_clear()
    get_session_factory.cache_clear()


@contextlib.contextmanager
def _client(database_reachable: bool):
    app = create_app()
    app.dependency_overrides[ping_database] = lambda: database_reachable
    with TestClient(app) as client:
        yield client


@pytest.fixture
def counting_probe(monkeypatch):
    """Replace the round trip with a counter. No database is contacted."""
    calls = []

    async def fake_probe() -> bool:
        calls.append(1)
        return True

    monkeypatch.setattr(database, "_probe_database", fake_probe)
    return calls


def test_liveness_endpoint(client):
    response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_liveness_never_queries_db(counting_probe):
    with TestClient(create_app()) as test_client:
        response = test_client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert counting_probe == []


def test_readiness_ok_when_db_up():
    with _client(True) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_503_when_db_down():
    with _client(False) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "unavailable"}


def test_readiness_503_does_not_disclose_the_dsn(monkeypatch):
    """Readiness is unauthenticated, so the body must not carry the DSN."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://app:sup3r-s3cret@localhost:5432/app")
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert "sup3r-s3cret" not in response.text
    assert "postgresql" not in response.text


async def test_readiness_does_not_query_db_twice_within_cache_window(counting_probe):
    assert await ping_database() is True
    assert await ping_database() is True

    assert len(counting_probe) == 1


async def test_readiness_queries_again_once_the_window_expires(counting_probe):
    assert await ping_database() is True

    reset_database_ping_cache()

    assert await ping_database() is True
    assert len(counting_probe) == 2


async def test_concurrent_probes_share_one_query(counting_probe):
    """Single-flight: a cold cache under concurrency must not fan out."""
    import asyncio

    results = await asyncio.gather(*(ping_database() for _ in range(10)))

    assert all(results)
    assert len(counting_probe) == 1


async def test_readiness_503_through_the_real_code_path(monkeypatch):
    """No mock: a closed port must make the endpoint answer 503.

    Proves the endpoint fails on a real connection error rather than only on an
    injected verdict. Port 1 refuses immediately, so this stays fast.
    """
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://app:app@127.0.0.1:1/app")
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
