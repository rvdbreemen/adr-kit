"""Judge the branch before the pull request exists (spec R2, TASK-76)."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _guard():
    name = "adr_pr_guard"
    loader = importlib.machinery.SourceFileLoader(name, str(REPO_ROOT / "hooks" / f"{name}.py"))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


guard = _guard()


@pytest.mark.parametrize(
    "command",
    [
        "gh pr create",
        "gh pr create --fill",
        "git push && gh pr create --base main",
        "cd repo; gh  pr   create",
    ],
)
def test_it_recognises_a_pr_being_opened(command):
    assert guard.looks_like_pr_create(command) is True


@pytest.mark.parametrize(
    "command",
    [
        "gh pr list",
        "gh pr view 42",
        "gh pr checkout 7",
        "echo 'run gh pr create when ready'",
        "git commit -m 'gh pr create later'",
        "ghost pr create",
    ],
)
def test_it_does_not_fire_on_a_near_miss(command):
    assert guard.looks_like_pr_create(command) is False, (
        "a guard that blocks unrelated commands is worse than no guard"
    )


def test_a_missing_judge_lets_the_command_through(tmp_path):
    """Fail open on tooling: a check that cannot run must not pretend it did."""
    verdict = guard.judge_branch(tmp_path, tmp_path / "docs" / "adr", tmp_path / "nope")

    assert verdict["decision"] == "allow"
    assert verdict["checked"] is False


def test_a_configuration_error_does_not_block(monkeypatch, tmp_path):
    """Exit 2 is a fact about the invocation, not about the code."""
    monkeypatch.setattr(guard, "base_ref", lambda cwd, deadline: "main")
    monkeypatch.setattr(guard.shutil, "which", lambda name: "/usr/bin/git")

    class _Result:
        def __init__(self, code, out="", err=""):
            self.returncode, self.stdout, self.stderr = code, out, err

    calls = {"n": 0}

    def fake_run(argv, cwd, timeout, stdin_text=None):
        calls["n"] += 1
        if argv[0] == "git":
            return _Result(0, "diff --git a/x b/x\n+line\n")
        return _Result(2, "", "diff exceeds --max-diff-bytes")

    monkeypatch.setattr(guard, "_run", fake_run)
    judge = tmp_path / "adr-judge"
    judge.write_text("#!/usr/bin/env python3\n", encoding="utf-8")

    verdict = guard.judge_branch(tmp_path, tmp_path / "docs" / "adr", judge)

    assert verdict["decision"] == "allow"
    assert "could not complete" in verdict["reason"]


def test_a_violation_denies_and_names_the_adr(monkeypatch, tmp_path):
    monkeypatch.setattr(guard, "base_ref", lambda cwd, deadline: "main")
    monkeypatch.setattr(guard.shutil, "which", lambda name: "/usr/bin/git")

    class _Result:
        def __init__(self, code, out="", err=""):
            self.returncode, self.stdout, self.stderr = code, out, err

    payload = (
        '{"findings": [{"severity": "violation", "adr": "ADR-042", '
        '"path": "src/x.py", "line": 12, "message": "no ArduinoJson"}]}'
    )

    def fake_run(argv, cwd, timeout, stdin_text=None):
        if argv[0] == "git":
            return _Result(0, "diff --git a/x b/x\n+line\n")
        return _Result(1, payload)

    monkeypatch.setattr(guard, "_run", fake_run)
    judge = tmp_path / "adr-judge"
    judge.write_text("#!/usr/bin/env python3\n", encoding="utf-8")

    verdict = guard.judge_branch(tmp_path, tmp_path / "docs" / "adr", judge)

    assert verdict["decision"] == "deny"
    assert "ADR-042" in verdict["reason"]
    assert "src/x.py:12" in verdict["reason"]
    assert "supersede" in verdict["reason"], "a block must name the way out"


def test_the_guard_uses_the_ci_sized_budget_not_the_commit_one():
    assert guard.CI_DIFF_BUDGET == 33_554_432


def test_the_retrieval_core_still_imports_no_subprocess():
    """The guard lives outside adr_hook_core precisely so this stays true."""
    text = (REPO_ROOT / "hooks" / "adr_hook_core.py").read_text(encoding="utf-8")
    assert "import subprocess" not in text


def test_the_pr_workflow_template_ships():
    template = REPO_ROOT / "templates" / "github-workflows" / "adr-judge.yml"
    text = template.read_text(encoding="utf-8")

    assert "pull_request" in text
    assert "fetch-depth: 0" in text
    assert "max-diff-bytes" in text


# ---------------------------------------------------------------------------
# The judge timeout is derived, not declared twice (Copilot review, PR #58)
# ---------------------------------------------------------------------------

def _guard_module(directory: str = "hooks"):
    import importlib.machinery
    import importlib.util

    name = f"adr_pr_guard_{directory.replace('/', '_')}"
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    loader = importlib.machinery.SourceFileLoader(
        name, str(REPO_ROOT / directory / "adr_pr_guard.py")
    )
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def test_the_guard_budget_stays_under_the_runner_budget():
    """Numbers that could disagree, and did: 120 s against a 5 s budget.

    The client kills the hook at its own timeout, so a judge allowed
    twenty-four times that never reaches the fail-open branch -- the process
    dies mid-call and the user sees nothing, which is indistinguishable from a
    clean branch.
    """
    manifest = json.loads(
        (REPO_ROOT / "hooks" / "manifest.json").read_text(encoding="utf-8")
    )
    runner = next(
        event["runner_timeout_sec"]
        for event in manifest["events"]
        if event["id"] == "pr-create"
    )

    assert _guard_module().guard_budget_s() < runner


@pytest.mark.parametrize("tree", ["hooks", "codex/hooks", "copilot/hooks"])
def test_every_client_tree_derives_the_same_budget(tree):
    """A mirror without the manifest silently falls back to a constant.

    The constant matches today and stops matching the moment somebody changes
    the budget -- the same drift, reintroduced one directory over.
    """
    if not (REPO_ROOT / tree / "adr_pr_guard.py").is_file():
        pytest.skip(f"{tree} ships no guard")

    assert (REPO_ROOT / tree / "manifest.json").is_file(), (
        f"{tree} cannot derive its budget"
    )
    assert _guard_module(tree).guard_budget_s() == _guard_module().guard_budget_s()


def test_an_unreadable_manifest_yields_a_small_budget_not_an_unbounded_one(
    tmp_path, monkeypatch
):
    """An unknown budget is not a licence to take an unbounded one."""
    guard = _guard_module()
    broken = tmp_path / "manifest.json"
    broken.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(
        guard, "__file__", str(tmp_path / "adr_pr_guard.py"), raising=False
    )

    assert guard.guard_budget_s() == guard.FALLBACK_BUDGET_S
    assert guard.FALLBACK_BUDGET_S <= 5


def test_the_timeout_leaves_room_for_the_guards_own_work():
    """Reading the manifest, running git diff and rendering all cost time.

    Handing the judge the entire budget means the client kills us mid-render.
    """
    guard = _guard_module()

    assert guard.GUARD_OVERHEAD_S >= 1


def test_no_subprocess_carries_its_own_hardcoded_timeout():
    """Deriving one timeout was not enough, which is how this test exists.

    A sweep found `git diff` at 60 s and up to five `base_ref` probes at 10 s
    each, all inside the same 5 s budget: 114 s worst case, every second of it
    invisible because the client kills the process before any fail-open branch
    runs. A deadline makes the bound structural; this asserts nobody puts a
    constant back.
    """
    import re

    source = (REPO_ROOT / "hooks" / "adr_pr_guard.py").read_text(encoding="utf-8")
    offenders = re.findall(r"_run\([^)]*?,\s*cwd,\s*(\d+)", source, re.DOTALL)

    assert not offenders, f"hardcoded subprocess timeout(s): {offenders}"


def test_an_exhausted_deadline_stops_rather_than_starting_a_subprocess():
    """Below the minimum a subprocess cannot usefully start.

    Launching one anyway means spending the last of the budget on a call that
    gets killed, instead of returning the allow the caller can act on.
    """
    guard = _guard_module()

    assert guard.Deadline(0).remaining() is None
    assert guard.Deadline(guard.MIN_SUBPROCESS_S - 1).remaining() is None
    assert guard.Deadline(guard.MIN_SUBPROCESS_S).remaining() == guard.MIN_SUBPROCESS_S


def test_the_whole_guard_is_bounded_by_one_budget():
    """Every call site draws from the same deadline, so the total is the budget.

    Four subprocesses each honouring a limit is not the same as four
    subprocesses that together honour one.
    """
    guard = _guard_module()
    deadline = guard.Deadline(guard.guard_budget_s())

    first = deadline.remaining()
    assert first is not None and first <= guard.guard_budget_s()
