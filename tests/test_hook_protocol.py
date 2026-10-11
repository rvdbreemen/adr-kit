"""Normalized hook protocol, client adapters, and fail-open behavior."""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "hooks"
if str(HOOKS) not in sys.path:
    sys.path.insert(0, str(HOOKS))

from adapters import ADAPTERS
from adr_hook_core import (
    MAX_CONTEXT_CHARS,
    MAX_INPUT_BYTES,
    duplicate_event,
    evaluate,
    parse_payload,
)


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "Project with spaces \u2603"
    adr = project / "docs" / "adr"
    adr.mkdir(parents=True)
    (adr / "ADR-INDEX.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "adrs": [
                    {
                        "id": "ADR-001",
                        "title": "Use bounded hooks",
                        "path": "ADR-001-hooks.md",
                        "format": "madr",
                        "status": "Accepted",
                        "date": "2026-07-23",
                        "decision_summary": "Hook work must remain deterministic and fail open.",
                        "scope": {"path_globs": ["src/hooks/**"]},
                        "metadata": {},
                        "context_scope": "global",
                        "topics": ["deterministic lifecycle hooks"],
                        "aliases": [],
                        "components": ["hook runtime"],
                        "symbols": [],
                        "decision_contract": {},
                    },
                    {
                        "id": "ADR-002",
                        "title": "Use SQLite",
                        "path": "ADR-002-storage.md",
                        "format": "madr",
                        "status": "Accepted",
                        "date": "2026-07-23",
                        "decision_summary": "Store durable records in SQLite.",
                        "scope": {"path_globs": ["src/store/**"]},
                        "metadata": {},
                        "context_scope": "selective",
                        "topics": ["sqlite storage"],
                        "aliases": [],
                        "components": ["storage"],
                        "symbols": [],
                        "decision_contract": {},
                    },
                    {
                        "id": "ADR-003",
                        "title": "Candidate lifecycle hooks",
                        "path": "ADR-003-proposal.md",
                        "format": "madr",
                        "status": "Proposed",
                        "date": "2026-07-23",
                        "decision_summary": "Candidate deterministic lifecycle hook behavior.",
                        "scope": {"path_globs": ["**"]},
                        "metadata": {},
                        "context_scope": "selective",
                        "topics": ["deterministic lifecycle hooks"],
                        "aliases": [],
                        "components": ["hook runtime"],
                        "symbols": [],
                        "decision_contract": {},
                    },
                ],
                "relationships": [],
            }
        ),
        encoding="utf-8",
    )
    return project


@pytest.mark.parametrize(
    ("native", "expected"),
    [
        ("SessionStart", "SessionStart"),
        ("sessionStart", "SessionStart"),
        ("userPromptSubmitted", "UserPromptSubmit"),
        ("PreToolUse", "PreToolUse"),
    ],
)
def test_native_event_naming_is_normalized(tmp_path, native, expected):
    project = _project(tmp_path)
    envelope = parse_payload(
        json.dumps({"cwd": str(project), "hookEventName": native}).encode(),
        "github-copilot-cli",
    )
    assert envelope is not None
    assert envelope.event == expected


def test_prompt_ranking_is_deterministic_bounded_and_source_linked(tmp_path):
    project = _project(tmp_path)
    envelope = parse_payload(
        json.dumps(
            {
                "cwd": str(project),
                "hook_event_name": "UserPromptSubmit",
                "prompt": "Implement deterministic lifecycle hooks",
            }
        ).encode(),
        "codex-cli",
    )
    assert envelope
    first = evaluate(envelope)
    second = evaluate(envelope)
    assert first == second
    assert first[1] == "prompt"
    assert "ADR-001" in first[0]
    # R5: the prompt injection presents retrieval candidates and asks the model
    # to select, rather than asserting relevance on its behalf (TASK-156).
    assert "Accepted ADR candidates for this prompt" in first[0]
    assert "ADR-003" in first[0]
    assert "Proposed ADR candidates for this prompt" in first[0]
    assert "retrieval candidates, not confirmed matches" in first[0]
    assert "source: docs/adr/ADR-001-hooks.md" in first[0]
    assert len(first[0]) <= MAX_CONTEXT_CHARS


@pytest.mark.parametrize("tool", ["Edit", "MultiEdit", "Write", "apply_patch"])
def test_pre_edit_filters_write_aliases_and_resolves_safe_paths(tmp_path, tool):
    project = _project(tmp_path)
    envelope = parse_payload(
        json.dumps(
            {
                "cwd": str(project),
                "hook_event_name": "PreToolUse",
                "tool_name": tool,
                "tool_input": {"file_path": "src/hooks/runtime.py"},
            }
        ).encode(),
        "claude-code-cli",
    )
    assert envelope
    context, kind = evaluate(envelope)
    assert kind == "pre-edit"
    assert "ADR-001" in context
    assert "ADR-002" not in context

    hostile = parse_payload(
        json.dumps(
            {
                "cwd": str(project),
                "hook_event_name": "PreToolUse",
                "tool_name": tool,
                "tool_input": {"file_path": "../outside.py"},
            }
        ).encode(),
        "claude-code-cli",
    )
    assert hostile and evaluate(hostile) == ("", "noop")


