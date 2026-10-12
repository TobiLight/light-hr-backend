# File: conftest.py
# Author: Oluwatibiloba Light Agunloye
"""Root conftest.

Existence is load-bearing: pytest prepends the rootdir to ``sys.path`` when it
collects this file, which is what makes ``import app.*`` resolve under
``uv run pytest`` without a ``pythonpath`` ini setting. Internal imports are
always absolute from the ``app`` package; see ``tests/smoke``.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
