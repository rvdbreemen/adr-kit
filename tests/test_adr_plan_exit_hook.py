"""Leaving plan mode is a decision point (spec R3, TASK-75).

The plan is complete and no code exists yet. It is the cheapest moment to notice
a missing decision, and the only one where the answer can still shape the
implementation instead of justifying it afterwards.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _core():
    sys.path.insert(0, str(REPO_ROOT / "bin"))
    name = "adr_hook_core_plan"
    loader = importlib.machinery.SourceFileLoader(
        name, str(REPO_ROOT / "hooks" / "adr_hook_core.py")
    )
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


core = _core()


def _envelope(tool_input: dict, tool: str = "ExitPlanMode"):
    return core.normalize(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": tool,
            "tool_input": tool_input,
            "cwd": str(REPO_ROOT),
        },
        "claude-code-cli",
        None,
    )


def test_leaving_plan_mode_injects_the_governing_adrs():
    text, kind = core.evaluate(_envelope({"plan": "Change the retrieval interface and add a dependency."}))

    assert kind == "plan-exit"
    assert "govern this plan" in text


def test_it_asks_the_question_the_moment_exists_for():
    text, _ = core.evaluate(_envelope({"plan": "Introduce a new caching layer."}))

    assert "does this plan make an architectural decision" in text
    assert "/adr-kit:grill" in text, "the question must come with the way to answer it"


def test_it_is_a_question_and_never_a_block():
    """A gate here would teach people to write an empty ADR to get past it."""
    text, kind = core.evaluate(_envelope({"plan": "Anything at all."}))

    payload = json.dumps({"text": text, "kind": kind})
    for blocking in ("deny", "block", "exit 2", "refuse"):
        assert blocking not in payload.lower()


def test_an_empty_plan_stays_silent():
    """No plan, no question.

    Asserted on the subject rather than on the whole tuple. Since ADR-021 the
    evaluator may prepend a staleness notice on any event that finds the index
    stale, and this fixture runs against the live repository -- so an unrelated
    ADR edit made without reindexing would fail this test for a reason that has
    nothing to do with empty plans.
    """
    text, _ = core.evaluate(_envelope({}))

    assert "does this plan make an architectural decision" not in text
    assert "/adr-kit:grill" not in text


def test_a_write_tool_still_takes_the_edit_path():
    """The new matcher must not swallow the fail-closed edit floor of ADR-004."""
    text, kind = core.evaluate(
        _envelope({"file_path": str(REPO_ROOT / "bin" / "adr-judge")}, tool="Edit")
    )

    assert kind == "pre-edit"


def test_the_manifest_registers_the_event_and_admits_where_it_does_not_exist():
    manifest = json.loads((REPO_ROOT / "hooks" / "manifest.json").read_text(encoding="utf-8"))
    event = next(item for item in manifest["events"] if item["id"] == "plan-exit")

    assert event["matcher"] == "ExitPlanMode"
    assert event["clients"]["claude-code-cli"] == "PreToolUse"
    # Codex and Copilot expose no plan transition. Recording null is the honest
    # answer; inventing an event name would be a parity nobody could rely on.
    assert event["clients"]["codex-cli"] is None
    assert event["clients"]["github-copilot-cli"] is None


def test_the_budget_matches_the_other_pre_tool_hooks():
    manifest = json.loads((REPO_ROOT / "hooks" / "manifest.json").read_text(encoding="utf-8"))
    plan = next(item for item in manifest["events"] if item["id"] == "plan-exit")
    pre_edit = next(item for item in manifest["events"] if item["id"] == "pre-tool-use")

    # Not equality. Both dispatch from PreToolUse, so plan-exit may never be
    # given LESS room than the edit tier it shares that dispatch with. It is
    # allowed more, and measurement says it needs it: plan-exit renders the
    # decision prompt on top of the retrieval both do, and costs 454 ms p50
    # against 297 ms (ADR-030). Asserting equality was fair while both carried a
    # copied 100 ms; once the numbers were measured it forced one of them to be
    # wrong.
    assert plan["latency_budget_ms"] >= pre_edit["latency_budget_ms"]
