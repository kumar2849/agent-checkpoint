"""Select pytest node IDs whose coverage intersects AI-authored lines."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from .coverage_mapper import CoverageMap
from .utils import normalize_path


def select_tests(
    ai_lines: Mapping[str, Iterable[int]],
    coverage_map: CoverageMap,
) -> list[str]:
    """Return a sorted, de-duplicated union of tests covering *ai_lines*."""

    selected: set[str] = set()
    normalized_coverage = {normalize_path(path): lines for path, lines in coverage_map.items()}
    for raw_path, line_numbers in ai_lines.items():
        path = normalize_path(raw_path)
        covered_lines = normalized_coverage.get(path)
        if covered_lines is None:
            # coverage.py may emit absolute paths unless ``relative_files`` is
            # enabled. Only accept a unique suffix match to avoid ambiguity.
            suffix_matches = [lines for candidate, lines in normalized_coverage.items() if candidate.endswith(f"/{path}")]
            covered_lines = suffix_matches[0] if len(suffix_matches) == 1 else {}
        for line_number in set(line_numbers):
            selected.update(covered_lines.get(line_number, ()))
    return sorted(selected)
