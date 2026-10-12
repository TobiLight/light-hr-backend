"""SQL echo is gated on app_env (T8).

echo=True makes SQLAlchemy log every statement with its bound parameters.
On an HR system those literals are names, emails, salaries and national
IDs, so the setting must not be reachable from a non-development
environment.

T4 makes debug=True outside dev a validation error, so the combined
expression is defence in depth: if that validator is ever relaxed, this
still keeps SQL text out of the log sink.
"""

import app.infrastructure.persistence.database as database
import pytest
from app.core.config import get_settings
from pydantic import ValidationError


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
