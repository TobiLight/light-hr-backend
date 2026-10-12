#!/usr/bin/env python3
# File: app/core/config.py
# Author: Oluwatobiloba Light Agunloye
"""Light HRMS Config"""

import logging
from functools import lru_cache
from typing import Annotated, Any, Literal

from dotenv import load_dotenv
from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

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
    # An explicit allowlist, never a wildcard. Starlette's TestClient sends
    # Host: testserver, so it is listed to keep the suite working.
    # NoDecode stops pydantic-settings from demanding JSON for list fields,
    # so an operator can write ALLOWED_HOSTS=a.example.com,b.example.com.
    allowed_hosts: Annotated[list[str], NoDecode] = ["localhost", "127.0.0.1", "testserver"]
    # Empty by default: fail closed until an operator names the origins. A
    # wildcard alongside allow_credentials=True is rejected by browsers and
    # is what CVE-shaped bugs look like.
    cors_origins: Annotated[list[str], NoDecode] = []

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

    @field_validator("allowed_hosts", "cors_origins", mode="before")
    @classmethod
    def split_comma_separated(cls, value: Any) -> Any:
        """Accept "a,b,c" from the environment and already-parsed sequences.

        pydantic-settings would otherwise demand JSON for a list field, which
        is not what anyone writes in a .env file. An empty string becomes an
        empty list so the production allowlist check can see it.
        """
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

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

    @model_validator(mode="after")
    def require_allowed_hosts_in_production(self) -> "Configs":
        """Refuse to boot production with an empty host allowlist.

        The list defaults to local dev hosts, so an operator deploying without
        setting ALLOWED_HOSTS gets a fail-closed service rather than one that
        trusts every Host header. An explicitly empty list is treated the same
        way -- it would silently disable the check.
        """
        if self.app_env == "production" and not self.allowed_hosts:
            raise ValueError(
                "allowed_hosts must not be empty when app_env='production'; "
                "set ALLOWED_HOSTS to your public hostnames. An empty list "
                "disables host validation entirely."
            )
        return self


@lru_cache
def get_settings() -> Configs:
    """Cache settings so the app has one consistent configuration snapshot."""
    return Configs()
