#!/usr/bin/env python3
# File: app/core/lifespan.py
# Author: Oluwatobiloba Light Agunloye
"""LIGHT HRMS LIFESPAN MANAGER"""


from collections.abc import AsyncIterator

from fastapi import FastAPI


async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    container = app.state.container

    # Initialize application-scoped resources here if needed.
    # For example, connect to Redis or initialize other clients.

    try:
        yield
    finally:
        # Close only resources whose lifecycle this function owns.
        # Use your container's actual shutdown mechanism here.
        pass
