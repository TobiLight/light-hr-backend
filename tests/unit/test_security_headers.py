"""Host validation, CORS allowlist and security headers (T6).

Host validation is not hypothetical: CVE-2026-48710 ("BadHost") let a
malformed Host header poison request.url.path and bypass path-based auth
checks. The installed Starlette is patched, but this project's posture
should not depend on that patch alone.
"""

import pytest
from app.bootstrap import SECURITY_HEADERS, create_app
from app.core.config import get_settings
from fastapi.testclient import TestClient

REQUIRED_HEADERS = (
    "strict-transport-security",
    "x-content-type-options",
    "x-frame-options",
    "referrer-policy",
    "permissions-policy",
)
CORS_HEADER = "access-control-allow-origin"


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    yield
    get_settings.cache_clear()


def _client(monkeypatch, app_env, **extra_env):
    for key, value in extra_env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("APP_ENV", app_env)
    get_settings.cache_clear()
    return TestClient(create_app())


def test_security_headers_on_every_response(monkeypatch):
    client = _client(monkeypatch, "dev")

    for path in ("/api/v1/health/live", "/does-not-exist"):
        response = client.get(path)
        for header in REQUIRED_HEADERS:
            assert header in response.headers, (path, header)
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["strict-transport-security"].startswith("max-age=")


def test_bad_host_rejected(monkeypatch):
    client = _client(monkeypatch, "dev", ALLOWED_HOSTS="api.example.com")

    response = client.get("/api/v1/health/live", headers={"Host": "evil.example.net"})

    assert response.status_code == 400


def test_allowed_host_accepted(monkeypatch):
    client = _client(monkeypatch, "dev", ALLOWED_HOSTS="api.example.com")

    response = client.get("/api/v1/health/live", headers={"Host": "api.example.com"})

    assert response.status_code == 200


def test_disallowed_origin_gets_no_cors_header(monkeypatch):
    client = _client(monkeypatch, "dev", CORS_ORIGINS="https://app.example.com")

    response = client.get(
        "/api/v1/health/live",
        headers={"Origin": "https://evil.example.net"},
    )

    assert CORS_HEADER not in response.headers


def test_allowed_origin_gets_cors_header(monkeypatch):
    client = _client(
        monkeypatch, "dev", CORS_ORIGINS="https://app.example.com,https://www.example.com"
    )

    response = client.get("/api/v1/health/live", headers={"Origin": "https://www.example.com"})

    assert response.headers[CORS_HEADER] == "https://www.example.com"


def test_production_rejects_empty_allowed_hosts(monkeypatch):
    monkeypatch.setenv("ALLOWED_HOSTS", "")
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()

    from app.core.config import Configs
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as exc_info:
        Configs()

    message = str(exc_info.value)
    assert "allowed_hosts" in message
    assert "app_env" in message


def test_no_wildcard_origin_default():
    assert "*" not in get_settings().cors_origins
    normalized = {name.lower(): value for name, value in SECURITY_HEADERS.items()}
    assert normalized["x-frame-options"] == "DENY"
