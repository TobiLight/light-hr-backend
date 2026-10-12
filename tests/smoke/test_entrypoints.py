# File: tests/smoke/test_entrypoints.py
# Author: Oluwatibiloba Light Agunloye
"""Entry-point regressions.

These tests guard the import root. They must never rely on pytest's own path
manipulation: the subprocess below runs with ``PYTHONPATH`` explicitly cleared
so it observes exactly what ``uvicorn app.main:app`` observes.
"""

import ast
import subprocess
import sys
from pathlib import Path

import pytest
from app.main import app
from fastapi import FastAPI

REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECT_MODULES = frozenset(
    {
        "bootstrap",
        "core",
        "domain",
        "infrastructure",
        "modules",
        "presentation",
    }
)
SCANNED_ROOTS = ("app", "tests")


def test_entrypoints_import_without_pythonpath():
    result = subprocess.run(
        [sys.executable, "-c", "import app.main"],
        cwd=REPO_ROOT,
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": ""},
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_asgi_target_resolves():
    assert isinstance(app, FastAPI)


@pytest.mark.parametrize("root", SCANNED_ROOTS)
def test_no_bare_internal_imports(root):
    offenders = []

    for path in sorted((REPO_ROOT / root).rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.level:
                continue
            root_name = (node.module or "").split(".")[0]
            if root_name in PROJECT_MODULES:
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}")

    assert not offenders, (
        "Internal modules must be imported through the 'app.' prefix, not bare "
        f"top-level names. Offending imports: {offenders}"
    )
