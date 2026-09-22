"""Detect changed lines whose owning commits contain AI metadata."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterable, Mapping
from pathlib import Path

from .utils import normalize_path

ChangedLines = dict[str, set[int]]

_HUNK = re.compile(r"^@@ -(?:\d+)(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
_BLAME_HEADER = re.compile(r"^([0-9a-fA-F^]+) \d+ (\d+)(?: \d+)?$")


class GitError(RuntimeError):
    """Raised when a required git command cannot be completed."""


def _git(repo_path: str | Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_path), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and result.returncode:
        message = result.stderr.strip() or result.stdout.strip() or "unknown git error"
        raise GitError(f"git {' '.join(args)} failed: {message}")
    return result.stdout


def parse_unified_diff(diff: str) -> ChangedLines:
    """Parse added-side line numbers from a zero-context unified diff."""

    changed: ChangedLines = {}
    current_file: str | None = None
    for raw_line in diff.splitlines():
        if raw_line.startswith("+++ "):
            candidate = raw_line[4:].split("\t", 1)[0]
            if candidate == "/dev/null":
                current_file = None
            else:
                current_file = normalize_path(candidate[2:] if candidate.startswith("b/") else candidate)
            continue
        match = _HUNK.match(raw_line)
        if match and current_file:
            start = int(match.group(1))
            count = int(match.group(2) or "1")
            if count:
                changed.setdefault(current_file, set()).update(range(start, start + count))
    return changed


def get_changed_lines(
    repo_path: str | Path = ".",
    base_ref: str | None = None,
    head_ref: str = "HEAD",
) -> ChangedLines:
    """Return added or modified line numbers between *base_ref* and *head_ref*.

    Without an explicit base, this compares the current commit to its first
    parent. A root commit is compared to git's empty tree.
    """

    if base_ref:
        revision = f"{base_ref}...{head_ref}"
    else:
        parent = _git(repo_path, "rev-parse", f"{head_ref}^", check=False).strip()
        if parent:
            revision = f"{parent}..{head_ref}"
        else:
            empty_tree = _git(repo_path, "hash-object", "-t", "tree", "/dev/null", check=False).strip()
            # Windows git does not interpret /dev/null consistently.
            if not empty_tree:
                empty_tree = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
            revision = f"{empty_tree}..{head_ref}"
    output = _git(
        repo_path,
        "diff",
        "--unified=0",
        "--no-color",
        "--diff-filter=ACMR",
        revision,
        "--",
    )
    return parse_unified_diff(output)


def parse_blame_porcelain(blame: str) -> dict[int, str]:
    """Map final line numbers to commit SHAs from line-porcelain output."""

    owners: dict[int, str] = {}
    for line in blame.splitlines():
        match = _BLAME_HEADER.match(line)
        if match:
            owners[int(match.group(2))] = match.group(1).lstrip("^")
    return owners


def _is_ai_commit(message: str, marker: str) -> bool:
    return bool(marker) and marker.casefold() in message.casefold()


def detect_ai_lines(
    changed_lines: Mapping[str, Iterable[int]],
    repo_path: str | Path = ".",
    marker: str = "Co-authored-by: <AI-agent>",
    known_ai_commits: Iterable[str] = (),
    revision: str = "HEAD",
) -> ChangedLines:
    """Return the subset of changed lines attributed to known AI commits."""

    whitelist = {sha.strip().lower() for sha in known_ai_commits if sha.strip()}
    result: ChangedLines = {}
    message_cache: dict[str, str] = {}

    for raw_path in sorted(changed_lines):
        path = normalize_path(raw_path)
        wanted = set(changed_lines[raw_path])
        if not wanted:
            continue
        blame = _git(repo_path, "blame", "--line-porcelain", revision, "--", path, check=False)
        owners = parse_blame_porcelain(blame)
        for line_number in sorted(wanted):
            sha = owners.get(line_number, "").lower()
            if not sha:
                continue
            whitelisted = any(sha.startswith(item) or item.startswith(sha) for item in whitelist)
            if not whitelisted:
                if sha not in message_cache:
                    message_cache[sha] = _git(repo_path, "show", "-s", "--format=%B", sha, check=False)
                whitelisted = _is_ai_commit(message_cache[sha], marker)
            if whitelisted:
                result.setdefault(path, set()).add(line_number)
    return result

