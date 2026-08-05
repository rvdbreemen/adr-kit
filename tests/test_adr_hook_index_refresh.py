"""The hook regenerates a stale ADR index, where it may and can afford it.

An agent that writes `docs/adr/ADR-NNN.md` directly -- the common case in a
harness -- leaves the generated index stale. `query_adr_context` then raises
`IndexQueryError`, `_query` swallows it into an empty list, and ADR injection
goes dark for the rest of the session with no message at all. Silence is the
defect: an empty answer reads exactly like "no ADR was relevant" (ADR-021).

This reverses the read-only property `hooks/adr_hook_core.py` documents in its
own first line, which is why the ADR states it and why these tests pin the
limits it accepts.

Gate anchor for ADR-021: adr-hook-index-refresh-v1
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _core():
    hooks = str(ROOT / "hooks")
    if hooks not in sys.path:
        sys.path.insert(0, hooks)
    spec = importlib.util.spec_from_file_location(
        "adr_hook_core_refresh_under_test", ROOT / "hooks" / "adr_hook_core.py"
    )
    module = importlib.util.module_from_spec(spec)
    # Registered before exec: @dataclass resolves its own module through
    # sys.modules[cls.__module__], and an unregistered name makes that None.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CORE = _core()

_ADR = """---
id: "ADR-001"
title: "Serve the Retrieval Layer From One Store"
status: "Accepted"
date: "2026-08-05"
binding: false
gate: null
documents_shipped: false
verified_in: []
supersedes: []
superseded_by: null
format: "madr"
context_scope: "global"
topics: ["retrieval"]
components: ["src"]
---

# ADR-001 Serve the Retrieval Layer From One Store

## Status

Accepted, 2026-08-05.

## Context and Problem Statement

The retrieval layer needs one store.

## Decision Drivers

* Local-first.

## Considered Options

* One store.
* Two stores.

## Decision Outcome

Chosen option: **one store**, because two would have to be kept in agreement.

## Consequences

### Positive

* One thing to reason about.

### Negative

* A single point of failure.

## Related Decisions

* None.

## References

* src/retrieval.py
"""


def _workspace(tmp_path: Path) -> Path:
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-001-serve-the-retrieval-layer-from-one-store.md").write_text(
        _ADR, encoding="utf-8"
    )
    subprocess.run(
        [sys.executable, str(ROOT / "bin" / "adr-index"), str(adr_dir)],
        capture_output=True,
        check=True,
    )
    return tmp_path


def _make_stale(workspace: Path) -> Path:
    """Add an ADR newer than every index artefact, the way an agent would."""
    adr_dir = workspace / "docs" / "adr"
    new = adr_dir / "ADR-002-add-a-cache.md"
    new.write_text(
        _ADR.replace('id: "ADR-001"', 'id: "ADR-002"')
        .replace("ADR-001 Serve", "ADR-002 Add")
        .replace("Serve the Retrieval Layer From One Store", "Add a Cache"),
        encoding="utf-8",
    )
    # Backdate the index rather than future-dating the ADR. Both make the index
    # read as stale, but a future-dated ADR stays newer than anything written
    # afterwards -- including the regeneration -- so the fixture would report
    # failure for a state the feature had actually fixed.
    past = time.time() - 60
    for name in ("README.md", "ADR-INDEX.md", "ADR-INDEX.json"):
        os.utime(adr_dir / name, (past, past))
    return new


def test_a_session_event_regenerates_a_stale_index(tmp_path):
    """AC#2 and AC#6: write an ADR, submit a prompt, see it in the same session."""
    workspace = _workspace(tmp_path)
    _make_stale(workspace)

    index = workspace / "docs" / "adr" / "ADR-INDEX.json"
    assert "ADR-002" not in index.read_text(encoding="utf-8")

    notice = CORE.refresh_index(workspace, "UserPromptSubmit")

    assert notice == "", notice
    assert "ADR-002" in index.read_text(encoding="utf-8")


def test_the_edit_tier_reads_only_and_says_the_index_is_stale(tmp_path):
    """AC#3. The 100 ms events cannot hold a render, and must not go silent."""
    workspace = _workspace(tmp_path)
    _make_stale(workspace)
    index = workspace / "docs" / "adr" / "ADR-INDEX.json"
    before = index.read_text(encoding="utf-8")

    for event in ("PreToolUse", "PostToolUse"):
        notice = CORE.refresh_index(workspace, event)
        assert "stale" in notice.lower()
        assert "bin/adr-index" in notice
    assert index.read_text(encoding="utf-8") == before, "the edit tier wrote"


