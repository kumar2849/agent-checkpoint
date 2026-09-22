"""Load per-test line attribution produced by coverage.py/pytest-cov."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from .utils import normalize_path

CoverageMap = dict[str, dict[int, set[str]]]


class CoverageMapError(ValueError):
    """Raised for malformed or unusable coverage data."""


def _test_from_context(context: str) -> str | None:
    context = context.strip()
    if not context or context == "(empty)":
        return None
    # pytest-cov contexts look like ``tests/test_x.py::test_y|run``.
    test_name = context.rsplit("|", 1)[0]
    return test_name if "::" in test_name else None


def load_coverage_map(path: str | Path) -> CoverageMap:
    """Read coverage JSON created with ``coverage json --show-contexts``."""

    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CoverageMapError(f"cannot read coverage map {path}: {exc}") from exc

    files = payload.get("files")
    if not isinstance(files, dict):
        raise CoverageMapError("coverage JSON has no 'files' object")

    result: CoverageMap = {}
    for raw_path, details in files.items():
        contexts = details.get("contexts", {}) if isinstance(details, dict) else {}
        if not isinstance(contexts, dict):
            continue
        line_map: dict[int, set[str]] = {}
        for raw_line, raw_contexts in contexts.items():
            try:
                line_number = int(raw_line)
            except (TypeError, ValueError):
                continue
            tests = {
                test
                for context in raw_contexts or []
                if isinstance(context, str) and (test := _test_from_context(context))
            }
            if tests:
                line_map[line_number] = tests
        if line_map:
            result[normalize_path(raw_path)] = line_map
    return result


def generate_coverage_json(
    repo_path: str | Path,
    output_path: str | Path,
    test_args: Sequence[str] = (),
) -> None:
    """Run pytest with per-test contexts and export coverage JSON.

    This is intended for periodically refreshing a baseline map. Incremental
    runs should consume the stored JSON rather than regenerate it every time.
    """

    repo = Path(repo_path)
    output = Path(output_path)
    commands = [
        [sys.executable, "-m", "pytest", "--cov=.", "--cov-context=test", *test_args],
        [sys.executable, "-m", "coverage", "json", "--show-contexts", "-o", str(output)],
    ]
    for command in commands:
        completed = subprocess.run(command, cwd=repo, check=False)
        if completed.returncode:
            raise RuntimeError(f"coverage command failed with exit code {completed.returncode}: {' '.join(command)}")
