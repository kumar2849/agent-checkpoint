from __future__ import annotations

from types import SimpleNamespace

import pytest

from agent_checkpoint import static_analysis


def test_runs_only_relevant_linters(monkeypatch, tmp_path):
    commands = []
    monkeypatch.setattr(static_analysis.shutil, "which", lambda tool: tool)

    def fake_run(command, **kwargs):
        commands.append(command)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(static_analysis.subprocess, "run", fake_run)
    static_analysis.run_static_analysis(["src/a.py", "web/a.ts", "README.md"], tmp_path)

    assert commands == [
        ["ruff", "check", "src/a.py"],
        ["eslint", "web/a.ts"],
    ]


def test_lint_failure_includes_output(monkeypatch, tmp_path):
    monkeypatch.setattr(static_analysis.shutil, "which", lambda tool: tool)
    monkeypatch.setattr(
        static_analysis.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout="E501 too long", stderr=""),
    )
    with pytest.raises(static_analysis.StaticAnalysisError, match="E501"):
        static_analysis.run_static_analysis(["bad.py"], tmp_path)

