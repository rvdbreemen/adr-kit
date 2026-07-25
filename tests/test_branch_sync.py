"""End-to-end tests for scripts/check-branch-sync.py.

Each test builds a throwaway git repository, runs the CLI as a subprocess and
asserts on the JSON output and exit code. This verifies the public interface
(exit codes and report shape), not internal helpers.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECK = REPO_ROOT / "scripts" / "check-branch-sync.py"


def git(repo: Path, *args: str) -> str:
    """Run a git command inside repo and return stdout."""
    result = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout


def commit(repo: Path, message: str) -> None:
    """Create an empty commit so history can diverge without file conflicts."""
    git(repo, "commit", "--allow-empty", "-m", message)


def make_repo(tmp_path: Path) -> Path:
    """Initialise a repo with a `main` branch carrying one commit."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "commit.gpgsign", "false")
    commit(repo, "root commit")
    git(repo, "branch", "-M", "main")
    return repo


def run_check(repo: Path, *args: str):
    """Invoke the checker against repo with --format json."""
    result = subprocess.run(
        [sys.executable, str(CHECK), "--repo-root", str(repo), "--format", "json", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if not result.stdout.strip():
        return result.returncode, {"_stderr": result.stderr}
    try:
        return result.returncode, json.loads(result.stdout)
    except json.JSONDecodeError:
        return result.returncode, {"_stdout": result.stdout, "_stderr": result.stderr}


def test_in_sync_when_dev_matches_main(tmp_path):
    """dev branched off main with no divergence is in sync."""
    repo = make_repo(tmp_path)
    git(repo, "branch", "dev")

    code, report = run_check(repo)

    assert code == 0
    assert report["in_sync"] is True
    assert report["behind_count"] == 0
    assert report["missing_tags"] == []


def test_dev_ahead_only_is_still_in_sync(tmp_path):
    """Unreleased work on dev is expected and must not be reported as drift."""
    repo = make_repo(tmp_path)
    git(repo, "checkout", "-b", "dev")
    commit(repo, "unreleased work")

    code, report = run_check(repo)

    assert code == 0
    assert report["in_sync"] is True
    assert report["behind_count"] == 0
    assert report["ahead_count"] == 1


def test_dev_behind_main_is_reported(tmp_path):
    """Release commits that never reached dev are drift and fail the check."""
    repo = make_repo(tmp_path)
    git(repo, "branch", "dev")
    commit(repo, "release commit on main")

    code, report = run_check(repo)

    assert code == 1
    assert report["in_sync"] is False
    assert report["behind_count"] == 1
    assert report["missing_commits"][0]["subject"] == "release commit on main"


def test_missing_release_tags_are_named(tmp_path):
    """The report names the released versions at risk, not just a commit count."""
    repo = make_repo(tmp_path)
    git(repo, "branch", "dev")
    commit(repo, "release: 0.41.0")
    git(repo, "tag", "v0.41.0")
    commit(repo, "release: 0.42.0")
    git(repo, "tag", "v0.42.0")

    code, report = run_check(repo)

    assert code == 1
    assert report["missing_tags"] == ["v0.41.0", "v0.42.0"]


def test_tags_already_on_dev_are_not_reported(tmp_path):
    """A version merged back into dev is no longer missing."""
    repo = make_repo(tmp_path)
    commit(repo, "release: 0.41.0")
    git(repo, "tag", "v0.41.0")
    git(repo, "branch", "dev")
    commit(repo, "release: 0.42.0")
    git(repo, "tag", "v0.42.0")

    code, report = run_check(repo)

    assert code == 1
    assert report["missing_tags"] == ["v0.42.0"]


def test_non_semver_tags_are_ignored(tmp_path):
    """Only release tags are reported; ad-hoc tags are noise."""
    repo = make_repo(tmp_path)
    git(repo, "branch", "dev")
    commit(repo, "release commit")
    git(repo, "tag", "v0.41.0")
    git(repo, "tag", "nightly-build")

    code, report = run_check(repo)

    assert code == 1
    assert report["missing_tags"] == ["v0.41.0"]


def test_missing_commit_list_is_capped_and_flagged(tmp_path):
    """A long drift reports a bounded sample and says so."""
    repo = make_repo(tmp_path)
    git(repo, "branch", "dev")
    for index in range(20):
        commit(repo, f"release commit {index}")

    code, report = run_check(repo)

    assert code == 1
    assert report["behind_count"] == 20
    assert len(report["missing_commits"]) == 15
    assert report["truncated"] is True


def test_unknown_branch_is_an_infrastructure_error(tmp_path):
    """A missing ref exits 2 so CI can tell drift from a broken checkout."""
    repo = make_repo(tmp_path)

    code, report = run_check(repo, "--dev-branch", "no-such-branch")

    assert code == 2
    assert "no-such-branch" in report["_stderr"]


def test_text_output_names_the_runbook_step(tmp_path):
    """The human-readable failure points at the runbook rather than a bare diff."""
    repo = make_repo(tmp_path)
    git(repo, "branch", "dev")
    commit(repo, "release commit on main")

    result = subprocess.run(
        [sys.executable, str(CHECK), "--repo-root", str(repo)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 1
    assert "docs/RELEASING.md" in result.stdout
    assert "git merge" in result.stdout
