# File: app/infrastructure/persistence/base.py
# Author: Oluwatobiloba Light Agunloye
"""LIGHT HRMS PERSISTENCE BASE MODULE"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base for SQLAlchemy persistence mappings only."""
