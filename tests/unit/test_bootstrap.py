"""API documentation is gated on app_env (T5).

The schema is a complete map of the authorization surface, so it is not
served from production. Each case rebuilds the app under a different
APP_ENV, which requires clearing the settings cache -- it is the reason
this file exists rather than a single parametrized assertion.
"""

import pytest
from app.bootstrap import create_app
from app.core.config import get_settings
from fastapi.testclient import TestClient

DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")
NON_PRODUCTION = ("dev", "test", "staging")


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    """Keep this module from leaking a cached settings snapshot into others."""
    yield
    get_settings.cache_clear()


def _client(monkeypatch, app_env):
    monkeypatch.setenv("APP_ENV", app_env)
    get_settings.cache_clear()
    return TestClient(create_app())


@pytest.mark.parametrize("app_env", NON_PRODUCTION)
def test_docs_reachable_outside_production(monkeypatch, app_env):
    client = _client(monkeypatch, app_env)

    for path in DOCS_PATHS:
        response = client.get(path)
        assert response.status_code == 200, path


def test_docs_unreachable_in_production(monkeypatch):
    client = _client(monkeypatch, "production")

    for path in DOCS_PATHS:
        response = client.get(path)
        assert response.status_code == 404, path
