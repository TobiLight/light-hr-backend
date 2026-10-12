#!/usr/bine/env python3
# File: app/presentation/http/api.py
# Author: Oluwatobiloba Light Agunloye
"""LIGHT HRMS API ROUTER"""

from fastapi import APIRouter

from presentation.http.routes.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
