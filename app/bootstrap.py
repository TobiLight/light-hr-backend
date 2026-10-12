#!/usr/bin/env python3
# File: app/core/bootstrap.py
# Author: Oluwatobiloba Light Agunloye
"""LIGHT HRMS APP BOOTSTRAP"""

from collections.abc import AsyncIterator, Mapping

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.infrastructure.persistence.database import dispose_database
from app.presentation.http.api import api_router

# Applied to every response, including the error paths produced by the other
# middleware below. HSTS is safe to send unconditionally: a browser only
# enforces it on HTTPS origins, and a plain-HTTP deployment ignores it.
SECURITY_HEADERS: Mapping[str, str] = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


class SecurityHeadersMiddleware:
    """Pure ASGI middleware that stamps SECURITY_HEADERS onto each response."""

    def __init__(self, app: ASGIApp, headers: Mapping[str, str]) -> None:
        self.app = app
        self.headers = headers

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                # Lowercase names: HTTP/2 requires them, and it keeps the
                # emitted bytes identical to what the test client reports.
                # The list is mutated in place; setdefault covers a response
                # that starts with no headers at all.
                headers: list[tuple[bytes, bytes]] = message.setdefault("headers", [])
                for name, value in self.headers.items():
                    headers.append((name.lower().encode("latin-1"), value.encode("latin-1")))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__)

    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info("Application Starting", environment=settings.app_env)
        try:
            yield
        finally:
            await dispose_database()
            logger.info("Application Stopped")

    gated = settings.app_env == "production"
    application = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url=None if gated else "/docs",
        redoc_url=None if gated else "/redoc",
        openapi_url=None if gated else "/openapi.json",
    )
    application.include_router(api_router, prefix=settings.api_v1_prefix)

    # Order matters: add_middleware inserts at index 0, so the last one added is
    # the outermost layer. Host validation is therefore the innermost of the
    # three, and the security headers wrap everything -- including the 400 that
    # TrustedHostMiddleware returns for a disallowed Host.
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(SecurityHeadersMiddleware, headers=SECURITY_HEADERS)

    return application
