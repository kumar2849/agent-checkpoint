"""Run lightweight language-specific linters on changed files."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Iterable
from pathlib import Path

from .utils import normalize_path

PYTHON_SUFFIXES = {".py", ".pyi"}
JAVASCRIPT_SUFFIXES = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}


class StaticAnalysisError(RuntimeError):
    """Raised when a linter is unavailable or reports a violation."""


def _run(command: list[str], repo_path: str | Path) -> None:
    completed = subprocess.run(command, cwd=repo_path, check=False, capture_output=True, text=True)
    if completed.returncode:
        output = "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part.strip())
        raise StaticAnalysisError(output or f"{' '.join(command)} exited with {completed.returncode}")


def run_static_analysis(files: Iterable[str], repo_path: str | Path = ".") -> None:
    """Run Ruff and/or ESLint only for changed files of the relevant type."""

    normalized = sorted({normalize_path(path) for path in files})
    python_files = [path for path in normalized if Path(path).suffix.lower() in PYTHON_SUFFIXES]
    javascript_files = [path for path in normalized if Path(path).suffix.lower() in JAVASCRIPT_SUFFIXES]

    if python_files:
        if not shutil.which("ruff"):
            raise StaticAnalysisError("Ruff is required for changed Python files but was not found")
        _run(["ruff", "check", *python_files], repo_path)
    if javascript_files:
        eslint = shutil.which("eslint")
        npx = shutil.which("npx")
        if eslint:
            command = [eslint, *javascript_files]
        elif npx:
            command = [npx, "--no-install", "eslint", *javascript_files]
        else:
            raise StaticAnalysisError("ESLint is required for changed JavaScript/TypeScript files but was not found")
        _run(command, repo_path)

