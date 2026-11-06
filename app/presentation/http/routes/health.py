#!/usr/bin/env python3
# File: app/presentation/http/routes/health.py
# Author: Oluwatibiloba Light Agunloye
from fastapi import APIRouter, Depends, Response, status

from app.core.logging import get_logger
from app.infrastructure.persistence.database import ping_database

router = APIRouter()
logger = get_logger(__name__)


@router.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness() -> dict[str, str]:
    """Confirms the process is alive; does not depend on external services."""
    return {"status": "ok"}


@router.get(
    "/health/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness probe",
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "The database did not answer in time.",
        },
    },
)
async def readiness(
    response: Response,
    database_reachable: bool = Depends(ping_database),
) -> dict[str, str]:
    """Reports whether this instance can serve traffic.

    Queries the database, because an instance that cannot reach it must not be
    sent requests. The verdict is cached for a couple of seconds, so a probe
    storm cannot turn into a connection storm.

    The failure body names the dependency but never the DSN, the exception or
    the connection string: readiness is unauthenticated.
    """
    if not database_reachable:
        logger.warning("Readiness check failed", dependency="database")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable", "database": "unavailable"}
    logger.info("Readiness check passed", dependency="database")
    return {"status": "ok"}
