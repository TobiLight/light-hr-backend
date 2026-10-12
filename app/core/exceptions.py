#!/usr/bin/env python3
# File: app/core/exceptions.py
# Author: Oluwatobiloba Light Agunloye
"""Application-wide exception types and HTTP mapping can be added here."""


class ApplicationError(Exception):
    """Base class for expected application errors."""


class ConfigurationError(ApplicationError):
    """Raised when application configuration is invalid for a requested operation."""
