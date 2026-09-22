from __future__ import annotations

import argparse
import json

from agent_checkpoint import main


def _args(tmp_path, **overrides):
    values = {
        "repo_path": str(tmp_path),
        "base_ref": "base",
        "head_ref": "HEAD",
        "ai_marker": "Bot",
        "ai_commit": [],
        "ai_commits": "",
        "threshold": 0.05,
        "coverage_json": "coverage.json",
        "run_static": False,
        "execute_tests": False,
        "full_suite_target": "tests",
        "output_json": None,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def test_threshold_skip_does_not_load_coverage(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(main, "get_changed_lines", lambda *args: {"a.py": set(range(1, 201))})
    monkeypatch.setattr(main, "detect_ai_lines", lambda *args: {"a.py": set(range(1, 9))})
    monkeypatch.setattr(main, "load_coverage_map", lambda path: (_ for _ in ()).throw(AssertionError("not called")))

    result = main.run_checkpoint(_args(tmp_path))

    assert result.skipped is True
    assert result.tests_to_run == []
    assert "Skipped: AI line ratio 4% < threshold 5%" in capsys.readouterr().out


def test_selects_tests_and_runs_static_when_enabled(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(main, "get_changed_lines", lambda *args: {"src/a.py": {10, 11}})
    monkeypatch.setattr(main, "detect_ai_lines", lambda *args: {"src/a.py": {10}})
    monkeypatch.setattr(main, "load_coverage_map", lambda path: {"src/a.py": {10: {"tests/test_a.py::test_a"}}})
    monkeypatch.setattr(main, "run_static_analysis", lambda files, repo: calls.append((files, repo)))

    result = main.run_checkpoint(_args(tmp_path, run_static=True))

    assert result.tests_to_run == ["tests/test_a.py::test_a"]
    assert result.fallback_to_full_suite is False
    assert len(calls) == 1


def test_missing_attribution_falls_back_to_full_suite(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "get_changed_lines", lambda *args: {"src/a.py": {10}})
    monkeypatch.setattr(main, "detect_ai_lines", lambda *args: {"src/a.py": {10}})
    monkeypatch.setattr(main, "load_coverage_map", lambda path: {})

    result = main.run_checkpoint(_args(tmp_path))

    assert result.tests_to_run == ["tests"]
    assert result.fallback_to_full_suite is True


def test_main_writes_json_and_action_outputs(monkeypatch, tmp_path, capsys):
    result = main.CheckpointResult(["tests/test_a.py::test_a"], 1, 2, 0.5, False, False)
    monkeypatch.setattr(main, "run_checkpoint", lambda args: result)
    action_output = tmp_path / "github-output"
    report = tmp_path / "report.json"
    monkeypatch.setenv("GITHUB_OUTPUT", str(action_output))

    assert main.main(["--output-json", str(report)]) == 0

    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["tests_to_run"] == ["tests/test_a.py::test_a"]
    assert 'tests-to-run=["tests/test_a.py::test_a"]' in action_output.read_text(encoding="utf-8")
    assert json.loads(capsys.readouterr().out)["ai_line_count"] == 1
