"""Command-line orchestration for Agent Checkpoint."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

from .coverage_mapper import CoverageMapError, load_coverage_map
from .detect_ai_lines import GitError, detect_ai_lines, get_changed_lines
from .static_analysis import StaticAnalysisError, run_static_analysis
from .test_selector import select_tests
from .utils import ai_line_ratio, parse_bool, write_github_outputs


@dataclass(frozen=True)
class CheckpointResult:
    tests_to_run: list[str]
    ai_line_count: int
    changed_line_count: int
    ai_line_ratio: float
    skipped: bool
    fallback_to_full_suite: bool


def _env(name: str, default: str = "") -> str:
    return os.environ.get(f"INPUT_{name.upper().replace('-', '_')}", default)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Select tests affected by AI-authored changed lines")
    parser.add_argument("--repo-path", default=".")
    parser.add_argument(
        "--base-ref",
        default=_env("base-ref") or os.environ.get("AGENT_CHECKPOINT_BASE_SHA") or None,
    )
    parser.add_argument("--head-ref", default=_env("head-ref", "HEAD"))
    parser.add_argument("--ai-marker", default=_env("ai-marker", "Co-authored-by: <AI-agent>"))
    parser.add_argument("--ai-commit", action="append", default=[], help="Known AI commit SHA; repeatable")
    parser.add_argument("--ai-commits", default=_env("ai-commits"), help="Comma-separated known AI commit SHAs")
    parser.add_argument("--threshold", type=float, default=float(_env("threshold", "0.05")))
    parser.add_argument("--coverage-json", default=_env("coverage-json", "coverage.json"))
    parser.add_argument("--run-static", action="store_true", default=parse_bool(_env("run-static", "false")))
    parser.add_argument("--execute-tests", action="store_true", default=parse_bool(_env("execute-tests", "false")))
    parser.add_argument("--full-suite-target", default=_env("full-suite-target", "tests"))
    parser.add_argument("--output-json", type=Path)
    return parser


def run_checkpoint(args: argparse.Namespace) -> CheckpointResult:
    if not 0 <= args.threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")

    changed = get_changed_lines(args.repo_path, args.base_ref, args.head_ref)
    known_commits = [*args.ai_commit, *(part.strip() for part in args.ai_commits.split(",") if part.strip())]
    ai_lines = detect_ai_lines(changed, args.repo_path, args.ai_marker, known_commits, args.head_ref)
    changed_count = sum(len(lines) for lines in changed.values())
    ai_count = sum(len(lines) for lines in ai_lines.values())
    ratio = ai_line_ratio(ai_lines, changed)

    if ratio < args.threshold:
        print(f"Skipped: AI line ratio {ratio:.0%} < threshold {args.threshold:.0%}")
        return CheckpointResult([], ai_count, changed_count, ratio, True, False)

    if args.run_static:
        run_static_analysis(changed, args.repo_path)

    fallback = False
    coverage_path = Path(args.coverage_json)
    if not coverage_path.is_absolute():
        coverage_path = Path(args.repo_path) / coverage_path
    try:
        coverage_map = load_coverage_map(coverage_path)
        tests = select_tests(ai_lines, coverage_map)
    except CoverageMapError as exc:
        print(f"Warning: {exc}; falling back to the full test suite", file=sys.stderr)
        tests = []
        fallback = True

    if not tests:
        tests = [args.full_suite_target]
        if not fallback:
            print("No attributed tests found; falling back to the full test suite", file=sys.stderr)
        fallback = True

    if args.execute_tests:
        completed = subprocess.run([sys.executable, "-m", "pytest", *tests], cwd=args.repo_path, check=False)
        if completed.returncode:
            raise RuntimeError(f"selected tests failed with exit code {completed.returncode}")

    return CheckpointResult(tests, ai_count, changed_count, ratio, False, fallback)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_checkpoint(args)
    except (GitError, StaticAnalysisError, RuntimeError, ValueError) as exc:
        print(f"agent-checkpoint: {exc}", file=sys.stderr)
        return 1

    payload = asdict(result)
    payload["ai_line_ratio"] = round(result.ai_line_ratio, 6)
    rendered = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    print(rendered)
    if args.output_json:
        args.output_json.write_text(rendered + "\n", encoding="utf-8")
    write_github_outputs(
        {
            "ai-line-count": result.ai_line_count,
            "tests-to-run": result.tests_to_run,
            "skipped": result.skipped,
        }
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