# Codex and OpenCode never send a file path for an apply_patch edit: the paths
# are in the patch's header lines (DEF-31, DEF-38). Codex 0.162.1 puts the patch
# in tool_input.command; OpenCode 1.19.0 puts it in args.patchText, and its
# plugin forwards those args under an Edit tool name with Claude's adapter.
def _patch(*lines: str) -> str:
    return "\n".join(("*** Begin Patch", *lines, "*** End Patch"))


def _edit(project, tool_input, *, tool="apply_patch", client="codex-cli", event="PreToolUse"):
    envelope = parse_payload(
        json.dumps(
            {
                "cwd": str(project),
                "hook_event_name": event,
                "tool_name": tool,
                "tool_input": tool_input,
            }
        ).encode(),
        client,
    )
    assert envelope
    return evaluate(envelope)


@pytest.mark.parametrize(
    ("event", "kind"), [("PreToolUse", "pre-edit"), ("PostToolUse", "post-edit")]
)
def test_a_codex_patch_gets_the_decisions_for_the_file_it_updates(tmp_path, event, kind):
    project = _project(tmp_path)
    patch = _patch("*** Update File: src/hooks/runtime.py", "@@", "-a", "+b")

    context, actual = _edit(project, {"command": patch}, event=event)

    assert actual == kind
    assert "ADR-001" in context and "ADR-002" not in context


def test_an_opencode_patch_text_gets_the_decisions_too(tmp_path):
    project = _project(tmp_path)
    patch = _patch("*** Update File: src/hooks/runtime.py", "@@", "-a", "+b")

    context, kind = _edit(
        project, {"patchText": patch}, tool="Edit", client="claude-code-cli",
    )

    assert kind == "pre-edit" and "ADR-001" in context


def test_every_file_a_patch_adds_updates_deletes_or_moves_to_counts(tmp_path):
    project = _project(tmp_path)
    patch = _patch(
        "*** Add File: src/store/schema.sql",
        "+create table t (id int);",
        "*** Delete File: notes/old.txt",
        "*** Update File: notes/draft.py",
        "*** Move to: src/hooks/runtime.py",
        "@@",
        "-a",
        "+b",
    )

    context, _ = _edit(project, {"command": patch})

    assert "ADR-001" in context and "ADR-002" in context


def test_lines_inside_a_hunk_that_look_like_headers_are_not_paths(tmp_path):
    project = _project(tmp_path)
    patch = _patch(
        "*** Add File: notes/readme.md",
        "+*** Update File: src/store/db.py",
        "*** Update File: src/hooks/runtime.py",
        "@@",
        " *** Delete File: src/store/other.py",
        "-a",
        "+b",
    )

    context, _ = _edit(project, {"command": patch})

    assert "ADR-001" in context and "ADR-002" not in context


def test_patch_paths_outside_the_workspace_are_dropped(tmp_path):
    project = _project(tmp_path)
    outside = _patch("*** Update File: ../outside.py", "@@", "-a", "+b")
    assert _edit(project, {"command": outside}) == ("", "noop")

    mixed = _patch("*** Delete File: /etc/hosts", "*** Delete File: src/hooks/runtime.py")
    context, _ = _edit(project, {"command": mixed})
    assert "ADR-001" in context


def test_a_patch_touching_more_files_than_the_query_takes_still_gets_context(tmp_path):
    # query_adr_context refuses more than 32 path filters; passing them all
    # would raise, and the edit would get no context at all.
    project = _project(tmp_path)
    headers = ["*** Update File: src/hooks/runtime.py", "@@", "-a", "+b"]
    for number in range(40):
        headers += [f"*** Add File: notes/n{number}.txt", "+x"]

    context, _ = _edit(project, {"command": _patch(*headers)})

    assert "ADR-001" in context


