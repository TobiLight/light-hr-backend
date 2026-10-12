# File: conftest.py
# Author: Oluwatibiloba Light Agunloye
"""Root conftest.

Existence is load-bearing: pytest prepends the rootdir to ``sys.path`` when it
collects this file, which is what makes ``import app.*`` resolve under
``uv run pytest`` without a ``pythonpath`` ini setting. Internal imports are
always absolute from the ``app`` package; see ``tests/smoke``.
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# database_url has no default (T7), so every test that constructs an app or a
# Configs would fail validation without one. A local DSN is enough here: no test
# opens a connection, and test_config.py deliberately asserts the field is
# required when this is absent.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://app:app@localhost:5432/app",
)
