"""Judge the branch before a pull request exists (spec R2, TASK-76).

The commit hook judges one commit. CI judges the pull request, but only once the
pull request is there. Between those two sits the moment the change actually
becomes a proposal: the agent runs `gh pr create`. In a coding harness that is a
tool call, so a pre-tool hook can intercept it and judge the whole branch
*before* the PR exists - earlier than CI can ever be.

**Why this lives outside adr_hook_core.** The retrieval hooks are
injection-only, model-free and forbidden by ADR-018's gate from importing
anything that can reach a model or the network - `subprocess` included, because
spawning a CLI is how this toolkit reaches a model. This guard must spawn
`adr-judge`, so it lives in its own module with its own budget rather than
weakening that assertion. Separate concerns, separate files, one gate that still
means what it says.

**This one may block, and that is the point.** Every other hook injects context
and never interferes. A violation here is precisely the case where the coding
agent should fix the code before proceeding, so a deny is the useful answer. It
still fails open on anything that is not a violation: no judge, no git, no
branch, a timeout - all let the command through, because a tool that cannot
check must not pretend it did.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Matching is on the command shape, not a substring. `gh pr create` must fire;
# `gh pr list`, `gh pr view`, and a comment mentioning gh pr create must not.
PR_CREATE_RE = re.compile(r"(?:^|[;&|]\s*)gh\s+pr\s+create\b")

# The branch diff is the whole development branch, not one commit, so it needs
# the CI-sized budget from TASK-73 rather than judge.max_diff_bytes.
CI_DIFF_BUDGET = 33_554_432
JUDGE_TIMEOUT_S = 120


def looks_like_pr_create(command: str) -> bool:
    return bool(PR_CREATE_RE.search(command or ""))


def _run(argv: List[str], cwd: Path, timeout: int, stdin_text: Optional[str] = None):
    return subprocess.run(
        argv,
        cwd=str(cwd),
        input=stdin_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def base_ref(cwd: Path) -> Optional[str]:
    """The branch this PR would target, from the repository's own configuration."""
    for argv in (
        ["git", "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"],
        ["git", "config", "--get", "init.defaultBranch"],
    ):
        try:
            result = _run(argv, cwd, 10)
        except (OSError, subprocess.SubprocessError):
            continue
        value = (result.stdout or "").strip()
        if result.returncode == 0 and value:
            return value.split("/")[-1]
    for candidate in ("main", "master", "dev"):
        try:
            probe = _run(["git", "rev-parse", "--verify", f"origin/{candidate}"], cwd, 10)
        except (OSError, subprocess.SubprocessError):
            return None
        if probe.returncode == 0:
            return candidate
    return None


def judge_branch(cwd: Path, adr_dir: Path, judge: Path) -> Dict:
    """Return a verdict dict. Every non-violation outcome is 'allow'."""
    if not judge.is_file():
        return {"decision": "allow", "reason": "adr-judge not found", "checked": False}
    if shutil.which("git") is None:
        return {"decision": "allow", "reason": "git not on PATH", "checked": False}
    base = base_ref(cwd)
    if not base:
        return {"decision": "allow", "reason": "no base branch to compare against", "checked": False}

    try:
        diff = _run(
            ["git", "diff", "--unified=0", f"origin/{base}...HEAD"], cwd, 60
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"decision": "allow", "reason": f"git diff failed ({exc})", "checked": False}
    if diff.returncode != 0:
        return {"decision": "allow", "reason": "git diff failed", "checked": False}
    if not (diff.stdout or "").strip():
        return {"decision": "allow", "reason": "empty branch diff", "checked": True}

    import sys

    try:
        verdict = _run(
            [
                sys.executable, str(judge),
                "--diff", "-",
                "--adr-dir", str(adr_dir),
                "--repo-root", str(cwd),
                "--snapshot", "worktree",
                "--max-diff-bytes", str(CI_DIFF_BUDGET),
                "--json",
            ],
            cwd,
            JUDGE_TIMEOUT_S,
            stdin_text=diff.stdout,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"decision": "allow", "reason": f"judge did not run ({exc})", "checked": False}

    if verdict.returncode == 0:
        return {"decision": "allow", "reason": "no violations on the branch", "checked": True}
    if verdict.returncode != 1:
        # Exit 2 is a configuration or input problem, including a diff over the
        # cap. That is a fact about the invocation, not about the code, and
        # blocking on it would punish the wrong thing.
        return {
            "decision": "allow",
            "reason": f"judge could not complete (exit {verdict.returncode})",
            "checked": False,
            "stderr": (verdict.stderr or "").strip()[:400],
        }

    findings = _violations(verdict.stdout)
    return {
        "decision": "deny",
        "reason": _explain(findings, base),
        "checked": True,
        "violations": findings,
    }


def _violations(stdout: str) -> List[Dict]:
    try:
        payload = json.loads(stdout or "{}")
    except (json.JSONDecodeError, ValueError):
        return []
    findings = payload.get("findings")
    if not isinstance(findings, list):
        return []
    return [f for f in findings if isinstance(f, dict) and f.get("severity") == "violation"]


def _explain(findings: List[Dict], base: str) -> str:
    if not findings:
        return (
            f"The branch violates an Accepted ADR against origin/{base}. "
            "Run `adr-judge` on the branch diff for the detail."
        )
    lines = [
        f"This branch violates {len(findings)} Accepted ADR rule(s) against "
        f"origin/{base}. Fix the code before opening the pull request:",
    ]
    for finding in findings[:5]:
        where = finding.get("path") or "?"
        line = finding.get("line")
        location = f"{where}:{line}" if line else where
        lines.append(f"  {finding.get('adr', '?')}  {location}  {finding.get('message', '')}".rstrip())
    if len(findings) > 5:
        lines.append(f"  ... and {len(findings) - 5} more")
    lines.append(
        "If the decision itself is wrong, supersede it rather than working around "
        "it; if this is a deliberate exception, ADR_KIT_OVERRIDE records it."
    )
    return "\n".join(lines)
