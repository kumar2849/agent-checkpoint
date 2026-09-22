"""Small shared helpers used by the CLI and action runner."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable, Mapping


def normalize_path(value: str | Path) -> str:
    """Return a stable repository-relative path representation."""

    text = str(value).replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    return text


def parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off", ""}:
        return False
    raise ValueError(f"invalid boolean value: {value!r}")


def ai_line_ratio(ai_lines: Mapping[str, Iterable[int]], changed_lines: Mapping[str, Iterable[int]]) -> float:
    ai_count = sum(len(set(lines)) for lines in ai_lines.values())
    changed_count = sum(len(set(lines)) for lines in changed_lines.values())
    return ai_count / changed_count if changed_count else 0.0


def write_github_outputs(values: Mapping[str, object], output_path: str | Path | None = None) -> None:
    """Append deterministic scalar outputs to the GitHub Actions output file."""

    target = output_path or os.environ.get("GITHUB_OUTPUT")
    if not target:
        return
    with Path(target).open("a", encoding="utf-8", newline="\n") as stream:
        for key in sorted(values):
            value = values[key]
            rendered = json.dumps(value, separators=(",", ":")) if isinstance(value, (list, dict)) else str(value).lower() if isinstance(value, bool) else str(value)
            stream.write(f"{key}={rendered}\n")

