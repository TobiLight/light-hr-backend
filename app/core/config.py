#!/usr/bin/env python3
# File: app/core/config.py
# Author: Oluwatobiloba Light Agunloye
"""Light HRMS Config"""

import logging
from functools import lru_cache
from typing import Any, Literal

from dotenv import load_dotenv
from pydantic import SecretStr, field_validator, model_validator
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

    app_name: str = "LIGHT_HRMS BACKEND "
    app_env: Literal["dev", "test", "staging", "production"] = "dev"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    # Required on purpose: a missing value must fail at boot rather than
    # silently connecting to localhost. SecretStr because the DSN carries the
    # database password -- Field(repr=False) only hid it from repr(), while
    # model_dump()/model_dump_json() returned it in plaintext.
    database_url: SecretStr
    log_level: str = "INFO"

    @field_validator("log_level", mode="before")
    @classmethod
    def validate_log_level(cls, value: Any) -> Any:
        """Normalize and reject log levels the standard library cannot resolve."""
        if not isinstance(value, str):
            return value

        normalized = value.strip().upper()
        valid_levels = logging.getLevelNamesMapping()
        if normalized not in valid_levels:
            allowed = ", ".join(sorted(valid_levels))
            raise ValueError(
                f"LOG_LEVEL {value!r} is not a valid logging level. Valid levels: {allowed}"
            )
        return normalized

    @model_validator(mode="after")
    def reject_debug_outside_dev(self) -> "Configs":
        """Refuse debug=True anywhere but development.

        With debug on, an unhandled exception renders the full traceback to the
        client -- absolute source paths, exception class and message -- which
        carries internal hostnames and ports.
        """
        if self.debug and self.app_env != "dev":
            raise ValueError(
                f"debug=True requires app_env='dev', got app_env={self.app_env!r}. "
                "A debug-enabled app returns tracebacks and absolute source "
                "paths to the client."
            )
        return self


@lru_cache
def get_settings() -> Configs:
    """Cache settings so the app has one consistent configuration snapshot."""
    return Configs()
