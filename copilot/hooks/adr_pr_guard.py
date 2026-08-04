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
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Matching is on the command shape, not a substring. `gh pr create` must fire;
# `gh pr list`, `gh pr view`, and a comment mentioning gh pr create must not.
PR_CREATE_RE = re.compile(r"(?:^|[;&|]\s*)gh\s+pr\s+create\b")

# The branch diff is the whole development branch, not one commit, so it needs
# the CI-sized budget from TASK-73 rather than judge.max_diff_bytes.
CI_DIFF_BUDGET = 33_554_432

#: Seconds kept back from the runner budget for this module's own work: reading
#: the manifest, parsing the verdict, rendering the reason. Every subprocess
#: shares what is left.
GUARD_OVERHEAD_S = 1

#: Below this a subprocess cannot usefully start, so the guard stops instead of
#: launching one it will kill immediately.
MIN_SUBPROCESS_S = 1

#: Used only when the manifest cannot be read. Deliberately small: an unknown
#: budget is not a licence to take an unbounded one.
FALLBACK_BUDGET_S = 4


class Deadline:
    """One budget for the whole guard, spent down by each subprocess.

    Deriving the judge timeout alone was not enough, and the sweep that found
    the rest is the reason this class exists. Every call site carried its own
    constant -- `git diff` at 60 s, five `base_ref` probes at 10 s each -- so the
    worst case was 114 s of subprocess inside a 5 s budget, all of it invisible
    because the client kills the process before any of the fail-open branches
    run.

    A deadline makes the bound structural rather than a set of numbers somebody
    has to keep in agreement. `remaining()` is what is left of the budget; a
    call site that would start with nothing left gets `None` and the guard stops
    with a reason instead of launching a subprocess it is about to kill.
    """

    def __init__(self, seconds: int) -> None:
        self._end = time.monotonic() + seconds

    def remaining(self) -> Optional[int]:
        left = int(self._end - time.monotonic())
        return left if left >= MIN_SUBPROCESS_S else None


def guard_budget_s() -> int:
    """How long the whole guard may run, from the budget the client enforces.

    This was a standalone 120 s constant while `hooks/manifest.json` declared
    `runner_timeout_sec: 5` for `pr-create`, and the two could not both be
    right. The client kills the hook at its own timeout, so a judge allowed
    twenty-four times that never reaches the `except SubprocessError` branch
    below -- the process dies mid-call and the carefully written fail-open path
    never runs. The user sees nothing at all, which is indistinguishable from a
    clean branch.

    Deriving it removes the possibility of disagreement: whoever changes the
    manifest changes this, and a fail-open stays something this module does
    rather than something that happens to it.

    Note what this does not do. A 5 s budget cannot hold an LLM judge pass, so a
    project that has enabled one will see this time out and allow, with the
    reason stated. That is the honest outcome of the budget `hooks/manifest.json`
    declares for this event, and moving the budget is a decision rather than a
    patch.
    """
    manifest = Path(__file__).resolve().parent / "manifest.json"
    try:
        events = json.loads(manifest.read_text(encoding="utf-8"))["events"]
        runner = next(
            event["runner_timeout_sec"]
            for event in events
            if event.get("id") == "pr-create"
        )
    except (OSError, ValueError, KeyError, TypeError, StopIteration):
        return FALLBACK_BUDGET_S
    if not isinstance(runner, int) or runner <= 0:
        return FALLBACK_BUDGET_S
    return max(MIN_SUBPROCESS_S, runner - GUARD_OVERHEAD_S)


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


def base_ref(cwd: Path, deadline: "Deadline") -> Optional[str]:
    """The branch this PR would target, from the repository's own configuration."""
    for argv in (
        ["git", "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"],
        ["git", "config", "--get", "init.defaultBranch"],
    ):
        left = deadline.remaining()
        if left is None:
            return None
        try:
            result = _run(argv, cwd, left)
        except (OSError, subprocess.SubprocessError):
            continue
        value = (result.stdout or "").strip()
        if result.returncode == 0 and value:
            return value.split("/")[-1]
    for candidate in ("main", "master", "dev"):
        try:
            left = deadline.remaining()
            if left is None:
                return None
            probe = _run(["git", "rev-parse", "--verify", f"origin/{candidate}"], cwd, left)
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
    deadline = Deadline(guard_budget_s())
    base = base_ref(cwd, deadline)
    if not base:
        return {"decision": "allow", "reason": "no base branch to compare against", "checked": False}

    left = deadline.remaining()
    if left is None:
        return {"decision": "allow", "reason": "ran out of budget before the diff", "checked": False}
    try:
        diff = _run(
            ["git", "diff", "--unified=0", f"origin/{base}...HEAD"], cwd, left
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"decision": "allow", "reason": f"git diff failed ({exc})", "checked": False}
    if diff.returncode != 0:
        return {"decision": "allow", "reason": "git diff failed", "checked": False}
    if not (diff.stdout or "").strip():
        return {"decision": "allow", "reason": "empty branch diff", "checked": True}

    import sys

    left = deadline.remaining()
    if left is None:
        return {"decision": "allow", "reason": "ran out of budget before the judge", "checked": False}
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
            left,
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
