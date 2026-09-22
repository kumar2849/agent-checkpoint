from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.name", "Test User")
    git(tmp_path, "config", "user.email", "test@example.com")
    source = tmp_path / "sample.py"
    source.write_text("def answer():\n    return 41\n", encoding="utf-8")
    git(tmp_path, "add", "sample.py")
    git(tmp_path, "commit", "-q", "-m", "human baseline")
    return tmp_path