def test_only_a_repeated_event_is_a_duplicate(tmp_path):
    # The dedupe keeps the session's previous event in the OS temp directory,
    # keyed by session id alone; it named neither the input nor the workspace.
    project = _project(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    session = f"dedupe-{uuid.uuid4()}"

    def event(target, cwd=project):
        return parse_payload(
            json.dumps(
                {
                    "cwd": str(cwd),
                    "hook_event_name": "PreToolUse",
                    "session_id": session,
                    "tool_name": "apply_patch",
                    "tool_input": {
                        "command": _patch(f"*** Update File: {target}", "@@", "-a", "+b")
                    },
                }
            ).encode(),
            "codex-cli",
        )

    try:
        assert not duplicate_event(event("src/hooks/runtime.py"))
        assert duplicate_event(event("src/hooks/runtime.py"))
        assert not duplicate_event(event("src/store/db.py"))
        assert not duplicate_event(event("src/store/db.py", cwd=other))
    finally:
        (Path(tempfile.gettempdir()) / f"adr-kit-hook-{session}.seen").unlink(
            missing_ok=True
        )


def test_copilot_uses_post_edit_backstop_not_false_pre_context(tmp_path):
    project = _project(tmp_path)
    base = {
        "cwd": str(project),
        "toolName": "Edit",
        "toolInput": {"filePath": "src/hooks/runtime.py"},
    }
    pre = parse_payload(
        json.dumps({**base, "hookEventName": "PreToolUse"}).encode(),
        "github-copilot-cli",
    )
    post = parse_payload(
        json.dumps({**base, "hookEventName": "PostToolUse"}).encode(),
        "github-copilot-cli",
    )
    assert pre and post
    pre_context, pre_kind = evaluate(pre)
    post_context, post_kind = evaluate(post)
    assert ADAPTERS["github-copilot-cli"]("PreToolUse", pre_context, pre_kind) == {}
    assert "additionalContext" in ADAPTERS["github-copilot-cli"](
        "PostToolUse", post_context, post_kind
    )


def test_subagent_and_precompact_preserve_only_selected_parent_context(tmp_path):
    project = _project(tmp_path)
    parent = "parent ADR bundle " * 1000
    subagent = parse_payload(
        json.dumps(
            {
                "cwd": str(project),
                "hook_event_name": "SubagentStart",
                "parent_context": parent,
            }
        ).encode(),
        "codex-cli",
    )
    compact = parse_payload(
        json.dumps(
            {
                "cwd": str(project),
                "hook_event_name": "PreCompact",
                "parent_context": parent,
            }
        ).encode(),
        "codex-cli",
    )
    assert subagent and compact
    assert evaluate(subagent)[0] == parent[:MAX_CONTEXT_CHARS]
    assert evaluate(compact)[0] == parent[:MAX_CONTEXT_CHARS]

    empty = parse_payload(
        json.dumps(
            {"cwd": str(project), "hook_event_name": "PreCompact"}
        ).encode(),
        "codex-cli",
    )
    assert empty and evaluate(empty) == ("", "noop")


def test_session_orientation_uses_only_explicit_global_accepted_adrs(tmp_path):
    project = _project(tmp_path)
    envelope = parse_payload(
        json.dumps(
            {"cwd": str(project), "hook_event_name": "SessionStart"}
        ).encode(),
        "codex-cli",
    )
    assert envelope
    context, kind = evaluate(envelope)
    assert kind == "session"
    assert "ADR-001" in context
    assert "ADR-002" not in context
    assert "ADR-003" not in context


@pytest.mark.parametrize(
    "event",
    ["Stop", "SubagentStop", "SessionEnd", "PermissionRequest", "Notification", "Interrupt", "Unknown"],
)
def test_unsupported_and_terminal_events_are_successful_noops(tmp_path, event):
    project = _project(tmp_path)
    envelope = parse_payload(
        json.dumps({"cwd": str(project), "hook_event_name": event}).encode(),
        "claude-code-cli",
    )
    assert envelope and evaluate(envelope) == ("", "noop")


def test_malformed_oversized_and_disabled_payloads_fail_open(tmp_path):
    assert parse_payload(b"{", "codex-cli") is None
    assert parse_payload(b"x" * (MAX_INPUT_BYTES + 1), "codex-cli") is None
    assert parse_payload(
        b'{"adr_kit_disabled":true}', "codex-cli"
    ) is None
    result = subprocess.run(
        [
            sys.executable,
            str(HOOKS / "adr-hook.py"),
            "--client",
            "codex-cli",
        ],
        input="{",
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout == ""


def test_duplicate_event_is_a_successful_noop(tmp_path):
    """Deduplication is a property of the one host.

    This used to run twice, once per host, because a second engine had to be
    held to the same contract. ADR-029 retired that engine, so the parameter
    is gone rather than left permanently skipped.
    """
    project = _project(tmp_path)
    payload = json.dumps(
        {
            "cwd": str(project),
            "hook_event_name": "SessionStart",
            "session_id": f"duplicate-{uuid.uuid4()}",
        }
    )
    command = [
        sys.executable,
        str(HOOKS / "adr-hook.py"),
        "--client",
        "codex-cli",
        "--event",
        "SessionStart",
    ]
    first = subprocess.run(
        command, input=payload, text=True, capture_output=True, check=False
    )
    second = subprocess.run(
        command, input=payload, text=True, capture_output=True, check=False
    )
    assert first.returncode == second.returncode == 0
    assert first.stdout
    assert second.stdout == ""
