"""SQL echo is gated on app_env (T8).

echo=True makes SQLAlchemy log every statement with its bound parameters.
On an HR system those literals are names, emails, salaries and national
IDs, so the setting must not be reachable from a non-development
environment.

T4 makes debug=True outside dev a validation error, so the combined
expression is defence in depth: if that validator is ever relaxed, this
still keeps SQL text out of the log sink.

The lower half covers the readiness probe (T14). The integration test proves
the probe against a real server, but it skips in CI, so the reachable and
expired-cache branches are pinned here with a fake engine.
"""

import asyncio

import app.infrastructure.persistence.database as database
import pytest
from app.core.config import get_settings
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError


@pytest.fixture
def factory(monkeypatch):
    """Capture the kwargs get_engine() passes to create_async_engine.

    The engine is never constructed, so no connection is attempted. A non-null
    returned object is enough to satisfy get_engine's @lru_cache.
    """
    captured = {}

    def fake_engine(url, **kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(database, "create_async_engine", fake_engine)
    return captured


@pytest.fixture(autouse=True)
def _reset_caches():
    yield
    get_settings.cache_clear()
    database.get_engine.cache_clear()


def _build_engine(factory):
    database.get_engine.cache_clear()
    try:
        database.get_engine()
    finally:
        database.get_engine.cache_clear()
    return factory["echo"]


@pytest.mark.parametrize("env", ["dev", "test", "staging", "production"])
def test_echo_enabled_only_for_dev(monkeypatch, factory, env):
    monkeypatch.setenv("APP_ENV", env)
    monkeypatch.setenv("DEBUG", "true" if env == "dev" else "false")

    assert _build_engine(factory) is (env == "dev")


@pytest.mark.parametrize("env", ["dev", "test", "staging", "production"])
def test_echo_false_when_debug_off(monkeypatch, factory, env):
    monkeypatch.setenv("APP_ENV", env)
    monkeypatch.setenv("DEBUG", "false")

    assert _build_engine(factory) is False


def test_debug_true_outside_dev_never_reaches_the_engine(monkeypatch, factory):
    """T4's control: debug on in staging is refused before any engine exists."""
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("DEBUG", "true")

    with pytest.raises(ValidationError):
        _build_engine(factory)


class _FakeConnection:
    """Stands in for an async connection, recording the statements it is given."""

    def __init__(self, error: Exception | None = None) -> None:
        self.statements: list[str] = []
        self._error = error

    async def __aenter__(self) -> "_FakeConnection":
        return self

    async def __aexit__(self, *_exc_info) -> bool:
        return False

    async def execute(self, statement) -> None:
        self.statements.append(str(statement))
        if self._error is not None:
            raise self._error


class _FakeEngine:
    def __init__(self, connection: _FakeConnection) -> None:
        self._connection = connection

    def connect(self) -> _FakeConnection:
        return self._connection


@pytest.fixture
def ping(monkeypatch):
    """Point the probe at a fake engine and hand back the connection spy."""
    connection = _FakeConnection()
    monkeypatch.setattr(database, "get_engine", lambda: _FakeEngine(connection))
    database.reset_database_ping_cache()
    yield connection
    database.reset_database_ping_cache()


async def test_probe_runs_select_one_when_the_database_answers(ping):
    assert await database.ping_database() is True
    assert ping.statements == ["SELECT 1"]


async def test_probe_reports_failure_instead_of_raising(monkeypatch):
    """SQLAlchemy wraps asyncpg's errors, so OperationalError is the shape seen."""
    connection = _FakeConnection(error=OperationalError("SELECT 1", {}, Exception("refused")))
    monkeypatch.setattr(database, "get_engine", lambda: _FakeEngine(connection))
    database.reset_database_ping_cache()

    assert await database.ping_database() is False


async def test_probe_reruns_once_the_cache_window_has_passed(ping, monkeypatch):
    assert await database.ping_database() is True
    assert len(ping.statements) == 1

    # A zero-length window expires the cached verdict on the next call.
    monkeypatch.setattr(database, "DB_PING_CACHE_TTL_SECONDS", 0.0)

    assert await database.ping_database() is True
    assert len(ping.statements) == 2


async def test_concurrent_probes_share_one_query_across_the_lock(ping, monkeypatch):
    """Waiters that queued on the lock reuse the verdict, not the query.

    The probe suspends once so the other callers pile up behind the lock; a
    probe that returned immediately would let each one hit the cache check at
    the top and never reach the re-check inside the lock.
    """
    calls = []

    async def slow_probe() -> bool:
        calls.append(1)
        await asyncio.sleep(0)
        return True

    monkeypatch.setattr(database, "_probe_database", slow_probe)

    results = await asyncio.gather(*(database.ping_database() for _ in range(5)))

    assert all(results)
    assert len(calls) == 1