def test_a_fresh_index_produces_no_notice_and_no_write(tmp_path):
    workspace = _workspace(tmp_path)
    index = workspace / "docs" / "adr" / "ADR-INDEX.json"
    before = index.stat().st_mtime_ns

    assert CORE.refresh_index(workspace, "SessionStart") == ""
    assert index.stat().st_mtime_ns == before


def test_a_contended_lock_reads_rather_than_waits(tmp_path):
    """AC#4. The loser continues; it never blocks, waits or retries.

    Waiting would spend a budget it cannot recover on work another session is
    already doing, and the client kills the hook at its own bound regardless.
    """
    workspace = _workspace(tmp_path)
    _make_stale(workspace)
    lock = workspace / "docs" / "adr" / ".adr-index.lock"
    lock.write_text("held by another session", encoding="utf-8")
    index = workspace / "docs" / "adr" / "ADR-INDEX.json"
    before = index.read_text(encoding="utf-8")

    started = time.monotonic()
    notice = CORE.refresh_index(workspace, "SessionStart")
    elapsed = time.monotonic() - started

    assert "stale" in notice.lower()
    assert index.read_text(encoding="utf-8") == before
    assert elapsed < 1.0, f"the loser waited {elapsed:.2f}s"


def test_the_lock_is_released_so_the_next_session_can_render(tmp_path):
    """A lock left behind would turn one crash into a permanently stale index."""
    workspace = _workspace(tmp_path)
    _make_stale(workspace)

    CORE.refresh_index(workspace, "SessionStart")

    assert not (workspace / "docs" / "adr" / ".adr-index.lock").exists()


def test_a_set_too_large_for_the_budget_degrades_to_a_nudge(tmp_path, monkeypatch):
    """AC#5. Bail out before starting, not by being killed mid-write.

    The client kills the hook at its own timeout, and a render interrupted
    halfway leaves the artefacts disagreeing with each other -- worse than the
    staleness it set out to fix.
    """
    workspace = _workspace(tmp_path)
    _make_stale(workspace)
    index = workspace / "docs" / "adr" / "ADR-INDEX.json"
    before = index.read_text(encoding="utf-8")

    import adr_index_core

    monkeypatch.setattr(adr_index_core, "projected_render_ms", lambda _dir: 10_000.0)

    notice = CORE.refresh_index(workspace, "SessionStart")

    assert "stale" in notice.lower()
    assert index.read_text(encoding="utf-8") == before


def test_the_budget_comes_from_the_manifest_not_a_constant():
    """Whoever changes the manifest changes this; they cannot drift apart."""
    manifest = json.loads(
        (ROOT / "hooks" / "manifest.json").read_text(encoding="utf-8")
    )
    declared = {
        event["id"]: event["latency"]["p50_ms"] for event in manifest["events"]
    }
    assert CORE._event_budget_ms("SessionStart") == declared["session-start"]
    assert CORE._event_budget_ms("UserPromptSubmit") == declared["user-prompt-submit"]


def test_only_the_two_session_events_may_write():
    """AC#2's other half, read off the constant rather than inferred."""
    assert CORE.REFRESHING_EVENTS == {"SessionStart", "UserPromptSubmit"}


def test_a_failing_regeneration_nudges_rather_than_raising(tmp_path, monkeypatch):
    """Fail-open is the contract for every path in this file.

    Driven by making the generator raise, not by writing a malformed file: the
    generator treats a file without frontmatter as "not an ADR" rather than as
    an error, so that fixture would prove the wrong thing. What matters is that
    an exception anywhere in here becomes a message and never an exit code.
    """
    workspace = _workspace(tmp_path)
    _make_stale(workspace)

    import adr_index_core

    def boom(*args, **kwargs):
        raise OSError("disk went away mid-render")

    monkeypatch.setattr(adr_index_core, "regenerate_index", boom)

    notice = CORE.refresh_index(workspace, "SessionStart")

    assert "stale" in notice.lower()
    # And the lock must not survive the failure.
    assert not (workspace / "docs" / "adr" / ".adr-index.lock").exists()


@pytest.mark.parametrize("client", ["codex", "copilot"])
def test_both_mirrors_carry_the_refresh(client):
    core = (ROOT / client / "hooks" / "adr_hook_core.py").read_text(encoding="utf-8")
    assert "def refresh_index(" in core
    index_core = (ROOT / client / "bin" / "adr_index_core.py").read_text(encoding="utf-8")
    assert "def regenerate_index(" in index_core
