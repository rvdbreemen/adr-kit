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

import os
import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "githooks" / "pre-commit"
ADR_043 = next((ROOT / "docs" / "adr").glob("ADR-043-*.md"))

needs_tools = pytest.mark.skipif(
    os.name == "nt" or not all(shutil.which(tool) for tool in ("bash", "git", "flock")),
    reason="needs bash, git and flock (the guard only takes the lock where flock exists)",
)


def _git(cwd: pathlib.Path, *args: str, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=cwd, env=env, capture_output=True, text=True, timeout=120,
    )


def _project(tmp_path: pathlib.Path) -> tuple[pathlib.Path, dict]:
    home = tmp_path / "home"
    cache = home / ".claude" / "plugins" / "cache" / "rvdbreemen-adr-kit" / "adr-kit"
    cache.mkdir(parents=True)
    (cache / "99.0.0").symlink_to(ROOT, target_is_directory=True)
    env = {
        **{key: value for key, value in os.environ.items() if not key.startswith("GIT_")},
        "HOME": str(home),
        "ADR_KIT_NO_LLM": "1",
        "ADR_KIT_SUGGEST_DISABLE": "1",
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
    }
    repo = tmp_path / "repo"
    (repo / "docs" / "adr").mkdir(parents=True)
    shutil.copy2(ADR_043, repo / "docs" / "adr" / ADR_043.name)
    hooks = repo / ".githooks"
    hooks.mkdir()
    shutil.copy2(TEMPLATE, hooks / "pre-commit")
    (hooks / "pre-commit").chmod(0o755)
    _git(repo, "init", "-q", env=env)
    _git(repo, "config", "core.hooksPath", ".githooks", env=env)
    _git(repo, "add", "-A", env=env)
    first = _git(repo, "commit", "-q", "--no-verify", "-m", "seed", env=env)
    assert first.returncode == 0, first.stderr
    return repo, env


def _stage_violation(repo: pathlib.Path, env: dict) -> None:
    target = repo / "bin" / "adr_llm.py"
    target.parent.mkdir(exist_ok=True)
    target.write_text('DEFAULT_LLM_CMD = ["claude", "-p"]\n', encoding="utf-8")
    _git(repo, "add", "bin/adr_llm.py", env=env)


@needs_tools
def test_a_refused_commit_prints_the_violation_report(tmp_path):
    repo, env = _project(tmp_path)
    _stage_violation(repo, env)

    result = _git(repo, "commit", "-m", "violates ADR-043", env=env)

    assert result.returncode != 0, "the commit should have been refused"
    assert "VIOLATION" in result.stderr and "ADR-043" in result.stderr, (
        f"the refusal printed nothing useful: {result.stderr!r}"
    )


@needs_tools
def test_a_linked_worktree_takes_the_lock_instead_of_reporting_a_rival(tmp_path):
    repo, env = _project(tmp_path)
    worktree = tmp_path / "wt"
    added = _git(repo, "worktree", "add", "-q", str(worktree), env=env)
    assert added.returncode == 0, added.stderr
    _stage_violation(worktree, env)

    result = _git(worktree, "commit", "-m", "violates ADR-043", env=env)

    assert "another ADR judge is running" not in result.stderr
    assert result.returncode != 0
    assert "VIOLATION" in result.stderr
