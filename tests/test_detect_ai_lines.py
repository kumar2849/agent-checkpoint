from __future__ import annotations

import subprocess

from agent_checkpoint.detect_ai_lines import (
    detect_ai_lines,
    get_changed_lines,
    parse_blame_porcelain,
    parse_unified_diff,
)


def _git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_parse_unified_diff_tracks_only_added_side_lines():
    diff = """diff --git a/foo.py b/foo.py
--- a/foo.py
+++ b/foo.py
@@ -2,2 +2,3 @@
+one
+two
+three
diff --git a/gone.py b/gone.py
--- a/gone.py
+++ /dev/null
@@ -1 +0,0 @@
-gone
"""
    assert parse_unified_diff(diff) == {"foo.py": {2, 3, 4}}


def test_parse_blame_porcelain_extracts_final_lines():
    blame = """abc123 4 8 1
author A
\tline
def456 5 9 1
author B
\tline
"""
    assert parse_blame_porcelain(blame) == {8: "abc123", 9: "def456"}


def test_detects_marker_commit_from_real_git_history(git_repo):
    base = _git(git_repo, "rev-parse", "HEAD")
    (git_repo / "sample.py").write_text("def answer():\n    return 42\n", encoding="utf-8")
    _git(git_repo, "add", "sample.py")
    _git(git_repo, "commit", "-q", "-m", "fix answer\n\nCo-authored-by: Test Bot")

    changed = get_changed_lines(git_repo, base)
    detected = detect_ai_lines(changed, git_repo, "Co-authored-by: Test Bot")

    assert changed == {"sample.py": {2}}
    assert detected == {"sample.py": {2}}


def test_detects_allowlisted_commit_without_marker(git_repo):
    base = _git(git_repo, "rev-parse", "HEAD")
    (git_repo / "sample.py").write_text("def answer():\n    return 43\n", encoding="utf-8")
    _git(git_repo, "add", "sample.py")
    _git(git_repo, "commit", "-q", "-m", "ordinary message")
    head = _git(git_repo, "rev-parse", "HEAD")

    changed = get_changed_lines(git_repo, base)
    detected = detect_ai_lines(changed, git_repo, known_ai_commits=[head[:10]])

    assert detected == {"sample.py": {2}}


def test_human_commit_is_not_a_false_positive(git_repo):
    base = _git(git_repo, "rev-parse", "HEAD")
    (git_repo / "sample.py").write_text("def answer():\n    return 44\n", encoding="utf-8")
    _git(git_repo, "add", "sample.py")
    _git(git_repo, "commit", "-q", "-m", "human change")

    changed = get_changed_lines(git_repo, base)
    assert detect_ai_lines(changed, git_repo, "Co-authored-by: Bot") == {}

