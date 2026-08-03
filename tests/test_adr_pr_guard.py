"""Judge the branch before the pull request exists (spec R2, TASK-76)."""

from __future__ import annotations

import importlib.machinery
import importlib.util
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
    monkeypatch.setattr(guard, "base_ref", lambda cwd: "main")
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
    monkeypatch.setattr(guard, "base_ref", lambda cwd: "main")
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
