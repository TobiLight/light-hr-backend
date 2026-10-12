#!/usr/bin/env python3
# File: app/core/app_creator.py
# Author: Oluwatobiloba Light Agunloye
"""LIGHT HRMS APP CREATOR"""


from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import light_hrms_config
from app.core.lifespan import lifespan


class AppCreator:
    def __init__(self) -> None:
        if not light_hrms_config.SECRET_KEY:
            raise RuntimeError("Missing Secret Key")

        self.container = Container()

        self.app = FastAPI(
            title=light_hrms_config.PROJECT_NAME,
            version="0.0.1",
            description="HRIS FastAPI Web Server",
            lifespan=lifespan,
        )

        # Keep application-scoped dependencies accessible.
        self.app.state.container = self.container

        self._configure_middleware()
        self._configure_routes()

    def _configure_middleware(self) -> None:
        self.app.add_middleware(
            SessionMiddleware,
            secret_key=light_hrms_config.SECRET_KEY,
            max_age=1800,
            same_site="lax",
        )

        if light_hrms_config.BACKEND_CORS_ORIGINS:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=[
                    str(origin)
                    for origin in light_hrms_config.BACKEND_CORS_ORIGINS
                ],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

    def _configure_routes(self) -> None:
        @self.app.get("/")
        async def root() -> dict[str, str]:
            return {"message": "Service is working"}

        self.app.include_router(
            routers,
            prefix=light_hrms_config.API,
        )
