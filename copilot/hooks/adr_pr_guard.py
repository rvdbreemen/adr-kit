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

#: Seconds kept back from the runner budget for the time the guard does not
#: control or measure: interpreter start, imports and the stdin read before
#: `judge_branch` is reached, plus parsing the verdict and rendering the reason
#: afterwards. Measured end to end on the Windows certification machine, a hook
#: process that does no subprocess work costs 218 ms p50 and 257 ms p95, so one
#: second is the reserve with room rather than a guess.
#:
#: The deadline deliberately starts at `judge_branch` rather than at import. An
#: import-time origin measures the startup exactly and makes the module usable
#: only once per process -- correct for a hook, wrong for anything that calls it
#: twice, and the second call silently gets no budget at all. Paying for the
#: startup out of a constant keeps the bound without that trap.
GUARD_OVERHEAD_S = 1

#: Below this a subprocess cannot usefully start, so the guard stops instead of
#: launching one it will kill immediately.
MIN_SUBPROCESS_S = 1

#: Share of the remaining budget `git diff` may take. The judge is the part that
#: produces a verdict, so it keeps the majority; reading the diff is setup.
DIFF_BUDGET_SHARE = 0.4

#: Used when the manifest cannot be read or declares no budget for this event.
#: One second, because that is what the generator writes into hooks.json when
#: `runner_timeout_sec` is absent (scripts/client_generation_artifacts.py), and
#: that is the number the client actually enforces. Five of the eight manifest
#: events omit the key today, so this is the live path rather than a corner.
FALLBACK_BUDGET_S = 1

#: The generator validates `runner_timeout_sec` as an int in 1..30 and refuses
#: anything else. The guard reads the same field at run time from a file that
#: may have been edited or shipped out of step with hooks.json, so it applies
#: the same bounds -- otherwise `runner_timeout_sec: 600` hands the guard a
#: 599 s deadline against whatever the client actually enforces, which is the
#: original defect restored at a larger multiple.
MAX_RUNNER_S = 30


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

    def __init__(self, seconds: int, start: Optional[float] = None) -> None:
        self._end = (time.monotonic() if start is None else start) + seconds

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
    if isinstance(runner, bool) or not isinstance(runner, int):
        return FALLBACK_BUDGET_S
    if not 1 <= runner <= MAX_RUNNER_S:
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


def _nudge(cwd: Path, adr_dir: Path, suggest: Path, diff_text: str, left: int) -> str:
    """The missing-decision half of R2, asked at the same moment as the verdict.

    Advisory by construction: this returns text or nothing, and no caller may
    turn it into a denial (ADR-024). A suggestion is a question about a decision
    nobody recorded, and blocking on one teaches people to write an empty ADR to
    get past it -- the failure mode that produced six rule-less Enforcement
    blocks in this very repository.

    It reuses the diff the judge already read and what is left of the same
    Deadline. A second `git diff` here would spend the budget twice on the same
    bytes, and the branches with the largest diffs are the ones most worth
    asking about.
    """
    import sys

    try:
        result = _run(
            [
                sys.executable, str(suggest),
                "--diff", "-",
                "--adr-dir", str(adr_dir),
                # Same reason as the judge's: killing the child does not reach
                # the model CLI it spawned.
                "--llm-timeout", str(left),
            ],
            cwd,
            left,
            stdin_text=diff_text,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    lines = [
        line
        for line in (result.stdout or "").splitlines()
        if line.startswith("[adr-suggest] This change") or line.startswith("[adr-suggest]   ")
    ]
    return "\n".join(lines)


def judge_branch(
    cwd: Path, adr_dir: Path, judge: Path, suggest: Optional[Path] = None
) -> Dict:
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
    # Capped rather than given the remainder. Handing `git diff` everything left
    # lets a large branch consume the whole budget and starve the judge -- and
    # the branches with the largest diffs are the ones most worth checking, so
    # the failure would scale with how much it matters.
    try:
        diff = _run(
            ["git", "diff", "--unified=0", f"origin/{base}...HEAD"],
            cwd,
            max(MIN_SUBPROCESS_S, int(left * DIFF_BUDGET_SHARE)),
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
                # Bound the child's own model call by what is left of our
                # budget. Without it adr-judge starts an LLM call with a 120 s
                # default, and subprocess timeouts do not reach grandchildren:
                # killing the judge leaves the model CLI running, billing a
                # verdict nobody will read.
                "--llm-timeout", str(left),
                "--json",
            ],
            cwd,
            left,
            stdin_text=diff.stdout,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"decision": "allow", "reason": f"judge did not run ({exc})", "checked": False}

    def _with_nudge(result: Dict) -> Dict:
        """Attach the advisory nudge, never touching the decision."""
        if suggest is None or not suggest.is_file():
            return result
        left_now = deadline.remaining()
        if left_now is None:
            return result
        text = _nudge(cwd, adr_dir, suggest, diff.stdout, left_now)
        if text:
            result["nudge"] = text
        return result

    if verdict.returncode == 0:
        return _with_nudge(
            {"decision": "allow", "reason": "no violations on the branch", "checked": True}
        )
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
    return _with_nudge({
        "decision": "deny",
        "reason": _explain(findings, base),
        "checked": True,
        "violations": findings,
    })


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
