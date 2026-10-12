#!/usr/bin/env python3
# File: app/presentation/http/routes/health.py
# Author: Oluwatobiloba Light Agunloye
from fastapi import APIRouter, status

router = APIRouter()


@router.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness() -> dict[str, str]:
    """Confirms the process is alive; does not depend on external services."""
    return {"status": "ok"}


@router.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness() -> dict[str, str]:
    """Placeholder readiness check. Add database/dependency checks when needed."""
    return {"status": "ok"}
