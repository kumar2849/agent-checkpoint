from __future__ import annotations

from agent_checkpoint.utils import ai_line_ratio, parse_bool, write_github_outputs


def test_ai_line_ratio_and_empty_diff():
    assert ai_line_ratio({"a.py": {1}}, {"a.py": {1, 2, 3, 4}}) == 0.25
    assert ai_line_ratio({}, {}) == 0.0


def test_parse_bool():
    assert parse_bool("TRUE") is True
    assert parse_bool("off") is False


def test_github_outputs_are_deterministic_json(tmp_path):
    output = tmp_path / "outputs"
    write_github_outputs({"tests-to-run": ["b", "a"], "ai-line-count": 2}, output)
    assert output.read_text(encoding="utf-8") == 'ai-line-count=2\ntests-to-run=["b","a"]\n'

