#!/usr/bin/env python3
# File: app/core/config.py
# Author: Oluwatobiloba Light Agunloye
"""Light HRMS Config"""


from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()

ENV: str = "dev"


class Configs(BaseSettings):
    # base
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "FastAPI DDD Starter"
    app_env: Literal["dev", "test", "staging", "production"] = "dev"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: str = Field(
        default="postgresql+asyncpg://app:app@localhost:5432/app",
        repr=False,
    )
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Configs:
    """Cache settings so the app has one consistent configuration snapshot."""
    return Configs()
