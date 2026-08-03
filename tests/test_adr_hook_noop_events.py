"""The end-of-work hooks are silent on purpose (TASK-86, ADR-019).

`Stop`, `SubagentStop` and `SessionEnd` are accepted by the runner and answered
with nothing. That is where "work finished -- were decisions made?" would live,
so the silence needs a reason attached to it, or the next reader will read three
no-ops as an unfinished feature.

The reason is in ADR-019: answering that question honestly means reading a whole
session, which means a model, and a session ends when nobody is watching. A hook
that spends there spends on an event the user cannot see fire and cannot refuse,
which contradicts every other paying path in this toolkit.

These tests hold the silence in place. A change that wires one of these events up
fails here first and has to go back to the ADR.
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_CORE = REPO_ROOT / "hooks" / "adr_hook_core.py"
HOOK_ENTRY = REPO_ROOT / "hooks" / "adr-hook.py"
MANIFEST = REPO_ROOT / "hooks" / "manifest.json"
ADR_019 = (
    REPO_ROOT / "docs" / "adr"
    / "ADR-019-keep-the-end-of-session-hooks-deliberately-silent.md"
)

END_OF_WORK = ("stop", "subagentstop", "sessionend")


def _core():
    name = "adr_hook_core_noop"
    loader = importlib.machinery.SourceFileLoader(name, str(HOOK_CORE))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


core = _core()


@pytest.mark.parametrize("event", END_OF_WORK)
def test_the_end_of_work_events_stay_silent(event):
    assert event in core.NOOP_EVENTS, (
        f"{event} left NOOP_EVENTS. ADR-019 keeps it silent because answering "
        "'were decisions made?' needs a model, and a session ends when nobody "
        "is watching. Supersede that decision before wiring this up."
    )


def test_the_silence_carries_its_reason_in_the_source():
    """A reader who never opens the ADR should still inherit the argument."""
    text = HOOK_CORE.read_text(encoding="utf-8")
    start = text.index("NOOP_EVENTS = {")
    preamble = text[max(0, start - 900):start]

    assert "deliberately" in preamble or "decision, not an oversight" in preamble, (
        "NOOP_EVENTS lost its rationale comment; an undocumented no-op is "
        "indistinguishable from an unfinished feature"
    )
    assert "ADR-019" in text[max(0, start - 900):start + 1400]


@pytest.mark.parametrize("event", END_OF_WORK)
def test_no_client_registers_an_end_of_work_event(event):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    registered = {
        str(native).casefold()
        for entry in manifest["events"]
        for native in entry["clients"].values()
        if native
    }

    assert event not in registered, (
        f"a client now registers {event}; ADR-019 says no client may while it stands"
    )


@pytest.mark.parametrize("event", ["Stop", "SubagentStop", "SessionEnd"])
def test_the_runner_answers_nothing_and_exits_zero(event):
    """Silence, not an error: an unhandled event must never break a session."""
    result = subprocess.run(
        [sys.executable, str(HOOK_ENTRY), "--client", "claude-code-cli",
         "--event", event],
        input=json.dumps({"session_id": "t", "cwd": str(REPO_ROOT)}),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(REPO_ROOT),
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""


def test_the_record_and_this_anchor_still_agree():
    text = ADR_019.read_text(encoding="utf-8")

    assert "NOOP_EVENTS" in text
    for event in END_OF_WORK:
        assert event in text.casefold()
    # The question is not abandoned, it moves somewhere the user is present.
    assert "adr-audit" in text
