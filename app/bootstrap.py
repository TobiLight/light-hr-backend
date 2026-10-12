#!/usr/bin/env python3
# File: app/core/bootstrap.py
# Author: Oluwatobiloba Light Agunloye
"""LIGHT HRMS APP BOOTSTRAP"""

from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.infrastructure.persistence.database import dispose_database
from app.presentation.http.api import api_router


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
    return application
