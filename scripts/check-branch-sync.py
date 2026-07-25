#!/usr/bin/env python3
"""Assert the release branch has been merged back into the development branch.

adr-kit releases land on `main` (protected, tagged, published), while day-to-day
work continues on `dev`. Nothing in the release flow moves those release commits
back, so `dev` silently drifts behind every time a version ships.

That drift is not cosmetic. It has already bitten twice: by v0.40.0 the `dev`
branch was 32 commits behind `main`, still declared version 0.37.0, and was
missing the whole release toolchain it is supposed to run (`bump-version.py`,
`check-release-version.py`, `packaging/version-sites.json`, `docs/RELEASING.md`,
`release-publish.yml`) plus three Accepted ADRs. Cutting the next release from
`dev` in that state would have reverted three published versions.

This check makes the drift loud instead of silent. It compares the two branches
and reports every release tag that reached the release branch but never reached
the development branch, so the finding names the versions at risk rather than a
bare commit count.

Exit codes follow the adr-readiness convention:
  0  the development branch contains every release-branch commit
  1  the development branch is behind (drift found)
  2  infrastructure or configuration error (bad ref, not a git repo)

Usage:
  python scripts/check-branch-sync.py
  python scripts/check-branch-sync.py --format json
  python scripts/check-branch-sync.py --release-branch main --dev-branch dev
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent

# Cap the per-commit detail so a long drift reports a useful sample instead of
# thousands of lines. The counts and the tag list stay complete either way.
MAX_LISTED_COMMITS = 15

SEMVER_TAG = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


class GitError(RuntimeError):
    """A git invocation failed or a ref could not be resolved."""


def run_git(args: List[str], repo: Path) -> str:
    """Run a git command and return stdout, raising GitError on failure."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(repo),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError as exc:  # git missing entirely
        raise GitError(f"could not run git: {exc}") from exc
    if result.returncode != 0:
        raise GitError(
            f"git {' '.join(args)} failed: {result.stderr.strip() or 'unknown error'}"
        )
    return result.stdout


def resolve_ref(name: str, repo: Path) -> str:
    """Resolve a branch name, preferring the remote-tracking copy.

    CI checks out a single branch, so `main` may exist only as `origin/main`.
    Local clones usually have both. Preferring the remote keeps the check
    honest about what is actually published rather than what happens to be
    checked out.
    """
    for candidate in (f"origin/{name}", name):
        try:
            run_git(["rev-parse", "--verify", f"{candidate}^{{commit}}"], repo)
        except GitError:
            continue
        return candidate
    raise GitError(
        f"branch {name!r} not found as 'origin/{name}' or '{name}'. "
        "Fetch it first (a shallow checkout will not have it)."
    )


def count_commits(base: str, head: str, repo: Path) -> int:
    """Count commits reachable from head but not from base."""
    out = run_git(["rev-list", "--count", f"{base}..{head}"], repo)
    return int(out.strip() or "0")


def list_commits(base: str, head: str, repo: Path, limit: int) -> List[Dict[str, str]]:
    """List up to `limit` commits reachable from head but not from base."""
    out = run_git(
        ["log", f"--max-count={limit}", "--format=%h%x1f%s", f"{base}..{head}"],
        repo,
    )
    commits = []
    for line in out.splitlines():
        if not line.strip():
            continue
        sha, _, subject = line.partition("\x1f")
        commits.append({"sha": sha, "subject": subject})
    return commits


def tags_merged_into(ref: str, repo: Path) -> List[str]:
    """Return the release tags reachable from ref."""
    out = run_git(["tag", "--merged", ref], repo)
    return [line.strip() for line in out.splitlines() if line.strip()]


def version_key(tag: str) -> Tuple[int, int, int]:
    """Sort key for a semver tag; unparsable tags sort first."""
    match = SEMVER_TAG.match(tag)
    if not match:
        return (-1, -1, -1)
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def missing_release_tags(release_ref: str, dev_ref: str, repo: Path) -> List[str]:
    """Release tags on the release branch that never reached the dev branch."""
    on_release = set(tags_merged_into(release_ref, repo))
    on_dev = set(tags_merged_into(dev_ref, repo))
    missing = [tag for tag in on_release - on_dev if SEMVER_TAG.match(tag)]
    return sorted(missing, key=version_key)


def evaluate(release_branch: str, dev_branch: str, repo: Path) -> Dict:
    """Compare the two branches and build the full report."""
    release_ref = resolve_ref(release_branch, repo)
    dev_ref = resolve_ref(dev_branch, repo)

    behind = count_commits(dev_ref, release_ref, repo)
    ahead = count_commits(release_ref, dev_ref, repo)

    report: Dict = {
        "release_branch": release_ref,
        "dev_branch": dev_ref,
        "in_sync": behind == 0,
        "behind_count": behind,
        "ahead_count": ahead,
        "missing_tags": [],
        "missing_commits": [],
        "truncated": False,
    }
    if behind:
        report["missing_tags"] = missing_release_tags(release_ref, dev_ref, repo)
        report["missing_commits"] = list_commits(
            dev_ref, release_ref, repo, MAX_LISTED_COMMITS
        )
        report["truncated"] = behind > MAX_LISTED_COMMITS
    return report


def render(report: Dict) -> str:
    """Render the report as human-readable text."""
    release = report["release_branch"]
    dev = report["dev_branch"]
    lines = [f"Branch sync check: {release} -> {dev}", ""]

    if report["in_sync"]:
        lines.append(f"  [ok] {dev} contains every commit from {release}")
        if report["ahead_count"]:
            lines.append(
                f"  [info] {dev} is {report['ahead_count']} commit(s) ahead, "
                "which is expected for unreleased work"
            )
        lines.append("")
        lines.append("Branches are in sync.")
        return "\n".join(lines)

    lines.append(
        f"  [BEHIND] {dev} is missing {report['behind_count']} commit(s) from {release}"
    )
    if report["missing_tags"]:
        lines.append(
            f"  [BEHIND] released versions not on {dev}: "
            + ", ".join(report["missing_tags"])
        )
    lines.append("")
    lines.append("Missing commits (newest first):")
    for commit in report["missing_commits"]:
        lines.append(f"  {commit['sha']}  {commit['subject']}")
    if report["truncated"]:
        remaining = report["behind_count"] - len(report["missing_commits"])
        lines.append(f"  ... and {remaining} more")
    lines.append("")
    lines.append(f"{dev} has fallen behind {release}. Merge the release back:")
    lines.append("")
    lines.append("    git fetch origin")
    lines.append(f"    git checkout -b sync/release-to-dev origin/{dev.split('/')[-1]}")
    lines.append(f"    git merge {release}")
    lines.append("    # resolve conflicts, run the release gates, open a PR into "
                 f"{dev.split('/')[-1]}")
    lines.append("")
    lines.append("See docs/RELEASING.md step 4 (merge the release back into dev).")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--release-branch",
        default="main",
        help="Branch that receives releases. Default: main",
    )
    parser.add_argument(
        "--dev-branch",
        default="dev",
        help="Branch that ongoing work continues on. Default: dev",
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Repository to inspect. Default: the adr-kit checkout this script is in.",
    )
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)

    repo = Path(args.repo_root).resolve() if args.repo_root else ROOT

    try:
        report = evaluate(args.release_branch, args.dev_branch, repo)
    except GitError as exc:
        print(f"check-branch-sync: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        print(render(report))
    return 0 if report["in_sync"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
