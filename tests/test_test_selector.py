from agent_checkpoint.test_selector import select_tests


def test_selects_sorted_union_for_ai_lines():
    coverage = {
        "src/foo.py": {
            12: {"tests/test_foo.py::test_bar"},
            13: {"tests/test_foo.py::test_baz", "tests/test_foo.py::test_bar"},
        }
    }
    assert select_tests({"src\\foo.py": {12, 13}}, coverage) == [
        "tests/test_foo.py::test_bar",
        "tests/test_foo.py::test_baz",
    ]


def test_returns_empty_for_uncovered_lines():
    assert select_tests({"src/foo.py": {99}}, {"src/foo.py": {1: {"tests/test_foo.py::test_one"}}}) == []


def test_matches_absolute_coverage_path_by_unique_suffix():
    coverage = {"C:/work/repo/src/foo.py": {5: {"tests/test_foo.py::test_five"}}}
    assert select_tests({"src/foo.py": {5}}, coverage) == ["tests/test_foo.py::test_five"]


def test_small_impacted_area_reduces_a_thousand_test_schedule_by_over_70_percent():
    coverage = {
        "src/service.py": {
            line: {f"tests/test_service.py::test_case_{line}"}
            for line in range(1, 1001)
        }
    }
    selected = select_tests({"src/service.py": set(range(1, 101))}, coverage)
    assert len(selected) == 100
    assert 1 - (len(selected) / 1000) >= 0.70
