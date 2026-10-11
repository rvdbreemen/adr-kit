"""A refused commit says why (DEF-01, DEF-12).

The concurrency guard opened its lock with `exec 9>"$ROOT/.git/..." 2>/dev/null`.
A bare `exec` applies its redirections to the shell itself, so wherever `flock`
exists stderr went to /dev/null for the rest of the hook: the judge refused the
commit and the violation report it printed never reached the terminal. The same
line assumed `.git` is a directory; in a linked worktree it is a file, the lock
could not be opened, and the hook announced "another ADR judge is running".

These tests run the real template in a scratch repository whose only engine is
this checkout, reached through a fake Claude plugin cache.
"""

from __future__ import annotations

import pytest

from _precommit_project import git, link_engine, project, stage_violation, tools_present

needs_tools = pytest.mark.skipif(
    not tools_present("bash", "git", "flock"),
    reason="needs bash, git and flock (the guard only takes the lock where flock exists)",
)


def _with_claude_cache(tmp_path):
    repo, home, env = project(tmp_path)
    link_engine(home / ".claude" / "plugins" / "cache" / "rvdbreemen-adr-kit" / "adr-kit" / "99.0.0")
    return repo, env


@needs_tools
def test_a_refused_commit_prints_the_violation_report(tmp_path):
    repo, env = _with_claude_cache(tmp_path)
    stage_violation(repo, env)

    result = git(repo, "commit", "-m", "violates ADR-043", env=env)

    assert result.returncode != 0, "the commit should have been refused"
    assert "VIOLATION" in result.stderr and "ADR-043" in result.stderr, (
        f"the refusal printed nothing useful: {result.stderr!r}"
    )


@needs_tools
def test_a_linked_worktree_takes_the_lock_instead_of_reporting_a_rival(tmp_path):
    repo, env = _with_claude_cache(tmp_path)
    worktree = tmp_path / "wt"
    added = git(repo, "worktree", "add", "-q", str(worktree), env=env)
    assert added.returncode == 0, added.stderr
    stage_violation(worktree, env)

    result = git(worktree, "commit", "-m", "violates ADR-043", env=env)

    assert "another ADR judge is running" not in result.stderr
    assert result.returncode != 0
    assert "VIOLATION" in result.stderr
