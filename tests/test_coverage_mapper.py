from __future__ import annotations

import json

import pytest

from agent_checkpoint.coverage_mapper import CoverageMapError, load_coverage_map


def test_loads_pytest_dynamic_contexts(tmp_path):
    coverage = {
        "meta": {"show_contexts": True},
        "files": {
            "src\\pkg\\foo.py": {
                "contexts": {
                    "12": ["tests/test_foo.py::test_bar|run", "tests/test_foo.py::test_bar|setup"],
                    "13": ["tests/test_foo.py::test_baz|run", ""],
                    "bad": ["tests/test_foo.py::ignored|run"],
                }
            }
        },
    }
    path = tmp_path / "coverage.json"
    path.write_text(json.dumps(coverage), encoding="utf-8")

    assert load_coverage_map(path) == {
        "src/pkg/foo.py": {
            12: {"tests/test_foo.py::test_bar"},
            13: {"tests/test_foo.py::test_baz"},
        }
    }


def test_rejects_non_coverage_json(tmp_path):
    path = tmp_path / "coverage.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(CoverageMapError, match="files"):
        load_coverage_map(path)


def test_reports_missing_file(tmp_path):
    with pytest.raises(CoverageMapError, match="cannot read"):
        load_coverage_map(tmp_path / "missing.json")

